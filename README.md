# Project Settlement — Ekstraksi Keypoint Absensi

Website untuk mengekstrak keypoint dari dokumen absensi karyawan dalam bentuk PDF (Timesheet, Surat Perintah Lembur, Berita Acara, dan Laporan Kehadiran/DigiHC). PDF dikonversi ke Markdown menggunakan [Docling](https://github.com/docling-project/docling), lalu setiap halaman diklasifikasikan dan diparsing dengan regex.

> **Catatan:** Seluruh data pada `Absensi PT Nusatama Teknologi.pdf` adalah **data fiktif (dummy)**. Nama orang, perusahaan, NPP, dan project tidak merujuk pada pihak sebenarnya.

## Fitur

- Deteksi otomatis tipe dokumen per halaman: **Timesheet**, **Form Lembur**, **Berita Acara**, **DigiHC**
- Ekstraksi keypoint: nama, periode, vendor, dan metrik sesuai tipe
  - Timesheet → total kehadiran
  - Form Lembur → jumlah hari lembur
  - Berita Acara → jumlah ketidakhadiran
  - DigiHC → jumlah H (Hadir), T (Terlambat), TK (Tanpa Keterangan)
- Penanganan tabel yang terpotong ke halaman berikutnya
- Rekap per pegawai, termasuk peringatan jika periode antar dokumen tidak konsisten
- REST API (FastAPI) + tampilan website sederhana (drag & drop PDF)

## Struktur Project

```
├── main.py            # Endpoint FastAPI (POST /keypoints)
├── pipeline.py        # Alur OCR → parsing → agregasi per pegawai
├── extract_pdf.py     # Konversi PDF ke Markdown (Docling)
├── parse_absensi.py   # Deteksi tipe dokumen & ekstraksi keypoint
├── schemas.py         # Model respons Pydantic
├── config.py          # Konfigurasi (content-type yang diizinkan)
├── legacy_main.py     # Versi CLI (tanpa API)
├── Task.md            # Catatan requirement
├── index.html         # Frontend
├── style.css
├── script.js
└── Absensi PT Nusatama Teknologi.pdf   # Contoh dokumen (dummy)
```

## Instalasi

Membutuhkan **Python 3.10+**.

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

> Docling akan mengunduh model OCR saat pertama kali dijalankan, jadi proses pertama bisa memakan waktu lebih lama.

## Cara Menjalankan

### 1. Via API + Web

```bash
uvicorn main:app --reload
```

Buka `index.html` di browser, upload PDF, lalu klik **Process Document**. Endpoint default: `http://127.0.0.1:8000/keypoints`. Dokumentasi API tersedia di `http://127.0.0.1:8000/docs`.

### 2. Via CLI

```bash
python legacy_main.py
```

Hasil ekstraksi dicetak ke terminal, dan teks lengkap disimpan ke `full_text.md`.

## Contoh Output

| Hal. | Tipe | Nama | Periode | Keypoint |
|---|---|---|---|---|
| 1 | Timesheet | Alvin Kurniawan | Mei 2026 | 13 hari hadir |
| 3 | Form Lembur | Alvin Kurniawan | Mei 2026 | 6 hari lembur |
| 7 | DigiHC | KEISHA PRANATA | Mei 2026 | 14 H / 2 T / 0 TK |
| 19 | Berita Acara | Rendy Kurniawan | Mei 2026 | 6 hari absen |

## Tech Stack

- Python, FastAPI, Pydantic
- Docling (PDF → Markdown/OCR)
- HTML, CSS, JavaScript (vanilla)
