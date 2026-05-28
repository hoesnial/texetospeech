from __future__ import annotations

import csv
import math
import tempfile
import unittest
import wave
from pathlib import Path

from texetospeech.personal_voice import (
    build_phrase_index,
    split_for_lookup,
    synthesize,
)


def _write_test_wav(
    path: Path,
    *,
    frequency: int = 440,
    duration_seconds: float = 0.2,
    sample_rate: int = 22050,
) -> None:
    total_frames = int(sample_rate * duration_seconds)
    with wave.open(str(path), "w") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        for frame in range(total_frames):
            sample = int(12000 * math.sin(2 * math.pi * frequency * frame / sample_rate))
            audio.writeframesraw(
                sample.to_bytes(2, byteorder="little", signed=True)
            )


def _make_dataset(
    root: Path,
    entries: list[tuple[int, str, int]],
) -> Path:
    """entries = list of (index, prompt, frequency)."""

    root.mkdir(parents=True, exist_ok=True)
    metadata_path = root / "metadata.csv"
    with metadata_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["index", "audio_path", "prompt", "backend"],
        )
        writer.writeheader()
        for index, prompt, frequency in entries:
            wav_path = root / f"{index:03d}.wav"
            _write_test_wav(wav_path, frequency=frequency)
            writer.writerow(
                {
                    "index": index,
                    "audio_path": str(wav_path),
                    "prompt": prompt,
                    "backend": "test",
                }
            )
    return root


class PersonalVoiceTest(unittest.TestCase):
    def test_build_phrase_index_normalizes_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = _make_dataset(
                Path(temp_dir) / "dataset",
                [
                    (1, "Satu", 220),
                    (2, "tambah", 330),
                    (3, "Dua", 440),
                ],
            )
            index = build_phrase_index([dataset])
            self.assertIn("satu", index)
            self.assertIn("tambah", index)
            self.assertIn("dua", index)

    def test_split_for_lookup_prefers_longer_phrases(self) -> None:
        index = {
            "satu": Path("a.wav"),
            "tambah": Path("b.wav"),
            "dua": Path("c.wav"),
            "satu tambah dua sama dengan tiga": Path("d.wav"),
            "sama dengan": Path("e.wav"),
            "tiga": Path("f.wav"),
        }
        matched, missing = split_for_lookup(
            "satu tambah dua sama dengan tiga", index
        )
        self.assertEqual(matched, ["satu tambah dua sama dengan tiga"])
        self.assertEqual(missing, [])

    def test_split_for_lookup_falls_back_to_words(self) -> None:
        index = {
            "satu": Path("a.wav"),
            "tambah": Path("b.wav"),
            "dua": Path("c.wav"),
            "sama dengan": Path("e.wav"),
            "tiga": Path("f.wav"),
        }
        matched, missing = split_for_lookup(
            "satu tambah dua sama dengan tiga", index
        )
        self.assertEqual(
            matched,
            ["satu", "tambah", "dua", "sama dengan", "tiga"],
        )
        self.assertEqual(missing, [])

    def test_synthesize_produces_valid_wav(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = _make_dataset(
                root / "dataset",
                [
                    (1, "satu", 220),
                    (2, "tambah", 330),
                    (3, "dua", 440),
                    (4, "sama dengan", 550),
                    (5, "tiga", 660),
                ],
            )
            output = root / "out.wav"
            result = synthesize(
                "satu tambah dua sama dengan tiga",
                output,
                dataset_dirs=[dataset],
            )
            self.assertTrue(output.exists())
            self.assertEqual(
                result.matched_phrases,
                ["satu", "tambah", "dua", "sama dengan", "tiga"],
            )
            self.assertEqual(result.missing_phrases, [])

            with wave.open(str(output), "rb") as audio:
                self.assertEqual(audio.getnchannels(), 1)
                self.assertEqual(audio.getsampwidth(), 2)
                self.assertEqual(audio.getframerate(), 22050)
                # Should have non-trivial length (multiple clips concatenated).
                self.assertGreater(audio.getnframes(), 22050 // 4)

    def test_synthesize_records_missing_words(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = _make_dataset(
                root / "dataset",
                [
                    (1, "satu", 220),
                    (2, "tambah", 330),
                ],
            )
            output = root / "out.wav"
            result = synthesize(
                "satu tambah duaribu",
                output,
                dataset_dirs=[dataset],
            )
            self.assertEqual(result.matched_phrases, ["satu", "tambah"])
            self.assertEqual(result.missing_phrases, ["duaribu"])


if __name__ == "__main__":
    unittest.main()
