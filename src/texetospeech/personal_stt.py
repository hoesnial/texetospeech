"""Keyword-spotting STT pakai dataset rekaman user sebagai template.

Backend ini cocok untuk vocabulary sempit MVP (angka 0..10 + operator dasar).
Karena user sudah merekam dataset bilangan dan operator, kita pakai rekaman
itu sebagai template referensi. Untuk audio masuk:

1. Resample ke 16 kHz mono int16.
2. Trim silence di kedua sisi.
3. Segmentasi per-kata berdasarkan deteksi senyap.
4. Untuk tiap segmen, hitung mean log-mel feature.
5. Cocokkan ke template terdekat (cosine similarity).
6. Susun output sebagai string.

Implementasi murni stdlib (`math`, `cmath`, `array`, `wave`). Tidak butuh
torch / numpy / pip install apa pun. Akurasi tergantung kebersihan dataset
dan input. Untuk audio bersih dengan vocabulary terbatas, akurasi biasanya
tinggi.
"""

from __future__ import annotations

import array
import cmath
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .errors import SpeechBackendError
from .personal_voice import build_phrase_index, find_default_dataset_dirs
from .wav_utils import _read_wav_int16_mono, _resample_linear


SAMPLE_RATE = 16000
FRAME_LENGTH = 400  # 25 ms @ 16 kHz
HOP_LENGTH = 160  # 10 ms @ 16 kHz
FFT_SIZE = 512
N_MELS = 20
LOW_FREQ = 80.0
HIGH_FREQ = 7600.0


@dataclass(frozen=True)
class PersonalSTTResult:
    text: str
    matched_count: int
    template_count: int
    similarity_min: float
    similarity_max: float


# ---------------------------------------------------------------------------
# DSP helpers (stdlib only)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _hann_window(length: int) -> tuple[float, ...]:
    return tuple(0.5 - 0.5 * math.cos(2 * math.pi * i / (length - 1)) for i in range(length))


def _fft_inplace(x: list[complex]) -> list[complex]:
    """Iterative Cooley-Tukey FFT. `x` length must be power of 2."""

    n = len(x)
    if n & (n - 1):
        raise ValueError("FFT length must be a power of two")

    # Bit-reversal permutation.
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            x[i], x[j] = x[j], x[i]

    size = 2
    while size <= n:
        half = size >> 1
        omega = cmath.exp(-2j * math.pi / size)
        for start in range(0, n, size):
            w = 1 + 0j
            for k in range(half):
                t = x[start + k + half] * w
                x[start + k + half] = x[start + k] - t
                x[start + k] = x[start + k] + t
                w *= omega
        size <<= 1
    return x


def _hz_to_mel(hz: float) -> float:
    return 2595.0 * math.log10(1.0 + hz / 700.0)


def _mel_to_hz(mel: float) -> float:
    return 700.0 * (10 ** (mel / 2595.0) - 1.0)


@lru_cache(maxsize=1)
def _mel_filterbank() -> tuple[tuple[float, ...], ...]:
    n_bins = FFT_SIZE // 2 + 1
    low_mel = _hz_to_mel(LOW_FREQ)
    high_mel = _hz_to_mel(HIGH_FREQ)
    mel_points = [low_mel + (high_mel - low_mel) * i / (N_MELS + 1) for i in range(N_MELS + 2)]
    hz_points = [_mel_to_hz(m) for m in mel_points]
    bin_points = [int(round(hz * FFT_SIZE / SAMPLE_RATE)) for hz in hz_points]

    filters: list[tuple[float, ...]] = []
    for m in range(1, N_MELS + 1):
        left, center, right = bin_points[m - 1], bin_points[m], bin_points[m + 1]
        if center == left:
            center = left + 1
        if right == center:
            right = center + 1
        weights = [0.0] * n_bins
        for k in range(max(0, left), min(n_bins, center)):
            weights[k] = (k - left) / (center - left)
        for k in range(max(0, center), min(n_bins, right)):
            weights[k] = (right - k) / (right - center)
        filters.append(tuple(weights))
    return tuple(filters)


