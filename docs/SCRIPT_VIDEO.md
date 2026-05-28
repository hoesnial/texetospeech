# Script Narasi Video Demo TexeToSpeech

Durasi target: 4–5 menit. Fokus: Speech to Text lalu Text to Speech, dataset bilangan asli 0..10 dan operator + - * :, pengisi suara sendiri.

> Catatan: `[ACTION]` artinya jeda untuk lakukan aksi di layar.
> `[CUT]` artinya tempat editing untuk potong jeda menunggu.

---

## SCENE 1 — Intro (0:00–0:30)

**[ACTION: Tampilkan judul aplikasi]**

> Halo. Saya akan mendemokan aplikasi Speech to Text dan Text to Speech untuk operasi aritmetika Bahasa Indonesia.

> Aplikasi ini menerima input suara saya, mengubahnya menjadi teks, menghitung hasilnya, lalu membacakan jawabannya. Vocabulary-nya bilangan asli nol sampai sepuluh, dengan operator tambah, kurang, kali, dan bagi. Yang spesial: pengisi suara output adalah suara saya sendiri, dari dataset rekaman yang sudah saya buat.

---

## SCENE 2 — Dataset Suara Sendiri (0:30–1:15)

**[ACTION: Buka file explorer ke folder recordings/browser_dataset/]**

> Pertama, saya tunjukkan dataset suara saya. Ada di folder `recordings/browser_dataset`.

**[ACTION: Tampilkan daftar file WAV]**

> Saya merekam suara saya membacakan tiap kata yang dibutuhkan: angka nol, satu, dua, tiga, sampai sepuluh, lalu operator tambah, kurang, kali, bagi, dan frasa sama dengan. Total ada sekitar 30 file WAV plus satu file metadata.csv yang menghubungkan tiap file ke kata yang diucapkan.

> Rekamannya saya buat lewat web app aplikasi ini, di bagian Dataset Suara Saya. Cukup klik Rekam Prompt, bacakan kata yang muncul, klik Stop. Browser menyimpan WAV langsung tanpa butuh tools tambahan.

---

## SCENE 3 — Demo Speech to Text + Aritmetika (1:15–3:00)

**[ACTION: Buka browser ke http://127.0.0.1:8765]**

> Sekarang demo intinya. Saya buka web app di port 8765.

**[ACTION: Sorot bagian "Speech to Text + Aritmetika"]**

> Bagian Speech to Text + Aritmetika ini yang akan saya pakai. Cara kerjanya: saya rekam suara, sistem mentranskripsi pakai faster-whisper, lalu langsung dihitung.

**[ACTION: Klik Mulai Rekam]**

> Klik Mulai Rekam.

**[ACTION: Ucapkan dengan jeda jelas antar kata]**

> "satu... tambah... dua... tambah... tiga"

**[ACTION: Klik Stop Rekam, tunggu transkripsi]**

> Stop Rekam.

**[CUT: tunggu hasil muncul]**

**[ACTION: Tunjukkan output di layar]**

> Hasilnya muncul. Transkrip suara saya: "satu tambah dua tambah tiga". Ekspresi: 1 plus 2 plus 3. Hasilnya 6, atau dalam kata: enam.

> Coba operasi yang lebih variatif. Kali ini saya pakai operator kali.

**[ACTION: Klik Mulai Rekam]**

> "tiga... kali... dua"

**[ACTION: Klik Stop Rekam]**

**[CUT: tunggu hasil]**

> Output: tiga kali dua sama dengan enam. Kali ini saya coba pembagian.

**[ACTION: Klik Mulai Rekam]**

> "sepuluh... bagi... dua"

**[ACTION: Klik Stop Rekam]**

**[CUT]**

> Sepuluh bagi dua sama dengan lima. Bilangan bulat, jadi diterima.

> Sistem juga akan menolak hasil pecahan. Misalnya kalau saya bilang lima bagi dua, hasilnya dua koma lima — sistem akan menolaknya. Saya skip demo itu untuk hemat waktu.

---

## SCENE 4 — Demo Text to Speech dengan Suara Sendiri (3:00–4:15)

**[ACTION: Sorot bagian "Text to Speech Aritmetika"]**

> Selanjutnya Text to Speech dengan suara saya sendiri.

**[ACTION: Centang opsi "pakai suara saya (personal voice / dataset)"]**

> Saya centang opsi "pakai suara saya". Opsi ini membuat sistem mengambil potongan rekaman dari dataset saya, lalu menggabungkannya menjadi audio jawaban. Tidak butuh model neural, tidak butuh GPU, hanya butuh dataset rekaman tadi.

**[ACTION: Ketik input "satu tambah dua tambah tiga" di kotak teks]**

> Saya ketik `satu tambah dua tambah tiga` di kotak input.

**[ACTION: Klik tombol Hitung + Audio]**

> Klik Hitung + Audio.

**[CUT: tunggu audio diputar]**

**[ACTION: Audio diputar, biarkan terdengar]**

> Dengarkan.

**[CUT: putar audio personal voice]**

> Itu suara saya sendiri. Sistem mengambil rekaman kata "satu", "tambah", "dua", "tambah", "tiga", "sama dengan", "enam" dari dataset, lalu menyatukannya jadi satu audio dengan crossfade antar potongan supaya transisinya halus.

> Coba satu lagi dengan operator kali.

**[ACTION: Ganti input ke "empat kali dua"]**

**[ACTION: Klik Hitung + Audio]**

**[CUT: putar audio]**

> Empat kali dua sama dengan delapan, dibacakan dengan suara saya.

> Inilah inti aplikasi: Speech to Text mengubah suara saya jadi teks, sistem menghitung, lalu Text to Speech membacakan jawabannya kembali dengan suara saya.

---

## SCENE 5 — Penutup (4:15–4:45)

**[ACTION: Tampilkan summary slide atau diagram]**

> Singkatnya, aplikasi ini sudah memenuhi requirement.

> Pertama, Speech to Text bekerja: suara saya berisi operasi aritmetika berhasil ditranskripsi dan dihitung dengan benar.

> Kedua, Text to Speech bekerja dengan dataset bilangan asli nol sampai sepuluh dan operator dasar tambah, kurang, kali, bagi.

> Ketiga, pengisi suara output adalah suara saya sendiri, diambil dari dataset rekaman pribadi yang saya buat lewat web app.

> Source code dan dokumentasi lengkap ada di repo. Terima kasih sudah menonton.

---

## Catatan Saat Rekam

### Persiapan
```bash
$env:TEXETOSPEECH_WHISPER_MODEL="tiny"
$env:PYTHONPATH="src"
py -3.13 -m texetospeech.cli web --port 8765
```

Tunggu pre-warm whisper selesai sebelum rekam (lihat log `[startup] Whisper model tiny siap dipakai`).

### Tempo bicara saat demo STT
Ucapkan angka dan operator dengan **jeda 0.5 detik** antar kata:
- "satu... tambah... dua... tambah... tiga"
- "tiga... kali... dua"

Ini krusial supaya whisper memisahkan kata dengan benar.

### Backup kalau STT meleset di tengah demo
Pakai tombol Upload Audio, pilih `recordings/browser_dataset/044.wav` yang berisi "satu tambah dua sama dengan tiga".

### Estimasi durasi
| Scene | Durasi |
|---|---|
| 1. Intro | 30 detik |
| 2. Dataset | 45 detik |
| 3. Demo STT | 1 menit 45 detik |
| 4. Demo TTS suara sendiri | 1 menit 15 detik |
| 5. Penutup | 30 detik |
| **Total** | **~4–5 menit** |
