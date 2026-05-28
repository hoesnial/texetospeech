"""End-to-end test alur PRD tanpa ffmpeg / torch / Coqui."""

from __future__ import annotations

import csv
import math
import os
import tempfile
import unittest
import wave
from pathlib import Path

from texetospeech.audio import build_voice_profile
from texetospeech.dataset import PROMPTS_MVP
from texetospeech.speech import speak_text


SAMPLE_RATE = 22050


def _write_sine_wav(path: Path, frequency: int, duration: float = 0.4) -> None:
    total = int(SAMPLE_RATE * duration)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(SAMPLE_RATE)
        for frame in range(total):
            value = int(
                12000 * math.sin(2 * math.pi * frequency * frame / SAMPLE_RATE)
            )
            audio.writeframesraw(value.to_bytes(2, byteorder="little", signed=True))


def _seed_dataset(dataset_dir: Path) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = dataset_dir / "metadata.csv"
    with metadata_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["index", "audio_path", "prompt", "backend"]
        )
        writer.writeheader()
        for index, prompt in enumerate(PROMPTS_MVP, start=1):
            wav_path = dataset_dir / f"{index:03d}.wav"
            _write_sine_wav(wav_path, frequency=200 + 20 * index)
            writer.writerow(
                {
                    "index": index,
                    "audio_path": str(wav_path),
                    "prompt": prompt,
                    "backend": "test",
                }
            )


class EndToEndTest(unittest.TestCase):
    def test_full_personal_voice_flow_without_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset_dir = root / "recordings" / "browser_dataset"
            profile_dir = root / "voice_profiles" / "default"
            output_dir = root / "audio"

            _seed_dataset(dataset_dir)

            # Build voice profile (langkah ini dulu butuh ffmpeg).
            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                profile = build_voice_profile(
                    dataset_dir,
                    profile_dir,
                    name="e2e",
                    max_files=10,
                )
                self.assertTrue(Path(profile.reference_wav).exists())
                self.assertEqual(profile.source_count, 10)

                # Personal voice TTS langsung pakai dataset.
                output_path = output_dir / "answer.wav"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                result = speak_text(
                    "satu tambah dua sama dengan tiga",
                    output_path=output_path,
                    voice_reference=str(profile.reference_wav),
                )
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(result.backend, "personal-voice")
            self.assertTrue(Path(result.output_path).exists())
            with wave.open(result.output_path, "rb") as audio:
                self.assertEqual(audio.getnchannels(), 1)
                self.assertEqual(audio.getsampwidth(), 2)
                self.assertEqual(audio.getframerate(), SAMPLE_RATE)


if __name__ == "__main__":
    unittest.main()
