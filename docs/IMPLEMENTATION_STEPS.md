# Langkah Implementasi TexeToSpeech

Dokumen ini adalah urutan eksekusi agar sistem pada PRD selesai dari MVP sampai alur speech to text to speech.

## 1. Cek Kesiapan Sistem

Jika `.venv` sudah dibuat, gunakan Python dari venv:

```bash
.venv/bin/python -m texetospeech.cli doctor
```

Jika belum memakai venv, mode source juga bisa:

```bash
PYTHONPATH=src python3 -m texetospeech.cli doctor
```

Yang wajib untuk MVP lokal:

- `espeak-ng` atau `espeak` untuk TTS standar.
- `ffmpeg` untuk konversi audio.
- `arecord` atau browser untuk rekam suara.

Yang opsional:

- `whisper` atau package `openai-whisper` untuk STT file audio.
- `SpeechRecognition` untuk STT Google/mikrofon.
- `TTS` untuk voice cloning Coqui XTTS.

## 2. Jalankan Core Aritmetika

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "satu tambah dua tambah tiga"
```

Expected:

```text
satu tambah dua tambah tiga sama dengan enam.
```

Cek jawaban:

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "satu tambah dua tambah tiga sama dengan enam"
```

Tolak pecahan:

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "lima bagi dua"
```

Expected:

```text
Hasil operasi ini bukan bilangan bulat, jadi tidak dapat diproses.
```

## 3. Jalankan TTS Standar

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "satu tambah dua" --speak --out audio/jawaban.wav
```

Jika berhasil, file audio tersimpan di:

```text
audio/jawaban.wav
```

## 4. Jalankan Web App

```bash
PYTHONPATH=src python3 -m texetospeech.cli web --port 8765
```

Buka:

```text
http://127.0.0.1:8765
```

Fitur web app:

- input teks aritmetika,
- hasil perhitungan,
- audio TTS,
- rekam suara dari browser,
- upload audio untuk STT,
- rekam dataset suara per prompt,
- build voice profile.

## 5. Rekam Dataset Suara

Cara CLI:

```bash
PYTHONPATH=src python3 -m texetospeech.cli record-dataset --out recordings/my_voice --seconds 4
```

Cara web:

1. Jalankan web app.
2. Buka bagian `Dataset Suara Saya`.
3. Klik `Rekam Prompt`.
4. Bacakan prompt yang tampil.
5. Klik `Stop Rekam`.
6. Ulangi minimal 5-10 menit audio bersih.

Output dataset:

```text
recordings/my_voice/
recordings/browser_dataset/
```

## 6. Build Voice Profile

Untuk dataset dari CLI:

```bash
PYTHONPATH=src python3 -m texetospeech.cli build-profile --dataset recordings/my_voice --out voice_profiles/default
```

Untuk dataset dari web:

```bash
PYTHONPATH=src python3 -m texetospeech.cli build-profile --dataset recordings/browser_dataset --out voice_profiles/default
```

Output:

```text
voice_profiles/default/speaker_reference.wav
voice_profiles/default/profile.json
```

## 7. Aktifkan STT Audio Asli

Di repo ini backend STT ringan sudah bisa dipasang di `.venv`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[speech]"
.venv/bin/python -m texetospeech.cli doctor
```

Pilihan 1, Whisper CLI:

```bash
pipx install openai-whisper
```

Lalu:

```bash
PYTHONPATH=src python3 -m texetospeech.cli listen --audio rekaman.wav --speak --out audio/jawaban.wav
```

Pilihan 2, package Python:

```bash
python3 -m pip install -e ".[stt]"
```

Pilihan 3, SpeechRecognition:

```bash
python3 -m pip install -e ".[speech]"
```

Catatan: STT Google membutuhkan koneksi internet.

Setelah `SpeechRecognition` aktif, jalankan STT file audio:

```bash
.venv/bin/python -m texetospeech.cli listen --audio uploads/contoh.webm --speak --out audio/jawaban.wav
```

Jika output berbunyi `Maaf, suara belum terbaca dengan jelas`, backend sudah tersedia tetapi audio belum cukup jelas untuk dikenali.

## 8. Aktifkan Voice Cloning

Sistem otomatis memilih backend voice cloning berdasarkan spek device:

### Opsi A: Piper TTS (Laptop Low-End, RAM < 3GB)

Paling ringan, model ~50MB, real-time di CPU:

```bash
python3 -m pip install -e ".[voice-light]"
```

Atau install Piper CLI:

```bash
pip install piper-tts
```

Download model Indonesia:

```bash
mkdir -p models/piper
# Download dari https://github.com/rhasspy/piper/releases
# Pilih model id_ID (Indonesian)
```

Gunakan:

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "satu tambah dua" --speak --out audio/clone.wav --voice-reference voice_profiles/default/speaker_reference.wav
```

