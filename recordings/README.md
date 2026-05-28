# recordings/

Folder ini menyimpan dataset rekaman suara pribadi.

- `recordings/browser_dataset/` — diisi otomatis oleh web app saat klik "Rekam Prompt".
- `recordings/my_voice/` — diisi oleh CLI `texetospeech record-dataset`.

## Penting

- **Jangan dihapus.** Personal voice TTS dan personal STT membaca dataset dari sini.
- Setelah rekam, akan muncul `metadata.csv` plus banyak file `001.wav`, `002.wav`, dst.
- Untuk membuat ulang dataset MVP (angka 0..10 + operator), buka web app dan rekam ulang prompt-nya.

## Cara cek dataset masih ada

```bash
PYTHONPATH=src python -m texetospeech.cli doctor
```

Cari baris `personal voice` dan `personal STT`. Jika kedua status tertulis "siap" atau menampilkan jumlah frasa, dataset valid.
