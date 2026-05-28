"""Concatenative TTS dari rekaman suara user.

Backend ini tidak butuh model neural, GPU, atau library eksternal apapun.
Cukup stdlib Python (`wave`, `array`, `csv`). Cocok untuk Windows / laptop
low-spec / Python 3.14 yang sulit pasang torch + Coqui TTS.

Cara kerjanya:

1. Baca `metadata.csv` dari folder dataset rekaman user.
2. Bangun index ``frasa -> path WAV`` setelah dinormalisasi.
3. Untuk teks output, lakukan greedy longest-match: kalau frasa panjang
   sudah direkam (mis. ``"satu tambah dua sama dengan tiga"``), putar utuh.
   Kalau tidak, fallback per kata.
4. Trim silence tiap clip, beri jeda kecil antar kata, lalu tulis WAV
   gabungan dengan format konsisten (mono 16-bit, 22050 Hz).

Karena audio yang dipakai adalah rekaman asli user, output TTS-nya benar-
benar suara user. Kekurangan: hanya mendukung kosakata yang sudah direkam.
"""

from __future__ import annotations

import array
import csv
import wave
from dataclasses import dataclass
from pathlib import Path

from .errors import SpeechBackendError
from .normalizer import normalize_text
from .wav_utils import _read_wav_int16_mono, _resample_linear


DEFAULT_DATASET_DIRS: tuple[str, ...] = (
    "recordings/browser_dataset",
    "recordings/my_voice",
)

DEFAULT_TARGET_RATE = 22050
DEFAULT_GAP_MS = 80


@dataclass(frozen=True)
class PersonalVoiceResult:
    output_path: str
    matched_phrases: list[str]
    missing_phrases: list[str]
    sample_rate: int
    source_count: int


def find_default_dataset_dirs() -> list[Path]:
    """Cari folder dataset yang ada `metadata.csv`-nya."""

    found: list[Path] = []
    for candidate in DEFAULT_DATASET_DIRS:
        path = Path(candidate)
        if (path / "metadata.csv").exists():
            found.append(path)
    return found


def _normalize_phrase(text: str) -> str:
    return normalize_text(text)


def _resolve_audio_path(dataset_dir: Path, raw_value: str, index_value: str | int) -> Path | None:
    """Resolve path audio dari metadata.csv dengan beberapa fallback."""

    candidates: list[Path] = []
    raw = (raw_value or "").strip()
    if raw:
        as_path = Path(raw)
        candidates.append(as_path)
        candidates.append(dataset_dir / as_path.name)
        if not as_path.is_absolute():
            candidates.append(dataset_dir.parent / as_path)

    try:
        idx_int = int(index_value)
    except (TypeError, ValueError):
        idx_int = None
    if idx_int is not None:
        candidates.append(dataset_dir / f"{idx_int:03d}.wav")
        candidates.append(dataset_dir / f"{idx_int:04d}.wav")

    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def build_phrase_index(dataset_dirs: list[Path] | None = None) -> dict[str, Path]:
    """Bangun mapping ``frasa -> path WAV`` dari metadata dataset."""

    if dataset_dirs is None:
        dataset_dirs = find_default_dataset_dirs()

    index: dict[str, Path] = {}
    for raw_dir in dataset_dirs:
        dataset_dir = Path(raw_dir)
        metadata_csv = dataset_dir / "metadata.csv"
        if not metadata_csv.exists():
            continue
        with metadata_csv.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                prompt = row.get("prompt", "")
                phrase = _normalize_phrase(prompt)
                if not phrase:
                    continue
                resolved = _resolve_audio_path(
                    dataset_dir,
                    row.get("audio_path", ""),
                    row.get("index", ""),
                )
                if resolved is None:
                    continue
                # Dataset pertama menang (urutan dataset_dirs = prioritas).
                index.setdefault(phrase, resolved)
    return index


def split_for_lookup(
    text: str,
    index: dict[str, Path],
) -> tuple[list[str], list[str]]:
    """Pecah teks menjadi frasa-frasa yang ada di index (greedy longest match)."""

    normalized = _normalize_phrase(text)
    tokens = normalized.split()
    if not tokens:
        return [], []

    max_len = max((len(key.split()) for key in index), default=1)
    max_len = max(1, min(max_len, len(tokens)))

    matched: list[str] = []
    missing: list[str] = []
    pos = 0
    while pos < len(tokens):
        best: str | None = None
        upper = min(max_len, len(tokens) - pos)
        for length in range(upper, 0, -1):
            candidate = " ".join(tokens[pos : pos + length])
            if candidate in index:
                best = candidate
                pos += length
                break
        if best is not None:
            matched.append(best)
        else:
            missing.append(tokens[pos])
            pos += 1
    return matched, missing


def _rms(samples: array.array) -> int:
    """RMS amplitudo. Hanya hitung sample non-silence agar tidak bias."""

    if not samples:
        return 0
    total = 0
    counted = 0
    for value in samples:
        if -200 < value < 200:
            continue
        total += value * value
        counted += 1
    if counted == 0:
        return 0
    return int((total / counted) ** 0.5)


def _scale_amplitude(samples: array.array, factor: float) -> array.array:
    """Skala amplitudo dengan clamp."""

    if abs(factor - 1.0) < 1e-3:
        return samples
    out = array.array("h")
    for value in samples:
        scaled = int(value * factor)
        if scaled > 32767:
            scaled = 32767
        elif scaled < -32768:
            scaled = -32768
        out.append(scaled)
    return out