### Opsi B: Coqui VITS (Laptop Medium, RAM 3-4GB)

Lebih ringan dari XTTS, mendukung speaker embedding:

```bash
python3 -m pip install -e ".[voice-medium]"
```

Gunakan:

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "satu tambah dua" --speak --out audio/clone.wav --voice-reference voice_profiles/default/speaker_reference.wav
```

### Opsi C: Coqui XTTS v2 (PC/Laptop dengan GPU atau RAM 6GB+)

Kualitas voice cloning terbaik tapi paling berat:

```bash
python3 -m pip install -e ".[voice]"
```

Gunakan:

```bash
PYTHONPATH=src python3 -m texetospeech.cli text "satu tambah dua" --speak --out audio/clone.wav --voice-reference voice_profiles/default/speaker_reference.wav
```

### Memaksa Backend Tertentu

Set environment variable untuk memaksa pilihan backend:

```bash
# Paksa Piper (paling ringan)
TEXETOSPEECH_TTS_BACKEND=piper python3 -m texetospeech.cli text "satu tambah dua" --speak --out audio/clone.wav --voice-reference voice_profiles/default/speaker_reference.wav

# Paksa VITS (medium)
TEXETOSPEECH_TTS_BACKEND=coqui-vits python3 -m texetospeech.cli text "satu tambah dua" --speak --out audio/clone.wav --voice-reference voice_profiles/default/speaker_reference.wav

# Paksa XTTS (berat)
TEXETOSPEECH_TTS_BACKEND=coqui-xtts python3 -m texetospeech.cli text "satu tambah dua" --speak --out audio/clone.wav --voice-reference voice_profiles/default/speaker_reference.wav
```

### Cek Backend Yang Dipilih

```bash
PYTHONPATH=src python3 -m texetospeech.cli doctor
```

Output akan menunjukkan backend mana yang dipilih otomatis berdasarkan RAM dan GPU.

Catatan: di Python 3.14, gunakan `coqui-tts` dan pastikan `torch`, `torchaudio`, dan `torchcodec` sudah terpasang di venv. Untuk environment CPU-only, pasang wheel CPU PyTorch secara manual jika diperlukan.

## 9. Fine-Tune Model Suara Sendiri (Opsional)

Agar output TTS benar-benar mirip suaramu, fine-tune model Piper di Google Colab:

### Export dataset untuk training:

```bash
.venv/bin/python -m texetospeech.cli export-training-dataset \
  --dataset recordings/browser_dataset \
  --out training_export
```

### Upload dan training:

1. Upload folder `training_export/` ke Google Drive.
2. Buka panduan lengkap di `docs/TRAINING_VOICE.md`.
3. Jalankan training di Colab (gratis, pakai GPU T4).
4. Download `piper_model.onnx` dan `piper_model.onnx.json`.
5. Taruh di `voice_profiles/default/`.

### Test model custom:

```bash
.venv/bin/python -m texetospeech.cli text "satu tambah dua" \
  --speak --out audio/custom_voice.wav \
  --voice-reference voice_profiles/default/speaker_reference.wav
```

Sistem otomatis mendeteksi `piper_model.onnx` dan menggunakannya.

## 10. Jalankan Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Target saat ini:

- parser angka dan operator lolos,
- kalkulator bilangan bulat lolos,
- penolakan pecahan lolos,
- dataset helper lolos,
- build voice profile lolos jika `ffmpeg` tersedia.
