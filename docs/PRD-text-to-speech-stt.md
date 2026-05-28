# PRD: Text to Speech dan Speech to Text Aritmetika Bahasa Indonesia

## 1. Executive Summary

### Problem Statement

Pengguna membutuhkan sistem yang dapat menerima teks atau suara berisi operasi aritmetika sederhana dalam Bahasa Indonesia, menghitung hasilnya, lalu membacakan hasil tersebut. Sistem juga harus menjaga agar hasil aritmetika selalu berupa bilangan bulat.

### Proposed Solution

Bangun aplikasi **speech to text to speech** dengan alur:

```text
suara pengguna -> teks -> parsing aritmetika -> hitung bilangan bulat -> teks jawaban -> suara mirip pengguna
```

### Success Criteria

- Sistem dapat menghitung `satu tambah dua tambah tiga` menjadi `enam`.
- Sistem dapat mengenali input teks dan suara yang berisi angka serta operator dasar.
- Sistem menolak hasil pecahan, misalnya `lima bagi dua`.
- Sistem dapat membacakan hasil menggunakan text to speech.
- Sistem memiliki dataset suara pengguna untuk membuat output TTS yang lebih mirip suara pengguna.

## 2. User Experience dan Functionality

### User Persona

Pengguna utama adalah siswa atau mahasiswa yang mengerjakan tugas aplikasi AI sederhana untuk aritmetika berbasis suara dan teks.

### User Stories

- Sebagai pengguna, saya ingin mengetik operasi seperti `satu tambah dua tambah tiga`, agar sistem menghitung dan membacakan hasilnya.
- Sebagai pengguna, saya ingin mengucapkan operasi aritmetika, agar sistem mengubah suara saya menjadi teks dan menghitung hasilnya.
- Sebagai pengguna, saya ingin hasilnya selalu bilangan bulat, agar sistem tidak mengeluarkan jawaban pecahan.
- Sebagai pengguna, saya ingin suara hasil TTS mirip suara saya, agar sistem terasa seperti menggunakan suara pribadi.

### Acceptance Criteria

- Input `satu tambah dua tambah tiga` menghasilkan `enam`.
- Input `1 tambah 2 tambah 3 sama dengan 6` dikenali sebagai jawaban benar.
- Input `satu tambah dua tambah tiga sama dengan lima` dikenali sebagai jawaban salah.
- Input `lima bagi dua` ditolak karena hasilnya `2.5`.
- Input suara `dua tambah dua` menghasilkan teks `dua tambah dua` dan hasil `empat`.
- Output TTS tidak membacakan angka pecahan.

### Non-Goals MVP

- Tidak mendukung desimal, pecahan, persen, akar, pangkat, atau trigonometri.
- Tidak mendukung percakapan bebas di luar aritmetika.
- Tidak mendukung banyak pembicara sekaligus.
- Tidak menargetkan kualitas voice cloning profesional pada versi awal.

## 3. Functional Requirements

### Text to Speech Aritmetika

Sistem menerima teks:

```text
satu tambah dua tambah tiga sama dengan enam
```

atau:

```text
1 tambah 2 tambah 3 sama dengan 6
```

Sistem harus memahami:

```text
satu tambah dua tambah tiga = 1 + 2 + 3
```

Lalu menghitung:

```text
1 + 2 + 3 = 6
```

Output yang dibacakan:

```text
satu tambah dua tambah tiga sama dengan enam
```

Jika pengguna menulis hasil yang salah:

```text
satu tambah dua tambah tiga sama dengan lima
```

Respons:

```text
Jawaban salah. Satu tambah dua tambah tiga sama dengan enam.
```

### Speech to Text Angka dan Operator

Sistem menerima suara pengguna lalu mengubahnya menjadi teks.

Contoh:

```text
input suara: satu tambah dua tambah tiga
hasil STT: satu tambah dua tambah tiga
ekspresi: 1 + 2 + 3
hasil: 6
```

Fokus STT adalah mengenali:

- angka Bahasa Indonesia,
- digit,
- operator aritmetika,
- frasa `sama dengan`.

### Aturan Bilangan Bulat

Sistem hanya boleh menghasilkan bilangan bulat.

Contoh valid:

```text
enam bagi tiga = dua
```

Karena:

```text
6 / 3 = 2
```

Contoh tidak valid:

```text
lima bagi dua
```

Karena:

