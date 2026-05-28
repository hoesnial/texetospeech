"""Dataset prompt helpers for personal voice recording."""

from __future__ import annotations

import csv
from pathlib import Path

from .audio import RecordingResult, record_wav


PROMPTS: list[str] = [
    "nol",
    "satu",
    "dua",
    "tiga",
    "empat",
    "lima",
    "enam",
    "tujuh",
    "delapan",
    "sembilan",
    "sepuluh",
    "sebelas",
    "dua belas",
    "tiga belas",
    "empat belas",
    "lima belas",
    "enam belas",
    "tujuh belas",
    "delapan belas",
    "sembilan belas",
    "dua puluh",
    "dua puluh satu",
    "tiga puluh dua",
    "empat puluh tiga",
    "lima puluh empat",
    "enam puluh lima",
    "tujuh puluh enam",
    "delapan puluh tujuh",
    "sembilan puluh delapan",
    "seratus",
    "seratus satu",
    "seratus dua puluh tiga",
    "tambah",
    "kurang",
    "kali",
    "bagi",
    "sama dengan",
    "hasilnya",
    "jawabannya",
    "benar",
    "salah",
    "tidak dapat diproses",
    "hasil operasi ini bukan bilangan bulat",
    "satu tambah dua sama dengan tiga",
    "dua tambah tiga sama dengan lima",
    "tiga tambah empat sama dengan tujuh",
    "empat tambah lima sama dengan sembilan",
    "sepuluh kurang tiga sama dengan tujuh",
    "dua puluh kurang lima sama dengan lima belas",
    "tiga kali dua sama dengan enam",
    "empat kali lima sama dengan dua puluh",
    "dua puluh bagi lima sama dengan empat",
    "sembilan bagi tiga sama dengan tiga",
    "lima bagi dua tidak dapat diproses karena hasilnya bukan bilangan bulat",
    "satu tambah dua tambah tiga sama dengan enam",
    "Halo, nama saya sedang digunakan untuk sistem suara.",
    "Saya sedang membaca kalimat dengan jelas.",
    "Hari ini saya belajar membuat aplikasi speech to text dan text to speech.",
    "Sistem akan mendengarkan suara saya lalu mengubahnya menjadi teks.",
    "Setelah itu sistem menghitung operasi aritmetika dan membacakan hasilnya.",
    "Saya mengucapkan setiap kata dengan tempo yang stabil.",
    "Suara saya direkam di ruangan yang tenang.",
]


def write_prompts(path: str | Path) -> Path:
    """Write numbered prompts to a UTF-8 text file."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{index:03d}|{prompt}" for index, prompt in enumerate(PROMPTS, start=1)]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def read_prompts(path: str | Path = "data/dataset_prompts.txt") -> list[str]:
    """Read prompts from numbered `001|text` or plain one-prompt-per-line files."""

    prompt_path = Path(path)
    prompts: list[str] = []
    for raw_line in prompt_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "|" in line:
            _, prompt = line.split("|", 1)
            prompts.append(prompt.strip())
        else:
            prompts.append(line)
    return prompts


def append_metadata(
    dataset_dir: str | Path,
    *,
    index: int,
    prompt: str,
    audio_path: str | Path,
    backend: str,
) -> Path:
    """Append recording metadata as CSV."""

    output_dir = Path(dataset_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / "metadata.csv"
    needs_header = not metadata_path.exists()
    with metadata_path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["index", "audio_path", "prompt", "backend"],
        )
        if needs_header:
            writer.writeheader()
        writer.writerow(
            {
                "index": index,
                "audio_path": str(audio_path),
                "prompt": prompt,
                "backend": backend,
            }
        )
    return metadata_path


def record_prompt(
    dataset_dir: str | Path,
    *,
    index: int,
    prompt: str,
    seconds: float = 4,
    sample_rate: int = 22050,
) -> RecordingResult:
    """Record one prompt into a dataset directory and update metadata."""

    output_dir = Path(dataset_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / f"{index:03d}.wav"
    result = record_wav(audio_path, seconds=seconds, sample_rate=sample_rate)
    append_metadata(
        output_dir,
        index=index,
        prompt=prompt,
        audio_path=result.path,
        backend=result.backend,
    )
    return result


def export_training_dataset(
    dataset_dir: str | Path,
    output_dir: str | Path,
    *,
    sample_rate: int = 22050,
) -> Path:
    """Export recorded dataset to Piper training format (LJSpeech-like).

    Piper expects:
      output_dir/
        metadata.csv   (format: id|text)
        wav/           (WAV files named by id)

    Returns the output directory path.
    """

    source = Path(dataset_dir)
    output = Path(output_dir)
    wav_dir = output / "wav"
    wav_dir.mkdir(parents=True, exist_ok=True)

    metadata_csv = source / "metadata.csv"
    if not metadata_csv.exists():
        raise FileNotFoundError(
            f"metadata.csv tidak ditemukan di {source}. "
            f"Rekam dataset terlebih dahulu."
        )

    entries: list[tuple[str, str]] = []
    with metadata_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            audio_path = Path(row["audio_path"])
            if not audio_path.exists():
                # Try relative to project root
                audio_path = source / audio_path.name
            if not audio_path.exists():
                continue

            file_id = f"{int(row['index']):04d}"
            prompt = row["prompt"].strip()
            if not prompt:
                continue

            # Convert to normalized WAV
            target_wav = wav_dir / f"{file_id}.wav"
            from .audio import convert_to_wav
            convert_to_wav(audio_path, target_wav, sample_rate=sample_rate)
            entries.append((file_id, prompt))

    # Write Piper-format metadata (pipe-separated, no header)
    piper_metadata = output / "metadata.csv"
    with piper_metadata.open("w", encoding="utf-8") as f:
        for file_id, prompt in entries:
            f.write(f"{file_id}|{prompt}\n")

    return output
