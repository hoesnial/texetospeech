# TexeToSpeech

MVP **Text to Speech dan Speech to Text Aritmetika Bahasa Indonesia** sesuai PRD di [docs/PRD-text-to-speech-stt.md](docs/PRD-text-to-speech-stt.md).

Panduan eksekusi step-by-step tersedia di [docs/IMPLEMENTATION_STEPS.md](docs/IMPLEMENTATION_STEPS.md).

Sistem ini sudah mendukung:

- parsing angka Bahasa Indonesia dan digit,
- operator `tambah`, `kurang`, `kali`, `bagi`,
- validasi hasil agar tetap bilangan bulat,
- pengecekan jawaban dengan frasa `sama dengan`,
- CLI untuk teks, STT opsional, TTS, dan web app lokal,
- rekam dataset suara pribadi,
- build `speaker_reference.wav` untuk voice cloning opsional.

## Jalankan Tanpa Install

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "satu tambah dua tambah tiga"
```

Atau install dulu dalam mode editable:

```bash
python3 -m pip install -e .
texetospeech text "satu tambah dua tambah tiga"
```

Output:

```text
satu tambah dua tambah tiga sama dengan enam.
```

## Contoh Perintah

Hitung input teks:

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "dua tambah tiga kali empat"
```

Cek jawaban:

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "satu tambah dua sama dengan tiga"
```

Tolak hasil pecahan:

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "lima bagi dua"
```

Buat output JSON:

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "satu tambah dua" --json
```

Bacakan hasil dengan TTS jika backend audio tersedia:

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "satu tambah dua" --speak
```

Simpan audio TTS ke file jika `espeak` atau `espeak-ng` tersedia:

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "satu tambah dua" --speak --out audio/jawaban.wav
```

Transkrip audio memakai backend STT opsional:

```bash
PYTHONPATH=src python3 -m texetospeech.cli listen --audio rekaman.wav
```

Untuk demo tanpa backend STT, gunakan file teks sebagai transkrip:

```bash
printf "dua tambah dua\n" > sample.txt
PYTHONPATH=src python3 -m texetospeech.cli listen --audio sample.txt
```

Ekspor prompt dataset suara:

```bash
PYTHONPATH=src python3 -m texetospeech.cli dataset-prompts --out data/dataset_prompts.txt
```

## Jalankan Web App

```bash
PYTHONPATH=src python3 -m texetospeech.cli web --port 8765
```

Buka:

```text
http://127.0.0.1:8765
```

Di web app kamu bisa:

- mengetik operasi aritmetika,
- membuat audio TTS,
- merekam suara dari browser untuk STT,
- merekam dataset suara per prompt,
- membuat voice profile dari dataset.

## Cek Kesiapan Sistem

```bash
PYTHONPATH=src python3 -m texetospeech.cli doctor
```

Perintah ini mengecek backend lokal seperti `espeak-ng`, `ffmpeg`, `arecord`, `whisper`, package Python STT, dan file `voice_profiles/default/speaker_reference.wav`.

## Backend Suara Opsional

Core aritmetika tidak membutuhkan dependency eksternal.

Untuk TTS:

- Linux: install `espeak-ng` atau `espeak`.
- Python opsional: install extra `speech` untuk mencoba `pyttsx3`.

Untuk STT:

- Jika ada command `whisper`, sistem akan mencoba memakainya untuk file audio.
- Jika package `openai-whisper` tersedia, sistem akan mencoba memakainya untuk file audio.
- Jika package `SpeechRecognition` tersedia, sistem bisa memakai Google Speech Recognition atau mikrofon.

Untuk voice cloning mirip suara kamu:

- Rekam dataset terlebih dahulu.
- Build voice profile menjadi `voice_profiles/default/speaker_reference.wav`.
- Install backend Coqui TTS/XTTS jika kompatibel dengan Python di mesinmu.
- Saat backend tersedia, gunakan opsi `--voice-reference` atau centang `pakai voice profile` di web app.

Install mode editable:

```bash
python3 -m pip install -e .
```

Install dependency suara opsional:

```bash
python3 -m pip install -e ".[speech]"
```

Jika Python sistem menolak install karena `externally-managed-environment`, gunakan venv lokal:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[speech]"
.venv/bin/python -m texetospeech.cli doctor
```

Install Whisper Python opsional untuk STT file audio:

```bash
python3 -m pip install -e ".[stt]"
```

Install backend voice cloning opsional:

```bash
python3 -m pip install -e ".[voice]"
```

Di Python 3.14, gunakan `coqui-tts` versi baru. Paket ini tetap diakses lewat `from TTS.api import TTS`, tetapi perlu PyTorch CPU dan `torchcodec` terpasang di venv.

## Dataset Suara Pribadi

Prompt dataset tersedia di [data/dataset_prompts.txt](data/dataset_prompts.txt).

Rekomendasi rekaman:

- format `wav`,
- mono,
- 16-bit,
- 22050 Hz atau 44100 Hz,
- ruangan tenang,
- tempo bicara stabil.

Minimal untuk percobaan awal: 5 sampai 10 menit. Lebih baik: 30 sampai 60 menit.

Rekam satu file cepat:

```bash
PYTHONPATH=src python3 -m texetospeech.cli record --out recordings/test.wav --seconds 4
```

Rekam dataset dari prompt:

```bash
PYTHONPATH=src python3 -m texetospeech.cli record-dataset --out recordings/my_voice --seconds 4
```

Coba beberapa prompt dulu:

```bash
PYTHONPATH=src python3 -m texetospeech.cli record-dataset --out recordings/my_voice --seconds 4 --limit 5
```

Buat voice profile:

```bash
PYTHONPATH=src python3 -m texetospeech.cli build-profile --dataset recordings/my_voice --out voice_profiles/default
```

Gunakan voice profile untuk TTS jika backend voice cloning tersedia:

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "satu tambah dua" --speak --out audio/jawaban.wav --voice-reference voice_profiles/default/speaker_reference.wav
```

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```
