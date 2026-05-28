"""Environment checks for the TexeToSpeech workflow."""

from __future__ import annotations

import importlib.util
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_doctor() -> list[CheckResult]:
    """Return status checks for audio and optional AI backends."""

    checks = [
        _command_check("espeak-ng", "TTS file/audio lokal"),
        _command_check("espeak", "TTS fallback lokal"),
        _command_check("spd-say", "TTS speaker langsung"),
        _command_check("ffmpeg", "konversi audio (opsional, hanya untuk webm/ogg)"),
        _command_check("arecord", "rekam mikrofon via ALSA"),
        _command_check("piper", "TTS neural ringan via Piper CLI"),
        _command_check("whisper", "STT file audio via Whisper CLI"),
        _module_check("piper", "TTS neural ringan via piper-tts Python"),
        _module_check("speech_recognition", "STT Google/mikrofon via Python"),
        _module_check("faster_whisper", "STT akurasi tinggi (faster-whisper)"),
        _module_check("pyttsx3", "TTS Python fallback"),
        _module_check("whisper", "STT file audio via Python package"),
        _module_check("TTS", "voice cloning Coqui (VITS/XTTS)"),
    ]
    checks.append(
        CheckResult(
            name="STT browser (Web Speech API)",
            ok=True,
            detail=(
                "siap di Chrome/Edge tanpa install apapun. Klik 'Mulai Rekam' di "
                "web app."
            ),
        )
    )
    profile = Path("voice_profiles/default/speaker_reference.wav")
    checks.append(
        CheckResult(
            name="voice profile",
            ok=profile.exists(),
            detail=str(profile) if profile.exists() else "belum dibuat",
        )
    )
    piper_model = Path("voice_profiles/default/piper_model.onnx")
    checks.append(
        CheckResult(
            name="piper custom model",
            ok=piper_model.exists(),
            detail=str(piper_model) if piper_model.exists() else "belum ada (opsional)",
        )
    )

    # Personal voice (concatenative TTS dari rekaman user) — paling reliable.
    from .personal_voice import (
        find_default_dataset_dirs,
        build_phrase_index,
    )
    from .personal_stt import has_personal_stt_dataset

    dataset_dirs = find_default_dataset_dirs()
    if dataset_dirs:
        index = build_phrase_index(dataset_dirs)
        if index:
            dirs_str = ", ".join(str(path) for path in dataset_dirs)
            detail = f"{len(index)} frasa dari {dirs_str}"
            checks.append(CheckResult(name="personal voice", ok=True, detail=detail))
        else:
            checks.append(
                CheckResult(
                    name="personal voice",
                    ok=False,
                    detail="dataset ada tapi tidak ada file WAV yang valid",
                )
            )
    else:
        checks.append(
            CheckResult(
                name="personal voice",
                ok=False,
                detail="belum ada rekaman dataset (recordings/browser_dataset/)",
            )
        )

    # Personal STT (template-matching dari dataset user) — offline, tanpa
    # whisper / SpeechRecognition.
    stt_ready = has_personal_stt_dataset()
    checks.append(
        CheckResult(
            name="personal STT",
            ok=stt_ready,
            detail=(
                "siap, vocabulary = kata satuan dari dataset"
                if stt_ready
                else "butuh dataset MVP (rekam angka 0..10 + operator dulu)"
            ),
        )
    )

    # Show auto-detected backend
    from .speech import _select_voice_backend, _get_available_ram_gb
    backend = _select_voice_backend()
    ram = _get_available_ram_gb()
    checks.append(
        CheckResult(
            name="voice backend (auto)",
            ok=True,
            detail=f"dipilih: {backend} (RAM tersedia: {ram:.1f}GB)",
        )
    )
    return checks


def _command_check(command: str, label: str) -> CheckResult:
    path = shutil.which(command)
    return CheckResult(
        name=command,
        ok=path is not None,
        detail=f"{label}: {path}" if path else f"{label}: belum tersedia",
    )


def _module_check(module: str, label: str) -> CheckResult:
    spec = importlib.util.find_spec(module)
    return CheckResult(
        name=module,
        ok=spec is not None,
        detail=f"{label}: tersedia" if spec else f"{label}: belum tersedia",
    )

