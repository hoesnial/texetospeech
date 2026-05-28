# Skrip Presentasi Video TexeToSpeech

Durasi target: **8–12 menit**. Format: layar terekam dengan voice over.

## Struktur Demo

```text
1. Pembuka & masalah         (1 menit)
2. Arsitektur singkat        (1 menit)
3. Demo Text to Speech       (2 menit)
4. Demo Personal Voice       (2 menit)
5. Demo Speech to Text       (2 menit)
6. Demo Edge Case            (1 menit)
7. Penutup & Roadmap         (1 menit)
```

---

## 1. Pembuka & Masalah (1 menit)

### Slide / Layar
Tampilkan judul `TexeToSpeech` dan satu kalimat tagline.

### Yang perlu dijelaskan
- Nama proyek dan tujuannya: sistem aritmetika berbasis suara dan teks Bahasa Indonesia.
- Masalah yang diselesaikan:
  - Pengguna mengetik atau mengucapkan operasi aritmetika seperti `satu tambah dua tambah tiga`.
  - Sistem harus paham angka kata Indonesia, menghitung dengan benar, dan menjaga hasilnya tetap bilangan bulat.
  - Sistem harus bisa membacakan jawaban, idealnya dengan suara yang bisa dipersonalisasi.
- Sebutkan acuan PRD: `docs/PRD-text-to-speech-stt.md`.

### Skrip narasi
> "Halo, saya akan mendemokan TexeToSpeech, sistem aritmetika Bahasa Indonesia yang menggabungkan Text to Speech, Speech to Text, dan personal voice. Tujuan utamanya adalah membaca operasi aritmetika dari teks atau suara, menghitung dengan akurat, dan membacakan hasilnya. Sistem ini juga bisa memakai suara saya sendiri untuk output TTS."

---

## 2. Arsitektur Singkat (1 menit)

### Layar
Tampilkan diagram dari PRD atau ketik cepat di terminal:

```text
input teks  ─┐
             ├─► normalizer ─► parser angka ─► calculator ─► answer text ─► TTS
input suara ─┘                                                              │
       ▲                                                                    │
       └────── STT (faster-whisper / Web Speech API / personal-stt) ◄───────┘
```

### Yang perlu dijelaskan
- Pipeline utama:
  - Normalizer mengubah teks input dan transkrip STT jadi token konsisten.
  - Parser memecah ekspresi `1 + 2 + 3` dari kata Indonesia.
  - Calculator menolak hasil pecahan dan pembagian dengan nol.
  - Generator jawaban menyusun kalimat: `"satu tambah dua sama dengan tiga."`.
- Backend modular yang bisa dipilih:
  - **TTS**: SAPI Windows (default), espeak-ng / pyttsx3 / piper / Coqui (opsional), `personal-voice` (concatenative dari rekaman user).
  - **STT**: `faster-whisper` (default offline), Web Speech API (browser), `personal-stt` (template matching offline tanpa ML).

### Skrip narasi
> "Pipeline-nya simpel: input teks atau suara dinormalisasi, lalu parser angka mengubahnya menjadi ekspresi aritmetika. Kalkulator memvalidasi hasilnya tetap bilangan bulat. Untuk output, sistem memilih backend yang tersedia. Saya pakai pendekatan modular: kalau backend canggih tidak terinstall, sistem otomatis pakai yang lebih ringan."

---

## 3. Demo Text to Speech (2 menit)

### Persiapan
Buka dua jendela:
- Terminal di folder proyek.
- Browser di `http://127.0.0.1:8765`.

### Langkah 1 — Cek kesiapan
```bash
$env:PYTHONPATH="src"
py -3.13 -m texetospeech.cli doctor
```

Tunjukkan baris:
- `[OK] faster_whisper: tersedia`
- `[OK] personal voice: N frasa dari recordings\browser_dataset`
- `[OK] personal STT: siap`

### Langkah 2 — Hitung teks dasar
```bash
py -3.13 -m texetospeech.cli text "satu tambah dua tambah tiga"
```

Output: `satu tambah dua tambah tiga sama dengan enam.`

### Langkah 3 — Validasi hasil pecahan
```bash
py -3.13 -m texetospeech.cli text "lima bagi dua"
```

Output: `Hasil operasi ini bukan bilangan bulat, jadi tidak dapat diproses.`

### Langkah 4 — Cek jawaban benar/salah
```bash
py -3.13 -m texetospeech.cli text "satu tambah dua sama dengan tiga"
py -3.13 -m texetospeech.cli text "satu tambah dua sama dengan empat"
```

Tunjukkan output `Jawaban benar` dan `Jawaban salah. Hasil yang benar adalah tiga.`

### Langkah 5 — Demo via web app
Di browser, di bagian **Text to Speech Aritmetika**:
1. Ketik `dua tambah tiga kali empat`.
2. Klik **Hitung**.
3. Tunjukkan hasil di output box: `2 + 3 * 4 = 14` dan jawaban `dua tambah tiga kali empat sama dengan empat belas.`
4. Klik **Hitung + Audio**. Audio diputar pakai SAPI Windows.

