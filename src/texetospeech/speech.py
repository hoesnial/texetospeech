"""Optional STT and TTS adapters.

The core calculator does not depend on these adapters. They use local commands
or optional packages only when available.

Backend voice cloning tersedia dalam beberapa tier berdasarkan spek device:

1. **piper-tts** (paling ringan, ~50MB model, real-time di CPU low-end)
   - Tidak butuh GPU, RAM minimal 512MB
   - Kualitas bagus untuk bahasa Indonesia
   - Tidak mendukung voice cloning langsung, tapi bisa fine-tune model

2. **Coqui VITS** (ringan, ~200MB model)
   - Bisa jalan di CPU dengan RAM 2-4GB
   - Mendukung speaker embedding dari reference audio
   - Lebih cepat dari XTTS

3. **Coqui XTTS v2** (berat, ~2GB model, butuh 6GB+ RAM)
   - Kualitas voice cloning terbaik
   - Butuh GPU atau RAM besar

Sistem akan otomatis memilih backend terbaik berdasarkan resource yang tersedia.
Set environment variable TEXETOSPEECH_TTS_BACKEND untuk memaksa pilihan:
  - "piper" : paksa Piper TTS
  - "coqui-vits" : paksa Coqui VITS
  - "coqui-xtts" : paksa Coqui XTTS v2
  - "auto" (default) : pilih otomatis berdasarkan RAM dan GPU
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path

from .audio import convert_to_wav
from .errors import SpeechBackendError


@dataclass(frozen=True)
class SpeechResult:
    text: str
    backend: str
    output_path: str | None = None


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    backend: str
    source_path: str | None = None


def _get_available_ram_gb() -> float:
    """Detect available system RAM in GB."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    kb = int(line.split()[1])
                    return kb / (1024 * 1024)
    except (OSError, ValueError):
        pass
    # Fallback: assume low RAM
    return 2.0


def _has_cuda() -> bool:
    """Check if CUDA GPU is available."""
    try:
        import torch  # type: ignore
        return torch.cuda.is_available()
    except Exception:
        return False


def _select_voice_backend() -> str:
    """Auto-select the best voice cloning backend based on system resources."""
    forced = os.environ.get("TEXETOSPEECH_TTS_BACKEND", "auto").strip().lower()
    if forced in ("piper", "coqui-vits", "coqui-xtts"):
        return forced

    # Auto-detection
    ram_gb = _get_available_ram_gb()

    # If GPU available and enough RAM, use XTTS
    if _has_cuda() and ram_gb >= 4.0:
        return "coqui-xtts"

    # If moderate RAM, try VITS
    if ram_gb >= 3.0:
        return "coqui-vits"

    # Low RAM: use Piper
    return "piper"


def speak_text(
    text: str,
    *,
    output_path: str | Path | None = None,
    voice_reference: str | Path | None = None,
) -> SpeechResult:
    """Speak text or save it as audio using an available backend.

    Jika voice_reference diberikan, sistem akan mencoba voice cloning
    dengan backend yang sesuai spek device (auto-detect).
    """

    if voice_reference is not None:
        backend_choice = _select_voice_backend()

        # Try backends in order of preference based on auto-detection
        if backend_choice == "piper":
            piper_result = _try_piper_tts(text, output_path, voice_reference)
            if piper_result is not None:
                return piper_result
            # Fallback to VITS if piper not available
            vits_result = _try_coqui_vits(text, output_path, voice_reference)
            if vits_result is not None:
                return vits_result

        elif backend_choice == "coqui-vits":
            vits_result = _try_coqui_vits(text, output_path, voice_reference)
            if vits_result is not None:
                return vits_result
            # Fallback to piper
            piper_result = _try_piper_tts(text, output_path, voice_reference)
            if piper_result is not None:
                return piper_result

        elif backend_choice == "coqui-xtts":
            xtts_result = _try_coqui_xtts(text, output_path, voice_reference)
            if xtts_result is not None:
                return xtts_result
            # Fallback to VITS then piper
            vits_result = _try_coqui_vits(text, output_path, voice_reference)
            if vits_result is not None:
                return vits_result
            piper_result = _try_piper_tts(text, output_path, voice_reference)
            if piper_result is not None:
                return piper_result

        # If all voice cloning backends fail, fall through to standard TTS
        # but log a warning
        print(
            f"[warn] Voice cloning backend '{backend_choice}' tidak tersedia. "
            f"Menggunakan TTS standar. RAM tersedia: {_get_available_ram_gb():.1f}GB"
        )

    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        for command in ("espeak-ng", "espeak"):
            if shutil.which(command):
                _run([command, "-v", "id", "-w", str(output), text])
                return SpeechResult(text=text, backend=command, output_path=str(output))

        pyttsx3_result = _try_pyttsx3(text, output)
        if pyttsx3_result is not None:
            return pyttsx3_result

        raise SpeechBackendError(
            "Backend TTS untuk menyimpan audio belum tersedia. "
            "Install espeak-ng, espeak, pyttsx3, atau piper-tts."
        )

    if shutil.which("spd-say"):
        _run(["spd-say", "-l", "id", text])
        return SpeechResult(text=text, backend="spd-say")

    for command in ("espeak-ng", "espeak"):
        if shutil.which(command):
            _run([command, "-v", "id", text])
            return SpeechResult(text=text, backend=command)

    pyttsx3_result = _try_pyttsx3(text, None)
    if pyttsx3_result is not None:
        return pyttsx3_result

    raise SpeechBackendError(
        "Backend TTS belum tersedia. Install espeak-ng, espeak, spd-say, pyttsx3, atau piper-tts."
    )


