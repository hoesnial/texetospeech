# Panduan Fine-Tune Piper TTS dengan Suara Sendiri

Panduan ini menjelaskan cara melatih model Piper TTS agar output suaranya mirip suaramu.
Proses training dilakukan di **Google Colab** (gratis, pakai GPU cloud), jadi laptop low-spec tidak masalah.

## Prasyarat

1. Dataset suara sudah direkam (minimal 5-10 menit audio bersih)
2. File `recordings/browser_dataset/metadata.csv` sudah ada
3. Akun Google untuk akses Colab

## Alur Kerja

```text
1. Rekam dataset suara (di laptop, lewat web app)
2. Upload dataset ke Google Drive
3. Buka notebook Colab → jalankan training
4. Download model .onnx hasil training
5. Taruh di voice_profiles/default/piper_model.onnx
6. Sistem otomatis pakai model custom
```

## Langkah 1: Siapkan Dataset

Pastikan kamu sudah punya rekaman di `recordings/browser_dataset/`:

```bash
.venv/bin/python -m texetospeech.cli web --port 8765
```

Buka http://127.0.0.1:8765, rekam semua prompt di bagian "Dataset Suara Saya".
Minimal 5-10 menit, idealnya 30+ menit untuk kualitas terbaik.

## Langkah 2: Export Dataset untuk Training

Jalankan script export:

```bash
.venv/bin/python -m texetospeech.cli export-training-dataset \
  --dataset recordings/browser_dataset \
  --out training_export
```

Ini akan menghasilkan folder `training_export/` berisi:
- `metadata.csv` (format: `id|text`)
- `wav/` (file WAV yang sudah dinormalisasi)

## Langkah 3: Upload ke Google Drive

Upload folder `training_export/` ke Google Drive kamu.

## Langkah 4: Jalankan Training di Google Colab

Buka notebook berikut di Google Colab:

**File:** `docs/piper_finetune_colab.ipynb` (ada di repo ini)

Atau buat notebook baru dan paste cell-cell berikut:

### Cell 1: Setup Environment

```python
# Install piper-train dan dependencies
!pip install piper-tts piper-phonemize onnx onnxruntime
!pip install pytorch-lightning==1.9.5
!pip install git+https://github.com/rhasspy/piper.git#subdirectory=src/python

# Install espeak-ng
!apt-get install -y espeak-ng

# Build monotonic align
import subprocess, os
os.chdir("/content")
!git clone https://github.com/rhasspy/piper.git
os.chdir("/content/piper/src/python")
!bash build_monotonic_align.sh
!pip install -e .
```

### Cell 2: Mount Google Drive

```python
from google.colab import drive
drive.mount('/content/drive')

# Path ke dataset kamu di Google Drive
DATASET_DIR = "/content/drive/MyDrive/training_export"
TRAINING_DIR = "/content/piper_training"
```

### Cell 3: Download Checkpoint untuk Fine-Tune

```python
import urllib.request
import os

os.makedirs("/content/checkpoints", exist_ok=True)

# Download Indonesian medium checkpoint (atau gunakan yang paling dekat)
# Cek https://huggingface.co/datasets/rhasspy/piper-checkpoints/tree/main
CHECKPOINT_URL = "https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/id/id_ID/news_tts/medium/epoch=4174-step=838782.ckpt"
CHECKPOINT_PATH = "/content/checkpoints/id_ID-news_tts-medium.ckpt"

if not os.path.exists(CHECKPOINT_PATH):
    print("Downloading checkpoint...")
    urllib.request.urlretrieve(CHECKPOINT_URL, CHECKPOINT_PATH)
    print("Done!")
```

### Cell 4: Preprocess Dataset

```python
!python3 -m piper_train.preprocess \
  --language id \
  --input-dir "{DATASET_DIR}" \
  --output-dir "{TRAINING_DIR}" \
  --dataset-format ljspeech \
  --single-speaker \
  --sample-rate 22050
```

### Cell 5: Mulai Training (Fine-Tune)

```python
!python3 -m piper_train \
    --dataset-dir "{TRAINING_DIR}" \
    --accelerator 'gpu' \
    --devices 1 \
    --batch-size 16 \
    --validation-split 0.0 \
    --num-test-examples 0 \
    --max_epochs 1000 \
    --resume_from_checkpoint "{CHECKPOINT_PATH}" \
    --checkpoint-epochs 100 \
    --precision 32
```

> Training 1000 epoch biasanya cukup untuk fine-tune.
> Di Colab GPU gratis (T4), ini butuh sekitar 2-4 jam tergantung ukuran dataset.

### Cell 6: Export ke ONNX

```python
import glob

# Cari checkpoint terakhir
checkpoints = sorted(glob.glob(f"{TRAINING_DIR}/lightning_logs/version_0/checkpoints/*.ckpt"))
latest_ckpt = checkpoints[-1]
print(f"Using checkpoint: {latest_ckpt}")

OUTPUT_ONNX = "/content/drive/MyDrive/piper_model.onnx"

!python3 -m piper_train.export_onnx \
    "{latest_ckpt}" \
    "{OUTPUT_ONNX}"

# Copy config
!cp "{TRAINING_DIR}/config.json" "{OUTPUT_ONNX}.json"

print(f"\nModel tersimpan di Google Drive: piper_model.onnx")
print(f"Config tersimpan di Google Drive: piper_model.onnx.json")
```

## Langkah 5: Download dan Pasang Model

Setelah training selesai, download dari Google Drive:
- `piper_model.onnx`
- `piper_model.onnx.json`

Taruh di project:

```bash
cp ~/Downloads/piper_model.onnx voice_profiles/default/piper_model.onnx
cp ~/Downloads/piper_model.onnx.json voice_profiles/default/piper_model.onnx.json
```

## Langkah 6: Test

```bash
.venv/bin/python -m texetospeech.cli text "satu tambah dua" \
  --speak --out audio/test_custom.wav \
  --voice-reference voice_profiles/default/speaker_reference.wav
```

Sistem akan otomatis mendeteksi `voice_profiles/default/piper_model.onnx` dan menggunakannya.

## Tips

- **Dataset lebih banyak = suara lebih mirip.** 30 menit audio bersih sudah sangat bagus.
- **Epoch 500-1000** biasanya cukup untuk fine-tune. Lebih dari itu bisa overfitting.
- **Cek loss** di tensorboard. Training "selesai" ketika `loss_disc_all` sudah stabil.
- **Jangan training dari nol** — selalu fine-tune dari checkpoint yang sudah ada.
- **Colab gratis** punya batas waktu ~12 jam. Untuk dataset besar, simpan checkpoint berkala.

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Colab disconnect | Simpan checkpoint ke Drive, lanjutkan dari checkpoint terakhir |
| Out of memory | Kurangi `--batch-size` ke 8 atau 4 |
| Suara masih belum mirip | Tambah epoch atau tambah data rekaman |
| Model terlalu besar | Gunakan quality `medium` (default), bukan `high` |
| espeak-ng error | Pastikan `--language id` (bukan `id-ID`) |