### Yang perlu ditekankan
- Operator precedence sudah sesuai matematika (`kali` dulu sebelum `tambah`).
- Sistem konsisten antara CLI dan web app.
- Validasi pecahan dan pembagian dengan nol berjalan otomatis.

### Skrip narasi
> "Pertama saya cek kesiapan sistem dengan perintah doctor. Semua komponen siap. Lalu saya tunjukkan core-nya: input `satu tambah dua tambah tiga` menghasilkan `enam`. Sistem juga menolak hasil pecahan seperti `lima bagi dua`. Yang menarik, ekspresi seperti `dua tambah tiga kali empat` mengikuti urutan operasi standar, jadi hasilnya empat belas, bukan dua puluh."

---

## 4. Demo Personal Voice (2 menit)

### Persiapan
Pastikan dataset di `recordings/browser_dataset/` sudah terisi.

### Langkah 1 — Tampilkan dataset
```bash
Get-ChildItem recordings\browser_dataset | Measure-Object | Select-Object Count
```

Tunjukkan jumlah file WAV dan `metadata.csv`.

### Langkah 2 — Demo voice profile via CLI
```bash
py -3.13 -m texetospeech.cli text "satu tambah dua tambah tiga sama dengan enam" --speak --out audio\demo_my_voice.wav --my-voice
```

Tunjukkan log:
- `[info] Personal voice memakai N potongan rekaman`
- `Backend TTS: personal-voice`

Putar `audio\demo_my_voice.wav` — itu suara user.

### Langkah 3 — Demo via web app
Di browser:
1. Centang **pakai suara saya (personal voice / dataset)**.
2. Ketik `tiga kali dua sama dengan enam`.
3. Klik **Hitung + Audio**.
4. Audio diputar pakai potongan suara user.

### Langkah 4 — Bandingkan dengan TTS standar
1. Hilangkan centang.
2. Klik **Hitung + Audio** lagi.
3. Audio sekarang pakai SAPI Windows (suara English default).

### Yang perlu ditekankan
- Personal voice **tidak butuh ML / GPU / training**. Cukup file rekaman + `metadata.csv`.
- Greedy longest-match: kalau frasa lengkap sudah direkam, dipakai utuh. Kalau tidak, dipecah per kata dengan crossfade dan RMS normalization.
- Output 100% suara user untuk vocabulary yang sudah direkam.

### Skrip narasi
> "Sekarang yang menarik: personal voice. Sistem saya pakai pendekatan concatenative, artinya saat saya minta TTS dengan flag `--my-voice`, sistem mengambil potongan-potongan rekaman saya dan menggabungkannya. Tidak butuh model neural, tidak butuh GPU. Saya hanya butuh dataset rekaman saya sendiri. Bandingkan suara ini dengan TTS standar SAPI: yang ini benar-benar suara saya."

---

## 5. Demo Speech to Text (2 menit)

### Langkah 1 — Backend STT
Tunjukkan baris doctor `[OK] faster_whisper: tersedia` dan jelaskan default model `tiny` (75 MB) dipilih untuk kecepatan di mesin low-end.

### Langkah 2 — Demo via web app
Di browser, di bagian **Speech to Text + Aritmetika**:
1. Klik **Mulai Rekam**.
2. Ucapkan `dua tambah tiga sama dengan lima`.
3. Klik **Stop Rekam**.
4. Tunggu 5–15 detik untuk transkripsi.
5. Tunjukkan output:
   - Transkrip yang dikenali
   - Ekspresi: `2 + 3 = 5`
   - Hasil: `5 (lima)`
   - Jawaban: "Jawaban benar..."
   - STT backend: `faster-whisper` atau `web-speech-api`.

### Langkah 3 — Demo upload file
1. Klik **Upload Audio**.
2. Pilih file rekaman (mis. `recordings\browser_dataset\062.wav`).
3. Tunjukkan transkripsi dan evaluasi.

### Langkah 4 — Tampilkan koreksi STT pintar
Tunjukkan di kode `src/texetospeech/normalizer.py` bagian `PHRASE_FIXES`:
- `"sepuluh empat"` → `"empat belas"` (mengoreksi kesalahan whisper umum)
- `"plas"` → `"tambah"`, `"inam"` → `"enam"`, dll.

Lewat CLI:
```bash
py -3.13 -m texetospeech.cli text "sepuluh empat tambah dua"
```

Output: `empat belas tambah dua sama dengan enam belas.`

### Yang perlu ditekankan
- Tiga lapis backend STT yang otomatis fallback:
  1. faster-whisper (default, akurat, gratis, offline)
  2. Web Speech API browser (gratis, butuh Chrome/Edge)
  3. Personal STT (template matching dari dataset user, offline, vocabulary terbatas)
- Pre-parser **memperbaiki kesalahan transkripsi STT umum** otomatis.