def _crossfade_concat(
    head: array.array,
    tail: array.array,
    fade_samples: int,
) -> array.array:
    """Gabungkan dua klip dengan linear crossfade pada batasnya."""

    if not head:
        return array.array("h", tail)
    if not tail:
        return head
    fade = min(fade_samples, len(head), len(tail))
    if fade <= 1:
        result = array.array("h", head)
        result.extend(tail)
        return result

    body_head = head[: -fade]
    overlap_head = head[-fade:]
    overlap_tail = tail[:fade]
    body_tail = tail[fade:]

    blended = array.array("h")
    denom = max(1, fade - 1)
    for i in range(fade):
        weight_b = i / denom
        weight_a = 1.0 - weight_b
        value = int(overlap_head[i] * weight_a + overlap_tail[i] * weight_b)
        if value > 32767:
            value = 32767
        elif value < -32768:
            value = -32768
        blended.append(value)

    result = array.array("h")
    result.extend(body_head)
    result.extend(blended)
    result.extend(body_tail)
    return result


def _read_int16_mono(wav_path: Path) -> tuple[array.array, int]:
    """Baca file WAV jadi mono int16. Pakai helper stdlib yang sama dengan
    `wav_utils` agar konsisten lintas modul."""

    try:
        return _read_wav_int16_mono(wav_path)
    except ValueError as exc:
        raise SpeechBackendError(str(exc)) from exc


def _trim_silence(
    samples: array.array,
    framerate: int,
    *,
    threshold_ratio: float = 0.08,
    threshold_floor: int = 600,
    margin_ms: int = 50,
) -> array.array:
    """Trim leading/trailing silence menggunakan window 30ms dan threshold amplitudo."""

    if not samples:
        return samples

    n = len(samples)
    max_amp = 0
    for value in samples:
        abs_value = -value if value < 0 else value
        if abs_value > max_amp:
            max_amp = abs_value
    if max_amp == 0:
        return array.array("h")

    threshold = int(max_amp * threshold_ratio)
    if threshold < threshold_floor:
        threshold = threshold_floor

    window = max(1, framerate * 30 // 1000)
    step = max(1, window // 2)

    def _peak(start: int, end: int) -> int:
        peak = 0
        for value in samples[start:end]:
            abs_value = -value if value < 0 else value
            if abs_value > peak:
                peak = abs_value
        return peak

    start_idx = 0
    while start_idx + window <= n:
        if _peak(start_idx, start_idx + window) > threshold:
            break
        start_idx += step
    else:
        start_idx = 0

    end_idx = n
    while end_idx >= window:
        if _peak(end_idx - window, end_idx) > threshold:
            break
        end_idx -= step
    else:
        end_idx = n

    margin = framerate * margin_ms // 1000
    start_idx = max(0, start_idx - margin)
    end_idx = min(n, end_idx + margin)
    if start_idx >= end_idx:
        return samples
    trimmed = array.array("h")
    trimmed.extend(samples[start_idx:end_idx])
    return trimmed


def synthesize(
    text: str,
    output_path: str | Path,
    *,
    dataset_dirs: list[Path] | None = None,
    target_rate: int = DEFAULT_TARGET_RATE,
    gap_ms: int = DEFAULT_GAP_MS,
    crossfade_ms: int = 25,
    target_rms: int = 4500,
) -> PersonalVoiceResult:
    """Sintesis teks menjadi WAV memakai potongan rekaman user.

    Tambahan kualitas:
    - RMS normalization per klip agar volume seragam.
    - Linear crossfade antar klip untuk menghilangkan klik di transisi.
    - Trim silence sebelum + sesudah konkatenasi.
    """

    if not text or not text.strip():
        raise SpeechBackendError("Teks untuk sintesis personal voice kosong.")

    if dataset_dirs is None:
        dataset_dirs = find_default_dataset_dirs()
    if not dataset_dirs:
        raise SpeechBackendError(
            "Dataset suara pribadi belum tersedia. Rekam dataset terlebih dahulu "
            "lewat web app atau perintah `record-dataset`."
        )

    index = build_phrase_index(dataset_dirs)
    if not index:
        raise SpeechBackendError(
            "Metadata dataset suara pribadi kosong atau file rekaman tidak ditemukan."
        )

    matched, missing = split_for_lookup(text, index)
    if not matched:
        raise SpeechBackendError(
            "Tidak ada kata pada teks yang cocok dengan dataset suara pribadi. "
            f"Kata belum direkam: {' '.join(missing)}"
        )

    output = array.array("h")
    silence_len = max(0, target_rate * gap_ms // 1000)
    silence = array.array("h", [0] * silence_len)
    fade_samples = max(0, target_rate * crossfade_ms // 1000)
    used_clips: set[Path] = set()

    for position, phrase in enumerate(matched):
        wav_path = index[phrase]
        used_clips.add(wav_path)
        samples, framerate = _read_int16_mono(wav_path)
        samples = _trim_silence(samples, framerate)
        if framerate != target_rate:
            samples = _resample_linear(samples, framerate, target_rate)

        # Volume normalization supaya potongan dari take berbeda terdengar
        # sama keras.
        rms = _rms(samples)
        if rms > 0 and target_rms > 0:
            samples = _scale_amplitude(samples, target_rms / rms)

        if position == 0:
            output = array.array("h", samples)
            continue

        if silence_len:
            output.extend(silence)
        if fade_samples:
            output = _crossfade_concat(output, samples, fade_samples)
        else:
            output.extend(samples)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(target_rate)
        wav_file.writeframes(output.tobytes())

    return PersonalVoiceResult(
        output_path=str(output_path),
        matched_phrases=matched,
        missing_phrases=missing,
        sample_rate=target_rate,
        source_count=len(used_clips),
    )


def has_personal_voice_dataset() -> bool:
    """Cek cepat apakah ada dataset rekaman user dengan minimal satu entry valid."""

    for dataset_dir in find_default_dataset_dirs():
        index = build_phrase_index([dataset_dir])
        if index:
            return True
    return False
