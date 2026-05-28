"""Stdlib-only WAV helpers untuk Windows tanpa ffmpeg.

Modul ini menggantikan kebutuhan ffmpeg saat:

- file input sudah berformat WAV,
- target output juga WAV mono 16-bit dengan sample rate konsisten.

Hanya pakai modul standar (`wave`, `array`). Cocok untuk alur dataset
rekaman dari browser (sudah WAV) maupun build voice profile.
"""

from __future__ import annotations

import array
import wave
from pathlib import Path


def _read_wav_int16_mono(path: Path) -> tuple[array.array, int]:
    """Baca WAV apapun menjadi int16 mono."""

    with wave.open(str(path), "rb") as wav_file:
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        framerate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        raw = wav_file.readframes(n_frames)

    if sample_width == 1:
        # Unsigned 8-bit -> signed 16-bit.
        samples = array.array("h")
        for byte in raw:
            samples.append((byte - 128) * 256)
    elif sample_width == 2:
        samples = array.array("h")
        samples.frombytes(raw)
    elif sample_width == 4:
        # 32-bit int -> 16-bit int.
        wide = array.array("i")
        wide.frombytes(raw)
        samples = array.array("h", [max(-32768, min(32767, value >> 16)) for value in wide])
    else:
        raise ValueError(
            f"Sample width {sample_width} tidak didukung untuk file {path}."
        )

    if n_channels > 1:
        mono = array.array("h")
        for offset in range(0, len(samples), n_channels):
            chunk = samples[offset : offset + n_channels]
            avg = sum(chunk) // len(chunk)
            if avg > 32767:
                avg = 32767
            elif avg < -32768:
                avg = -32768
            mono.append(avg)
        samples = mono
    return samples, framerate


def _resample_linear(
    samples: array.array,
    src_rate: int,
    dst_rate: int,
) -> array.array:
    """Resample linear sederhana memakai stdlib saja."""

    if src_rate == dst_rate or not samples:
        return samples
    ratio = dst_rate / src_rate
    n_dst = int(len(samples) * ratio)
    out = array.array("h")
    last = len(samples) - 1
    for i in range(n_dst):
        src_pos = i / ratio
        idx = int(src_pos)
        frac = src_pos - idx
        if idx >= last:
            value = samples[last]
        else:
            value = int(samples[idx] * (1 - frac) + samples[idx + 1] * frac)
        if value > 32767:
            value = 32767
        elif value < -32768:
            value = -32768
        out.append(value)
    return out


def _write_wav_mono16(path: Path, samples: array.array, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())


def normalize_wav(
    input_path: str | Path,
    output_path: str | Path,
    *,
    sample_rate: int = 22050,
) -> Path:
    """Tulis ulang file WAV menjadi mono 16-bit pada sample rate target."""

    source = Path(input_path)
    output = Path(output_path)
    samples, src_rate = _read_wav_int16_mono(source)
    samples = _resample_linear(samples, src_rate, sample_rate)
    _write_wav_mono16(output, samples, sample_rate)
    return output


def concat_wavs(
    wav_files: list[Path],
    output_path: str | Path,
    *,
    sample_rate: int = 22050,
) -> Path:
    """Gabungkan beberapa WAV (mono 16-bit) menjadi satu file."""

    if not wav_files:
        raise ValueError("Daftar file WAV kosong.")

    output = Path(output_path)
    combined = array.array("h")
    for wav_file in wav_files:
        samples, src_rate = _read_wav_int16_mono(Path(wav_file))
        if src_rate != sample_rate:
            samples = _resample_linear(samples, src_rate, sample_rate)
        combined.extend(samples)
    _write_wav_mono16(output, combined, sample_rate)
    return output


def is_wav_file(path: str | Path) -> bool:
    """Cek cepat apakah file ber-header WAV."""

    candidate = Path(path)
    if not candidate.exists() or not candidate.is_file():
        return False
    try:
        with candidate.open("rb") as file:
            header = file.read(12)
    except OSError:
        return False
    return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"