def transcribe_audio(
    audio_path: str | Path | None = None,
    *,
    language: str = "id-ID",
) -> TranscriptResult:
    """Transcribe an audio file or microphone input using optional backends."""

    if audio_path is not None:
        source = Path(audio_path)
        if source.suffix.lower() in {".txt", ".transcript"}:
            return TranscriptResult(
                text=source.read_text(encoding="utf-8").strip(),
                backend="text-transcript",
                source_path=str(source),
            )

        whisper_result = _try_whisper_cli(source)
        if whisper_result is not None:
            return whisper_result

        whisper_python_result = _try_whisper_python(source)
        if whisper_python_result is not None:
            return whisper_python_result

        recognition_result = _try_speech_recognition_file(source, language)
        if recognition_result is not None:
            return recognition_result

        raise SpeechBackendError(
            "Backend STT untuk file audio belum tersedia. Install whisper CLI atau SpeechRecognition."
        )

    recognition_result = _try_speech_recognition_microphone(language)
    if recognition_result is not None:
        return recognition_result

    raise SpeechBackendError(
        "Backend STT mikrofon belum tersedia. Install SpeechRecognition dan PyAudio."
    )


def _try_piper_tts(
    text: str,
    output_path: str | Path | None,
    voice_reference: str | Path | None = None,
) -> SpeechResult | None:
    """Try Piper TTS — very lightweight neural TTS that runs on CPU.

    Piper menggunakan model ONNX yang sangat kecil (~50MB).
    Untuk voice cloning, Piper menggunakan model yang sudah di-fine-tune
    dengan suara pengguna. Jika belum ada fine-tuned model, Piper tetap
    menghasilkan suara natural yang jauh lebih baik dari espeak.

    Install: pip install piper-tts
    Model akan di-download otomatis saat pertama kali digunakan.
    """
    if output_path is None:
        return None

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Try piper Python package first
    piper_result = _try_piper_python(text, output, voice_reference)
    if piper_result is not None:
        return piper_result

    # Try piper CLI
    piper_result = _try_piper_cli(text, output)
    if piper_result is not None:
        return piper_result

    return None


def _try_piper_python(
    text: str,
    output: Path,
    voice_reference: str | Path | None = None,
) -> SpeechResult | None:
    """Use piper-tts Python package."""
    try:
        from piper import PiperVoice  # type: ignore
    except Exception:
        return None

    try:
        import wave
        model_path = _get_piper_model_path()
        if model_path is None:
            return None

        voice = PiperVoice.load(str(model_path))
        chunks = list(voice.synthesize(text))
        if not chunks:
            return None

        with wave.open(str(output), "wb") as wav_file:
            wav_file.setnchannels(chunks[0].sample_channels)
            wav_file.setsampwidth(chunks[0].sample_width)
            wav_file.setframerate(chunks[0].sample_rate)
            for chunk in chunks:
                wav_file.writeframes(chunk.audio_int16_bytes)

        return SpeechResult(text=text, backend="piper-tts", output_path=str(output))
    except Exception:
        return None


