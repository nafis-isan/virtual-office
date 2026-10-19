# Visual Office AI

Dashboard kantor virtual multi-agent lokal: Nuxt 4 + Vue 3 untuk UI kantor 2D bergaya pixel-art, FastAPI untuk API/orchestrator, MySQL untuk penyimpanan dan indeks RAG, serta Gemini untuk generasi dan embedding.

## Prasyarat

- Node.js 20 atau lebih baru
- Python 3.10 atau lebih baru
- MySQL 8 yang berjalan lokal
- Gemini API key dan nama model yang tersedia, jika ingin menjalankan alur AI

## Versi yang diverifikasi

| Bagian | Versi |
| --- | --- |
| Python | 3.10.6 |
| FastAPI / Uvicorn | 0.115.6 / 0.24.0 |
| SQLAlchemy / PyMySQL / Alembic | 2.0.23 / 1.2.3 / 1.20.0 |
| Pydantic Settings / python-dotenv | 2.1.0 / 1.0.0 |
| Google GenAI SDK / httpx / pytest | 1.2.0 / 0.28.1 / 8.4.2 |
| python-multipart / pypdf / python-docx | 0.0.20 / 5.1.0 / 1.1.2 |
| Node.js / npm | 24.20.0 / 11.19.0 |
| Nuxt / Vue | 4.6.2 / 3.5.44 |
| TypeScript / Vue TypeScript Checker | 5.9.3 / 3.3.13 |

Backend Python dipatok pada versi yang diuji di `backend/requirements.txt`; versi frontend dikunci di `frontend/package-lock.json`.

## Menyiapkan MySQL

Buat database dan akun aplikasi terbatas dari MySQL:

```sql
CREATE DATABASE visual_office_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'visual_office'@'127.0.0.1' IDENTIFIED BY 'ganti-password-lokal';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
  ON visual_office_ai.* TO 'visual_office'@'127.0.0.1';
```

Jangan gunakan akun `root` untuk aplikasi. Sesuaikan host akun MySQL bila server mendengarkan pada `127.0.0.1`.

## Menjalankan backend

Di PowerShell, dari direktori `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Isi `DATABASE_URL` pada `backend/.env`. Isi `GEMINI_API_KEY` dan `GEMINI_MODEL` dengan kredensial/model yang sudah diverifikasi di Google AI Studio. API key hanya dibaca oleh backend dan tidak pernah dikirim ke browser.
RAG memakai `GEMINI_EMBEDDING_MODEL=gemini-embedding-001` secara default; model embedding juga memerlukan akses Gemini API.

Jalankan migrasi dan server:

```powershell
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Periksa `http://localhost:8000/api/health` dan `http://localhost:8000/docs`. Health check tetap tersedia saat MySQL belum tersambung; status akan `degraded`, dan endpoint yang membutuhkan database mengembalikan `503`.

## Menjalankan frontend

Di terminal lain, dari direktori `frontend`:

```powershell
npm install
npm run dev
```

Buka alamat yang ditampilkan Nuxt (umumnya `http://localhost:3000`). API lokal dapat diganti melalui konfigurasi Nuxt `runtimeConfig.public.apiBase`.

Jika port `8000` sudah digunakan backend lain, jalankan backend aplikasi ini di `8001`:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Atur `NUXT_PUBLIC_API_BASE=http://127.0.0.1:8001` di `frontend/.env` agar Nuxt mengarah ke port tersebut. File `.env` lokal diabaikan Git.

## Yang tersedia pada MVP ini

- Scene kantor 3D stylized dengan empat karakter agent humanoid.
- Tata kantor stylized dengan meja pribadi dan meja kolaborasi di tengah; agent berstatus aktif berjalan ke area kolaborasi dan kembali ke mejanya ketika tugas selesai.
- Panel status agent, daftar riwayat task, aktivitas, langkah, dan hasil.
- Chat membuat task melalui REST API; dashboard melakukan polling status dari backend.
- Project Manager menyusun rencana JSON tervalidasi, lalu specialist bekerja berurutan dan Project Manager merangkum hasil.
- Pustaka RAG menerima dokumen PDF, TXT, MD, dan DOCX sampai 5 MB; teks dipecah menjadi potongan dan embedding Gemini disimpan di MySQL. Saat task dibuat, lima potongan terdekat (jika relevan) dipakai sebagai konteks dan sumber dicantumkan di ringkasan.
- Dokumen diunggah melalui UI dan dapat dihapus dari pustaka; jalankan `alembic upgrade head` untuk membuat tabel knowledge.
- Isi teks dikirim ke Gemini API untuk embedding dan sebagai konteks jawaban; file asli tidak disimpan. Jangan unggah data sensitif yang tidak boleh diproses oleh layanan Gemini.
- Task, langkah, aktivitas, pesan, artefak teks, agent, dan approval disimpan melalui model SQLAlchemy dan migrasi Alembic MySQL.
- Gemini hanya dipanggil backend. Status API key tidak membuka nilainya ke frontend.
- Penanganan error Gemini/database ditampilkan sebagai pesan aman; task gagal tidak ditandai selesai.

## Batas keamanan MVP

Programmer hanya menghasilkan draft dan artefak teks. MVP ini **tidak** menulis, menimpa, atau menghapus file, menjalankan shell, menginstal paket, melakukan pencarian web, maupun membatalkan task. Approval dicatat sebagai konsep API, tetapi tidak memberi izin untuk menjalankan tindakan sistem. Jangan mengaktifkan tindakan tersebut tanpa sandbox, validasi workspace, dan kebijakan approval yang ditinjau.

Agent memerlukan MySQL dan konfigurasi `GEMINI_API_KEY` serta `GEMINI_MODEL` agar tugas dapat diproses. Unggah dan retrieval dokumen juga memerlukan akses ke model `GEMINI_EMBEDDING_MODEL`. Nama model dan ketersediaan kuota bergantung pada konfigurasi akun; aplikasi tidak mengasumsikan nama model atau kuota gratis tanpa batas.

## Pemeriksaan

Backend: `cd backend; python -m pytest`. Frontend checks: `cd frontend; npm run typecheck; npm run build`.
