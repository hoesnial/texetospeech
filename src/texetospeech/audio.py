"""Local audio recording and voice-profile helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .errors import SpeechBackendError


@dataclass(frozen=True)
class RecordingResult:
    path: str
    backend: str
    seconds: float
    sample_rate: int


@dataclass(frozen=True)
class VoiceProfile:
    name: str
    profile_dir: str
    reference_wav: str
    source_count: int
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def record_wav(
    output_path: str | Path,
    *,
    seconds: float = 4,
    sample_rate: int = 22050,
) -> RecordingResult:
    """Record mono 16-bit WAV from the default microphone."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("arecord"):
        _run(
            [
                "arecord",
                "-q",
                "-f",
                "S16_LE",
                "-c",
                "1",
                "-r",
                str(sample_rate),
                "-d",
                str(int(seconds)),
                str(output),
            ],
            timeout=int(seconds) + 15,
        )
        return RecordingResult(
            path=str(output),
            backend="arecord",
            seconds=seconds,
            sample_rate=sample_rate,
        )

    if shutil.which("ffmpeg"):
        _run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "alsa",
                "-i",
                "default",
                "-t",
                str(seconds),
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                str(output),
            ],
            timeout=int(seconds) + 20,
        )
        return RecordingResult(
            path=str(output),
            backend="ffmpeg-alsa",
            seconds=seconds,
            sample_rate=sample_rate,
        )

    raise SpeechBackendError(
        "Backend rekam mikrofon belum tersedia. Install arecord atau ffmpeg."
    )


def convert_to_wav(
    input_path: str | Path,
    output_path: str | Path,
    *,
    sample_rate: int = 22050,
) -> Path:
    """Convert browser/system audio into mono 16-bit WAV with ffmpeg."""

    if not shutil.which("ffmpeg"):
        raise SpeechBackendError("Konversi audio membutuhkan ffmpeg.")

    source = Path(input_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-sample_fmt",
            "s16",
            str(output),
        ],
        timeout=120,
    )
    return output


def build_voice_profile(
    source_dir: str | Path,
    profile_dir: str | Path = "voice_profiles/default",
    *,
    name: str = "default",
    max_files: int = 20,
    sample_rate: int = 22050,
) -> VoiceProfile:
    """Build a single speaker reference WAV from recorded dataset clips."""

    source = Path(source_dir)
    if not source.exists():
        raise SpeechBackendError(f"Folder dataset tidak ditemukan: {source}")

    wav_files = sorted(path for path in source.rglob("*.wav") if path.is_file())
    if not wav_files:
        raise SpeechBackendError(
            f"Tidak ada file .wav di {source}. Rekam dataset terlebih dahulu."
        )

    selected = wav_files[:max_files]
    profile = Path(profile_dir)
    profile.mkdir(parents=True, exist_ok=True)
    reference_wav = profile / "speaker_reference.wav"

    if len(selected) == 1:
        convert_to_wav(selected[0], reference_wav, sample_rate=sample_rate)
    else:
        _concat_wavs(selected, reference_wav, sample_rate=sample_rate)

    created_at = datetime.now(UTC).isoformat()
    voice_profile = VoiceProfile(
        name=name,
        profile_dir=str(profile),
        reference_wav=str(reference_wav),
        source_count=len(selected),
        created_at=created_at,
    )
    (profile / "profile.json").write_text(
        json.dumps(voice_profile.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return voice_profile


def _concat_wavs(
    wav_files: list[Path],
    output_path: Path,
    *,
    sample_rate: int,
) -> None:
    if not shutil.which("ffmpeg"):
        raise SpeechBackendError("Membuat voice profile membutuhkan ffmpeg.")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        normalized_files: list[Path] = []
        for index, wav_file in enumerate(wav_files, start=1):
            normalized = temp / f"{index:03d}.wav"
            convert_to_wav(wav_file, normalized, sample_rate=sample_rate)
            normalized_files.append(normalized)

        concat_list = temp / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{path.as_posix()}'" for path in normalized_files) + "\n",
            encoding="utf-8",
        )
        _run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-sample_fmt",
                "s16",
                str(output_path),
            ],
            timeout=240,
        )


def _run(command: list[str], *, timeout: int) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise SpeechBackendError(message) from exc