def _mean_log_mel(samples: array.array) -> list[float] | None:
    """Hitung rata-rata log-mel energies untuk satu segmen audio."""

    if len(samples) < FRAME_LENGTH:
        return None
    window = _hann_window(FRAME_LENGTH)
    filters = _mel_filterbank()
    n_frames = (len(samples) - FRAME_LENGTH) // HOP_LENGTH + 1
    mel_sum = [0.0] * N_MELS
    for frame_idx in range(n_frames):
        start = frame_idx * HOP_LENGTH
        frame = [
            complex((samples[start + j] / 32768.0) * window[j], 0.0)
            for j in range(FRAME_LENGTH)
        ]
        if FFT_SIZE > FRAME_LENGTH:
            frame.extend([0 + 0j] * (FFT_SIZE - FRAME_LENGTH))
        spectrum = _fft_inplace(frame)
        half = FFT_SIZE // 2 + 1
        power = [s.real * s.real + s.imag * s.imag for s in spectrum[:half]]
        for m in range(N_MELS):
            weights = filters[m]
            energy = 0.0
            for k in range(half):
                energy += power[k] * weights[k]
            mel_sum[m] += math.log(energy + 1e-10)
    return [value / n_frames for value in mel_sum]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / math.sqrt(na * nb)


# ---------------------------------------------------------------------------
# Silence detection / word segmentation
# ---------------------------------------------------------------------------


def _frame_rms(samples: array.array, frame_size: int, hop: int) -> list[float]:
    rms_values: list[float] = []
    n = len(samples)
    if n < frame_size:
        return rms_values
    n_frames = (n - frame_size) // hop + 1
    for i in range(n_frames):
        start = i * hop
        total = 0
        for j in range(frame_size):
            value = samples[start + j]
            total += value * value
        rms_values.append(math.sqrt(total / frame_size))
    return rms_values


def _segment_words(samples: array.array, sample_rate: int) -> list[tuple[int, int]]:
    """Cari batas kata berdasarkan deteksi senyap."""

    frame_size = sample_rate * 25 // 1000
    hop = sample_rate * 10 // 1000
    if frame_size <= 0 or hop <= 0:
        return [(0, len(samples))]

    rms_values = _frame_rms(samples, frame_size, hop)
    if not rms_values:
        return [(0, len(samples))]

    peak_rms = max(rms_values)
    if peak_rms <= 0:
        return []
    threshold = max(peak_rms * 0.18, 250.0)

    min_word_frames = max(1, int(0.08 * sample_rate / hop))  # 80 ms minimum
    min_silence_frames = max(1, int(0.15 * sample_rate / hop))  # 150 ms gap

    segments: list[tuple[int, int]] = []
    in_word = False
    start_frame = 0
    silence_run = 0

    for i, value in enumerate(rms_values):
        active = value > threshold
        if in_word:
            if active:
                silence_run = 0
            else:
                silence_run += 1
                if silence_run >= min_silence_frames:
                    end_frame = i - silence_run + 1
                    if end_frame - start_frame >= min_word_frames:
                        seg_start = start_frame * hop
                        seg_end = min(len(samples), end_frame * hop + frame_size)
                        segments.append((seg_start, seg_end))
                    in_word = False
                    silence_run = 0
        else:
            if active:
                in_word = True
                start_frame = i
                silence_run = 0

    if in_word:
        seg_start = start_frame * hop
        seg_end = len(samples)
        if seg_end - seg_start >= frame_size:
            segments.append((seg_start, seg_end))

    return segments


# ---------------------------------------------------------------------------
# Template management
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Template:
    phrase: str
    feature: tuple[float, ...]