```text
5 / 2 = 2.5
```

Respons:

```text
Hasil operasi ini bukan bilangan bulat, jadi tidak dapat diproses.
```

## 4. Parsing dan Normalisasi

### Angka Yang Didukung MVP

Versi awal disarankan mendukung angka `0` sampai `100`.

| Kata | Nilai |
| --- | --- |
| `nol` | `0` |
| `satu` | `1` |
| `dua` | `2` |
| `tiga` | `3` |
| `empat` | `4` |
| `lima` | `5` |
| `enam` | `6` |
| `tujuh` | `7` |
| `delapan` | `8` |
| `sembilan` | `9` |
| `sepuluh` | `10` |
| `sebelas` | `11` |
| `dua belas` | `12` |
| `dua puluh satu` | `21` |
| `seratus` | `100` |

### Operator

| Kata | Operator |
| --- | --- |
| `tambah` | `+` |
| `plus` | `+` |
| `kurang` | `-` |
| `minus` | `-` |
| `kali` | `*` |
| `dikali` | `*` |
| `bagi` | `/` |
| `dibagi` | `/` |
| `sama dengan` | `=` |

### Prioritas Operator

Rekomendasi MVP mengikuti prioritas matematika standar:

1. `kali` dan `bagi`
2. `tambah` dan `kurang`

Contoh:

```text
dua tambah tiga kali empat = empat belas
```

Karena:

```text
2 + (3 * 4) = 14
```

## 5. AI System Requirements

### Speech to Text

STT bertugas mengubah suara pengguna menjadi teks. Dataset suara pribadi tidak wajib untuk STT jika menggunakan model STT umum, tetapi kualitas mikrofon dan pengucapan tetap penting.

Output STT harus dinormalisasi agar variasi ucapan tetap dipahami.

Contoh normalisasi:

```text
satu plus dua -> satu tambah dua
dua di kali tiga -> dua kali tiga
samadengan -> sama dengan
```

### Text to Speech

TTS bertugas membacakan jawaban sistem. Untuk membuat suara mirip pengguna, sistem membutuhkan dataset rekaman suara pengguna.

Catatan penting:

- Dataset suara pribadi lebih penting untuk TTS mirip pengguna.
- STT fokus pada pengenalan suara menjadi teks.
- TTS fokus pada pembuatan suara dari teks.

## 6. Dataset Suara Pengguna

### Kualitas Rekaman

Rekaman sebaiknya:

- Direkam di ruangan tenang.
- Menggunakan mikrofon yang sama.
- Tidak ada musik, kipas, kendaraan, atau suara orang lain.
- Volume suara stabil.
- Pengucapan jelas dan tidak terlalu cepat.
- Format audio disarankan `wav`, mono, 16-bit, 22050 Hz atau 44100 Hz.

### Durasi Dataset

- Minimal percobaan awal: 5 sampai 10 menit.
- Lebih baik: 30 sampai 60 menit.
- Semakin bersih dan konsisten dataset, semakin baik kemiripan suara.

### Kalimat Yang Perlu Direkam

#### Angka Dasar

```text
nol
satu
dua
tiga
empat
lima
enam
tujuh
delapan
sembilan
sepuluh
sebelas
dua belas
tiga belas
empat belas
lima belas
enam belas
tujuh belas
delapan belas
sembilan belas
dua puluh
```

#### Puluhan dan Ratusan

```text
dua puluh satu
tiga puluh dua
empat puluh tiga
lima puluh empat
enam puluh lima
tujuh puluh enam
delapan puluh tujuh
sembilan puluh delapan
seratus
seratus satu
seratus dua puluh tiga
```

#### Operator Aritmetika

```text
tambah
kurang
kali
bagi
sama dengan
hasilnya
jawabannya
benar
salah
tidak dapat diproses
hasil operasi ini bukan bilangan bulat
```

#### Kalimat Latihan Aritmetika

```text
satu tambah dua sama dengan tiga
dua tambah tiga sama dengan lima
tiga tambah empat sama dengan tujuh
empat tambah lima sama dengan sembilan
sepuluh kurang tiga sama dengan tujuh
dua puluh kurang lima sama dengan lima belas
tiga kali dua sama dengan enam
empat kali lima sama dengan dua puluh
dua puluh bagi lima sama dengan empat
sembilan bagi tiga sama dengan tiga
lima bagi dua tidak dapat diproses karena hasilnya bukan bilangan bulat
satu tambah dua tambah tiga sama dengan enam
```