### Skrip narasi
> "Untuk Speech to Text, saya pakai faster-whisper, port Whisper yang offline dan gratis. Default model `tiny` cukup cepat di laptop saya. Saya ucapkan operasi aritmetika, sistem mentranskripsi, lalu langsung menghitung. Yang penting, saya juga bikin pre-parser yang memperbaiki kesalahan whisper umum, misalnya `sepuluh empat` otomatis dikoreksi jadi `empat belas`. Jadi walau STT-nya kadang meleset, hasil akhirnya tetap benar."

---

## 6. Demo Edge Case (1 menit)

### Validasi input
```bash
py -3.13 -m texetospeech.cli text "lima bagi nol"
```
Output: `Pembagian dengan nol tidak dapat diproses.`

```bash
py -3.13 -m texetospeech.cli text ""
```
Output: error `Input kosong.`

### Operator precedence
```bash
py -3.13 -m texetospeech.cli text "dua tambah tiga kali empat"
```
Output: `dua tambah tiga kali empat sama dengan empat belas.`

### Format digit ↔ kata
```bash
py -3.13 -m texetospeech.cli text "1 + 2 = 3"
```
Output: `Jawaban benar. satu tambah dua sama dengan tiga.`

### Yang perlu ditekankan
- Sistem konsisten menerima digit, simbol matematika, atau kata Indonesia.
- Semua error punya pesan jelas.
- Test suite 23 unit test menjaga regression.

### Skrip narasi
> "Sistem juga menangani edge case: pembagian dengan nol, input kosong, mix digit dengan kata. Saya punya 23 unit test yang otomatis dijalankan untuk memastikan tidak ada regression."

---

## 7. Penutup & Roadmap (1 menit)

### Yang perlu disebutkan
- **Pencapaian MVP**:
  - Parser angka 0 sampai juta.
  - Operator `+ - * /` dengan precedence benar.
  - Validasi bilangan bulat.
  - TTS Windows native (SAPI) tanpa install dependency.
  - STT akurat (faster-whisper) offline.
  - Personal voice 100% suara user tanpa ML.
  - Personal STT offline tanpa pip install apa pun.
  - Web app standalone tanpa framework eksternal.
- **Roadmap selanjutnya**:
  - Fine-tune Piper TTS agar suara user juga bisa untuk teks bebas (panduan di `docs/TRAINING_VOICE.md`).
  - Tambah dukungan angka lebih besar (juta, miliar).
  - History operasi & logging session.
  - Mode soal latihan untuk siswa (random generator).

### Skrip narasi penutup
> "Singkatnya, MVP TexeToSpeech mencakup parser, kalkulator, TTS, STT, dan personal voice — semuanya bisa jalan offline dengan minimum dependency. Roadmap selanjutnya: fine-tune model Piper agar suara user bisa membaca teks apa pun, plus mode soal latihan otomatis. Terima kasih sudah menonton."

---

## Tips Eksekusi Video

### Persiapan sebelum rekam
```bash
$env:PYTHONPATH="src"
py -3.13 -m texetospeech.cli doctor          # pastikan semua OK
py -3.13 -m texetospeech.cli web --port 8765 # boot web app, biarkan jalan
```

Pastikan:
- Mikrofon aktif dan tidak ada noise.
- Browser sudah di `http://127.0.0.1:8765`.
- Folder `recordings/browser_dataset` sudah berisi minimal 30 prompt.
- Folder `audio/` sudah dibersihkan dari output sesi sebelumnya.

### Tools rekam layar
- **OBS Studio** (gratis, multiplatform) — disarankan.
- **PowerPoint** punya fitur rekam layar di tab Insert > Screen Recording.
- **Windows Game Bar** (Win + G) untuk rekam jendela aplikasi cepat.

### Mic & audio
- Pakai headset atau mic eksternal kalau ada.
- Volume bicara stabil; ucapkan angka dan operator dengan jelas.
- Untuk demo STT, jeda 0.3 detik antar kata supaya whisper memisahkan dengan benar.

### Visual cue
- Saat menjalankan command, perbesar font terminal supaya terbaca di video.
- Saat klik tombol di web app, hover dulu beberapa detik supaya viewer melihat tombol mana yang ditekan.
- Saat memutar audio output, buka equalizer atau spektrum supaya viewer lihat ada audio yang muncul.

### Editing
- Pangkas waktu menunggu transkripsi STT (potong jeda 5–15 detik) supaya pacing tetap cepat.
- Tambahkan teks overlay saat mengganti subtopic ("Demo 3: Personal Voice").
- Akhir video tampilkan diagram arsitektur lagi sebagai recap visual.

### Backup plan kalau gagal di tengah demo
- Siapkan file audio pre-recorded untuk Speech to Text demo (`recordings/browser_dataset/044.wav` berisi `satu tambah dua sama dengan tiga`).
- Kalau STT meleset, tunjukkan PHRASE_FIXES di kode sebagai bukti bahwa sistem antisipatif.
- Kalau personal voice tidak terdengar mulus, jelaskan trade-off concatenative vs neural sebagai topik diskusi.
