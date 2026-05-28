"""Windows SAPI TTS via PowerShell.

System.Speech.Synthesis tersedia di setiap Windows tanpa install apa pun.
Suara default biasanya English (David / Zira), tapi tetap suara manusia
sehingga jauh lebih bisa diterima dibanding fallback tone.

Fungsi `synthesize_to_wav` menulis file WAV mono 16 kHz 16-bit. Cocok
sebagai fallback Windows ketika espeak/pyttsx3/piper belum terpasang.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def is_supported() -> bool:
    """SAPI hanya jalan di Windows yang punya PowerShell."""

    if not sys.platform.startswith("win"):
        return False
    return _powershell_path() is not None


def _powershell_path() -> str | None:
    for command in ("pwsh.exe", "pwsh", "powershell.exe", "powershell"):
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            full = Path(path_dir) / command
            if full.exists():
                return str(full)
    # Fallback paths khas Windows.
    candidates = [
        Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"),
        Path("C:/Program Files/PowerShell/7/pwsh.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _escape_for_single_quoted(value: str) -> str:
    """Escape value untuk dimasukkan ke PowerShell single-quoted string."""

    return value.replace("'", "''")


def synthesize_to_wav(
    text: str,
    output_path: str | Path,
    *,
    rate: int = 0,
    voice_hint: str | None = None,
) -> Path:
    """Sintesis teks ke WAV memakai System.Speech.Synthesis.

    rate: -10..10 (0 = default).
    voice_hint: substring nama voice. Misal "Zira" atau "Indonesian".
    """

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    pwsh = _powershell_path()
    if pwsh is None:
        raise RuntimeError("PowerShell tidak ditemukan untuk SAPI TTS.")

    safe_text = _escape_for_single_quoted(text)
    safe_path = _escape_for_single_quoted(str(output.resolve()))
    voice_block = ""
    if voice_hint:
        safe_voice = _escape_for_single_quoted(voice_hint)
        voice_block = (
            "$voices = $synth.GetInstalledVoices()\n"
            "foreach ($voice in $voices) {\n"
            f"    if ($voice.VoiceInfo.Name -like '*{safe_voice}*' -or "
            f"$voice.VoiceInfo.Culture.Name -like '*{safe_voice}*') {{\n"
            "        $synth.SelectVoice($voice.VoiceInfo.Name)\n"
            "        break\n"
            "    }\n"
            "}\n"
        )

    script = (
        "Add-Type -AssemblyName System.Speech\n"
        "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
        f"$synth.Rate = {int(rate)}\n"
        f"{voice_block}"
        f"$synth.SetOutputToWaveFile('{safe_path}')\n"
        f"$synth.Speak('{safe_text}')\n"
        "$synth.Dispose()\n"
    )

    proc = subprocess.run(
        [pwsh, "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0 or not output.exists():
        message = proc.stderr.strip() or proc.stdout.strip() or "SAPI gagal."
        raise RuntimeError(f"SAPI TTS gagal: {message}")
    return output