#### Kalimat Umum Agar Suara Natural

```text
Halo, nama saya sedang digunakan untuk sistem suara.
Saya sedang membaca kalimat dengan jelas.
Hari ini saya belajar membuat aplikasi speech to text dan text to speech.
Sistem akan mendengarkan suara saya lalu mengubahnya menjadi teks.
Setelah itu sistem menghitung operasi aritmetika dan membacakan hasilnya.
Saya mengucapkan setiap kata dengan tempo yang stabil.
Suara saya direkam di ruangan yang tenang.
```

## 7. Technical Specifications

### Architecture Overview

```text
Input Teks
-> Normalisasi teks
-> Parser angka dan operator
-> Kalkulator bilangan bulat
-> Generator kalimat jawaban
-> TTS
-> Output audio
```

```text
Input Suara
-> STT
-> Normalisasi teks
-> Parser angka dan operator
-> Kalkulator bilangan bulat
-> Generator kalimat jawaban
-> TTS suara pengguna
-> Output audio
```

### Modul Yang Disarankan

- `number_parser`: mengubah kata angka Indonesia menjadi integer.
- `number_formatter`: mengubah integer menjadi kata angka Indonesia.
- `calculator`: menghitung ekspresi dan menolak hasil pecahan.
- `speech_to_text`: mengubah audio menjadi teks.
- `text_to_speech`: mengubah teks jawaban menjadi audio.
- `voice_dataset`: menyimpan metadata dan file rekaman suara pengguna.

## 8. Error Handling

Sistem harus memberi pesan jika:

- Input kosong.
- Angka tidak dikenali.
- Operator tidak dikenali.
- Ekspresi tidak lengkap.
- Ada pembagian dengan nol.
- Hasil pembagian bukan bilangan bulat.
- Hasil akhir bukan bilangan bulat.
- Suara terlalu pelan atau tidak terbaca.

Contoh respons:

```text
Maaf, saya belum bisa mengenali operasi tersebut.
```

```text
Pembagian dengan nol tidak dapat diproses.
```

```text
Hasil operasi ini bukan bilangan bulat, jadi tidak dapat diproses.
```

## 9. Evaluation Strategy

### Test Case

| No | Input | Output Yang Diharapkan |
| --- | --- | --- |
| 1 | `satu tambah dua` | `tiga` |
| 2 | `satu tambah dua tambah tiga` | `enam` |
| 3 | `sepuluh kurang empat` | `enam` |
| 4 | `tiga kali empat` | `dua belas` |
| 5 | `dua puluh bagi lima` | `empat` |
| 6 | `lima bagi dua` | `Hasil operasi ini bukan bilangan bulat` |
| 7 | `satu tambah dua sama dengan tiga` | `Jawaban benar` |
| 8 | `satu tambah dua sama dengan empat` | `Jawaban salah. Hasil yang benar adalah tiga` |
| 9 | suara: `dua tambah dua` | teks: `dua tambah dua`, hasil: `empat` |
| 10 | suara terlalu pelan | `Maaf, suara belum terbaca dengan jelas` |

### Target Kualitas MVP

- Akurasi parser teks untuk test case utama: 100%.
- STT berhasil mengenali minimal 8 dari 10 contoh suara bersih.
- Tidak ada output berupa desimal atau pecahan.
- Semua error utama memiliki pesan yang jelas.

## 10. Risks dan Roadmap

### Risiko Teknis

- STT dapat salah mengenali angka yang mirip bunyinya.
- Voice cloning membutuhkan dataset bersih dan cukup panjang.
- Pembagian dapat menghasilkan pecahan jika tidak divalidasi.
- Pengucapan pengguna yang terlalu cepat dapat menurunkan akurasi STT.

### Roadmap

#### MVP

- Parser angka 0 sampai 100.
- Operator tambah, kurang, kali, bagi.
- Validasi bilangan bulat.
- TTS standar.
- STT untuk suara bersih.

#### Versi 1.1

- Dataset suara pengguna.
- TTS dengan suara mirip pengguna.
- UI sederhana untuk rekam suara dan menjalankan operasi.

#### Versi 2.0

- Angka lebih besar dari 100.
- Riwayat operasi.
- Evaluasi akurasi STT otomatis.
- Peningkatan kualitas suara sintetis.