def _load_templates(dataset_dirs: list[Path]) -> list[_Template]:
    index = build_phrase_index(dataset_dirs)
    templates: list[_Template] = []
    for phrase, wav_path in index.items():
        # Hanya pakai prompt satu kata untuk keyword spotting; frasa panjang
        # tidak cocok untuk segmentasi per-kata.
        if " " in phrase:
            continue
        try:
            samples, src_rate = _read_wav_int16_mono(wav_path)
        except (OSError, ValueError):
            continue
        if src_rate != SAMPLE_RATE:
            samples = _resample_linear(samples, src_rate, SAMPLE_RATE)
        samples = _trim_silence(samples, SAMPLE_RATE)
        feature = _mean_log_mel(samples)
        if feature is None:
            continue
        templates.append(_Template(phrase=phrase, feature=tuple(feature)))
    return templates


def _trim_silence(samples: array.array, sample_rate: int) -> array.array:
    """Trim leading/trailing silence sederhana untuk template/segment."""

    if not samples:
        return samples
    frame_size = sample_rate * 25 // 1000
    hop = sample_rate * 10 // 1000
    rms_values = _frame_rms(samples, frame_size, hop)
    if not rms_values:
        return samples
    peak = max(rms_values)
    if peak <= 0:
        return samples
    threshold = max(peak * 0.18, 200.0)

    start_frame = 0
    while start_frame < len(rms_values) and rms_values[start_frame] <= threshold:
        start_frame += 1
    end_frame = len(rms_values) - 1
    while end_frame > start_frame and rms_values[end_frame] <= threshold:
        end_frame -= 1
    start_idx = max(0, start_frame * hop - hop)
    end_idx = min(len(samples), end_frame * hop + frame_size + hop)
    if start_idx >= end_idx:
        return samples
    out = array.array("h")
    out.extend(samples[start_idx:end_idx])
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def transcribe(
    audio_path: str | Path,
    *,
    dataset_dirs: list[Path] | None = None,
    min_similarity: float = 0.45,
) -> PersonalSTTResult:
    """Transkrip audio dengan keyword spotting terhadap dataset user."""

    if dataset_dirs is None:
        dataset_dirs = find_default_dataset_dirs()
    if not dataset_dirs:
        raise SpeechBackendError(
            "Personal STT butuh dataset rekaman pribadi. Rekam dulu di web app "
            "atau dengan `record-dataset`."
        )

    templates = _load_templates(dataset_dirs)
    if not templates:
        raise SpeechBackendError(
            "Personal STT tidak menemukan template kata satuan dari dataset. "
            "Pastikan dataset MVP (angka 0..10 + operator) sudah direkam."
        )

    audio_path = Path(audio_path)
    samples, src_rate = _read_wav_int16_mono(audio_path)
    if src_rate != SAMPLE_RATE:
        samples = _resample_linear(samples, src_rate, SAMPLE_RATE)
    samples = _trim_silence(samples, SAMPLE_RATE)

    if not samples:
        raise SpeechBackendError("Audio terlalu pendek atau senyap.")

    segments = _segment_words(samples, SAMPLE_RATE)
    if not segments:
        raise SpeechBackendError("Tidak ada kata terdeteksi pada audio.")

    words: list[str] = []
    sims: list[float] = []
    for start, end in segments:
        seg = array.array("h")
        seg.extend(samples[start:end])
        feature = _mean_log_mel(seg)
        if feature is None:
            continue
        best_phrase: str | None = None
        best_sim = -1.0
        for template in templates:
            sim = _cosine_similarity(feature, list(template.feature))
            if sim > best_sim:
                best_sim = sim
                best_phrase = template.phrase
        if best_phrase is None or best_sim < min_similarity:
            continue
        words.append(best_phrase)
        sims.append(best_sim)

    if not words:
        raise SpeechBackendError("Tidak ada kata cocok di template dataset.")

    text = " ".join(words)
    return PersonalSTTResult(
        text=text,
        matched_count=len(words),
        template_count=len(templates),
        similarity_min=min(sims),
        similarity_max=max(sims),
    )


def has_personal_stt_dataset() -> bool:
    """Cek cepat apakah dataset rekaman cukup untuk personal STT."""

    dataset_dirs = find_default_dataset_dirs()
    if not dataset_dirs:
        return False
    index = build_phrase_index(dataset_dirs)
    for phrase in index:
        if " " not in phrase:
            return True
    return False
