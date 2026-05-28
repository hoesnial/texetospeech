from __future__ import annotations

import math
import tempfile
import unittest
import wave
from pathlib import Path

from texetospeech.audio import build_voice_profile, convert_to_wav
from texetospeech.dataset import append_metadata, read_prompts


class DatasetAudioTest(unittest.TestCase):
    def test_read_prompts_numbered_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_path = Path(temp_dir) / "prompts.txt"
            prompt_path.write_text("001|satu\n002|dua tambah dua\n", encoding="utf-8")
            self.assertEqual(read_prompts(prompt_path), ["satu", "dua tambah dua"])

    def test_append_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = append_metadata(
                temp_dir,
                index=1,
                prompt="satu",
                audio_path="recordings/001.wav",
                backend="test",
            )
            text = metadata_path.read_text(encoding="utf-8")
            self.assertIn("index,audio_path,prompt,backend", text)
            self.assertIn("1,recordings/001.wav,satu,test", text)

    def test_build_voice_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "dataset"
            profile = root / "profile"
            dataset.mkdir()
            _write_test_wav(dataset / "001.wav")
            _write_test_wav(dataset / "002.wav", frequency=660)

            result = build_voice_profile(dataset, profile, name="test")

            self.assertEqual(result.source_count, 2)
            self.assertTrue((profile / "speaker_reference.wav").exists())
            self.assertTrue((profile / "profile.json").exists())

    def test_convert_to_wav_handles_existing_wav_without_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "in.wav"
            target = root / "out.wav"
            _write_test_wav(source, frequency=440)

            result = convert_to_wav(source, target, sample_rate=22050)
            self.assertTrue(result.exists())
            with wave.open(str(result), "rb") as audio:
                self.assertEqual(audio.getnchannels(), 1)
                self.assertEqual(audio.getsampwidth(), 2)
                self.assertEqual(audio.getframerate(), 22050)


def _write_test_wav(path: Path, *, frequency: int = 440) -> None:
    sample_rate = 22050
    duration_seconds = 0.1
    total_frames = int(sample_rate * duration_seconds)
    with wave.open(str(path), "w") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        for frame in range(total_frames):
            sample = int(12000 * math.sin(2 * math.pi * frequency * frame / sample_rate))
            audio.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))


if __name__ == "__main__":
    unittest.main()