def _try_piper_cli(text: str, output: Path) -> SpeechResult | None:
    """Use piper CLI if installed."""
    if not shutil.which("piper"):
        return None

    model_path = _get_piper_model_path()
    model_args = []
    if model_path is not None:
        model_args = ["--model", str(model_path)]
    else:
        # Try with default model download
        model_args = ["--model", "id_ID-aceh-medium"]

    try:
        proc = subprocess.run(
            ["piper", *model_args, "--output_file", str(output)],
            input=text,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0 and output.exists():
            return SpeechResult(text=text, backend="piper-cli", output_path=str(output))
    except (subprocess.TimeoutExpired, OSError):
        pass

    return None


def _get_piper_model_path() -> Path | None:
    """Get path to Piper model, checking for custom fine-tuned model first."""
    # Check for user's fine-tuned model
    custom_model = Path("voice_profiles/default/piper_model.onnx")
    if custom_model.exists():
        return custom_model

    # Check environment variable
    env_model = os.environ.get("TEXETOSPEECH_PIPER_MODEL")
    if env_model:
        model_path = Path(env_model)
        if model_path.exists():
            return model_path

    # Check common piper model locations
    data_dirs = [
        Path("models/piper"),
        Path.home() / ".local" / "share" / "piper-voices",
        Path("/usr/share/piper-voices"),
    ]
    for data_dir in data_dirs:
        if data_dir.exists():
            # Look for Indonesian model (.onnx files)
            for onnx in sorted(data_dir.rglob("*.onnx")):
                # Prefer Indonesian models
                if "id" in onnx.name.lower():
                    return onnx
            # Fallback to any .onnx model
            for onnx in sorted(data_dir.rglob("*.onnx")):
                return onnx

    return None


def _try_coqui_vits(
    text: str,
    output_path: str | Path | None,
    voice_reference: str | Path,
) -> SpeechResult | None:
    """Try Coqui VITS — lighter than XTTS, supports speaker embedding.

    VITS model ~200MB, bisa jalan di CPU dengan RAM 2-4GB.
    Lebih cepat dari XTTS karena single-stage synthesis.
    """
    if output_path is None:
        raise SpeechBackendError(
            "Voice cloning membutuhkan --out agar audio dapat disimpan."
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    reference = Path(voice_reference)
    if not reference.exists():
        raise SpeechBackendError(f"File voice reference tidak ditemukan: {reference}")

    try:
        model = _load_coqui_vits_model()
        model.tts_to_file(
            text=text,
            speaker_wav=str(reference),
            language="id",
            file_path=str(output),
        )
    except ImportError:
        return None
    except Exception as exc:
        # If VITS fails (e.g., model not found), return None to try next backend
        print(f"[warn] Coqui VITS gagal: {exc}")
        return None

    return SpeechResult(text=text, backend="coqui-vits", output_path=str(output))


@lru_cache(maxsize=1)
def _load_coqui_vits_model():
    """Load a lighter Coqui VITS model for voice cloning."""
    try:
        import torch  # type: ignore
        from TTS.api import TTS  # type: ignore
    except Exception as exc:
        raise ImportError(
            "Backend Coqui VITS belum siap. Install coqui-tts dan torch."
        ) from exc

    os.environ.setdefault("COQUI_TOS_AGREED", "1")
    model_name = os.environ.get(
        "TEXETOSPEECH_VITS_MODEL",
        "tts_models/multilingual/multi-dataset/your_tts",
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return TTS(model_name=model_name, progress_bar=False).to(device)


def _try_coqui_xtts(
    text: str,
    output_path: str | Path | None,
    voice_reference: str | Path,
) -> SpeechResult | None:
    """Try Coqui XTTS v2 — highest quality but heaviest (needs 6GB+ RAM/VRAM)."""
    if output_path is None:
        raise SpeechBackendError(
            "Voice cloning membutuhkan --out agar audio dapat disimpan."
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    reference = Path(voice_reference)
    if not reference.exists():
        raise SpeechBackendError(f"File voice reference tidak ditemukan: {reference}")

    try:
        model = _load_coqui_xtts_model()
        model.tts_to_file(
            text=text,
            speaker_wav=str(reference),
            language="id",
            file_path=str(output),
        )
    except ImportError:
        return None
    except Exception as exc:
        raise SpeechBackendError(f"Voice cloning XTTS gagal: {exc}") from exc

    return SpeechResult(text=text, backend="coqui-xtts", output_path=str(output))


def _try_pyttsx3(text: str, output_path: Path | None) -> SpeechResult | None:
    try:
        import pyttsx3  # type: ignore
    except Exception:
        return None

    engine = pyttsx3.init()
    if output_path is None:
        engine.say(text)
        engine.runAndWait()
        return SpeechResult(text=text, backend="pyttsx3")

    engine.save_to_file(text, str(output_path))
    engine.runAndWait()
    return SpeechResult(text=text, backend="pyttsx3", output_path=str(output_path))


@lru_cache(maxsize=1)
def _load_coqui_xtts_model():
    try:
        import torch  # type: ignore
        from TTS.api import TTS  # type: ignore
    except Exception as exc:
        raise ImportError(
            "Backend voice cloning belum siap. Install coqui-tts, torch, torchaudio, dan torchcodec."
        ) from exc

    os.environ.setdefault("COQUI_TOS_AGREED", "1")
    model_name = os.environ.get(
        "TEXETOSPEECH_COQUI_MODEL",
        "tts_models/multilingual/multi-dataset/xtts_v2",
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return TTS(model_name=model_name, progress_bar=False).to(device)


def _try_whisper_cli(source: Path) -> TranscriptResult | None:
    if not shutil.which("whisper"):
        return None

    with tempfile.TemporaryDirectory() as temp_dir:
        _run(
            [
                "whisper",
                str(source),
                "--language",
                "Indonesian",
                "--model",
                "base",
                "--output_format",
                "txt",
                "--output_dir",
                temp_dir,
            ],
            timeout=900,
        )
        output_files = sorted(Path(temp_dir).glob("*.txt"))
        if not output_files:
            raise SpeechBackendError("Whisper tidak menghasilkan file transkrip.")
        transcript = output_files[0].read_text(encoding="utf-8").strip()
        return TranscriptResult(
            text=transcript,
            backend="whisper-cli",
            source_path=str(source),
        )


def _try_whisper_python(source: Path) -> TranscriptResult | None:
    try:
        import whisper  # type: ignore
    except Exception:
        return None

    model = whisper.load_model("base")
    result = model.transcribe(str(source), language="id")
    transcript = str(result.get("text", "")).strip()
    return TranscriptResult(
        text=transcript,
        backend="whisper-python",
        source_path=str(source),
    )


def _try_speech_recognition_file(
    source: Path,
    language: str,
) -> TranscriptResult | None:
    try:
        import speech_recognition as sr  # type: ignore
    except Exception:
        return None

    recognizer = sr.Recognizer()
    audio_source = source
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if source.suffix.lower() not in {".wav", ".aiff", ".aif", ".flac"}:
        temp_dir = tempfile.TemporaryDirectory()
        audio_source = Path(temp_dir.name) / "speech-recognition.wav"
        convert_to_wav(source, audio_source, sample_rate=16000)
    try:
        with sr.AudioFile(str(audio_source)) as audio_file:
            audio = recognizer.record(audio_file)
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()
    try:
        text = recognizer.recognize_google(audio, language=language)
    except sr.UnknownValueError as exc:
        raise SpeechBackendError("Maaf, suara belum terbaca dengan jelas.") from exc
    except sr.RequestError as exc:
        raise SpeechBackendError(f"Layanan STT gagal diakses: {exc}.") from exc
    return TranscriptResult(
        text=text,
        backend="SpeechRecognition-google",
        source_path=str(source),
    )


def _try_speech_recognition_microphone(language: str) -> TranscriptResult | None:
    try:
        import speech_recognition as sr  # type: ignore
    except Exception:
        return None

    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio, language=language)
    except sr.UnknownValueError as exc:
        raise SpeechBackendError("Maaf, suara belum terbaca dengan jelas.") from exc
    except sr.RequestError as exc:
        raise SpeechBackendError(f"Layanan STT gagal diakses: {exc}.") from exc
    return TranscriptResult(text=text, backend="SpeechRecognition-google-microphone")


def _run(command: list[str], *, timeout: int = 120) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise SpeechBackendError(message) from exc
