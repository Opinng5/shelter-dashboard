# Dashboard Analisis Karyawan — PT Shelter Indonesia Gemilang

Dashboard Streamlit yang membaca data langsung dari Google Sheets **DATA KARYAWAN**
dan **ikut ter-update otomatis** setiap 60 detik saat isi sheet berubah.

## Isi folder
| File | Fungsi |
|---|---|
| `app.py` | Aplikasi Streamlit (file yang dijalankan) |
| `core.py` | Membaca dan mengolah data, lalu menyusun tampilan |
| `templates/dashboard.html` | Desain dashboard (layout, warna, grafik) |
| `assets/` | Foto header, logo, dan foto gedung UPN |
| `data/DATABASE_LABOUR_KARYAWAN.xlsx` | Data cadangan bila Google Sheets tidak bisa dibaca |
| `requirements.txt` | Daftar library |

## 1. Siapkan Google Sheets
1. Buka Google Sheets **DATA KARYAWAN**.
2. Klik **Bagikan** → bagian *Akses umum* pilih **Siapa saja yang memiliki link** → peran **Viewer**.
3. Pastikan nama tab tetap **DATA_KARYAWAN** dan judul kolom tidak diubah
   (NO, NAMA LENGKAP, DOJ, SITE, STATUS, TIPE KONTRAK, END, KAB KOTA, POSISI, TANGGAL LAHIR, JENIS KELAMIN).

Link sheet sudah tertulis di `app.py` (`DEFAULT_SHEET_URL`). Untuk memakai sheet lain,
isi `SHEET_URL` di Secrets (lihat `.streamlit/secrets.toml.example`).

## 2. Jalankan di laptop
```bash
pip install -r requirements.txt
streamlit run app.py
```
Browser akan terbuka di `http://localhost:8501`.

## 3. Online-kan gratis (Streamlit Community Cloud)
1. Upload seluruh isi folder ini ke repository GitHub baru.
2. Buka https://share.streamlit.io → login dengan GitHub → **Create app**.
3. Pilih repository, branch `main`, file `app.py` → **Deploy**.
4. Dapat link seperti `https://nama-app.streamlit.app` untuk dibagikan ke dosen.

## Cara kerja update otomatis
- Ubah data di Google Sheets (tambah karyawan, ganti status, dll).
- Dalam ±1 menit dashboard mengambil data terbaru tanpa perlu di-refresh.
- Filter yang sedang dipilih (periode, klien, menu) tetap tersimpan saat data diperbarui.
- Waktu refresh bisa diubah lewat Secrets: `REFRESH_SECONDS = 30`.

## Menu
Beranda · Analisis Karyawan · Penempatan Klien (klik baris untuk memfilter dashboard) ·
Perbandingan (dua klien berdampingan) · Data Karyawan (cari dan filter status) · Rekomendasi.
