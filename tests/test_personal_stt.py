from __future__ import annotations

import csv
import math
import tempfile
import unittest
import wave
from pathlib import Path

from texetospeech.personal_stt import transcribe


SAMPLE_RATE = 16000


def _write_wav(
    path: Path,
    *,
    samples: list[int],
    sample_rate: int = SAMPLE_RATE,
) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        for value in samples:
            if value > 32767:
                value = 32767
            elif value < -32768:
                value = -32768
            audio.writeframesraw(value.to_bytes(2, byteorder="little", signed=True))


def _tone(frequency: int, duration: float, *, amplitude: int = 12000) -> list[int]:
    total = int(SAMPLE_RATE * duration)
    return [
        int(amplitude * math.sin(2 * math.pi * frequency * frame / SAMPLE_RATE))
        for frame in range(total)
    ]


def _silence(duration: float) -> list[int]:
    return [0] * int(SAMPLE_RATE * duration)


def _seed_dataset(
    dataset_dir: Path,
    word_to_freq: dict[str, int],
) -> Path:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = dataset_dir / "metadata.csv"
    with metadata_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["index", "audio_path", "prompt", "backend"]
        )
        writer.writeheader()
        for index, (word, freq) in enumerate(word_to_freq.items(), start=1):
            wav_path = dataset_dir / f"{index:03d}.wav"
            samples = _tone(freq, 0.6)
            _write_wav(wav_path, samples=samples)
            writer.writerow(
                {
                    "index": index,
                    "audio_path": str(wav_path),
                    "prompt": word,
                    "backend": "test",
                }
            )
    return dataset_dir


class PersonalSTTTest(unittest.TestCase):
    def test_transcribe_recognises_known_keywords(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "dataset"
            _seed_dataset(
                dataset,
                {
                    "satu": 220,
                    "dua": 330,
                    "tiga": 440,
                    "tambah": 550,
                    "kurang": 660,
                },
            )

            # Audio masuk: "satu tambah dua" disusun dengan tone yang sama
            # seperti template + jeda diam di antaranya.
            test_audio = root / "input.wav"
            samples: list[int] = []
            samples.extend(_tone(220, 0.5))
            samples.extend(_silence(0.2))
            samples.extend(_tone(550, 0.5))
            samples.extend(_silence(0.2))
            samples.extend(_tone(330, 0.5))
            _write_wav(test_audio, samples=samples)

            result = transcribe(test_audio, dataset_dirs=[dataset])
            self.assertEqual(result.text, "satu tambah dua")
            self.assertEqual(result.matched_count, 3)
            self.assertGreater(result.similarity_min, 0.9)


if __name__ == "__main__":
    unittest.main()
