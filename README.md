# Visual Office AI

Workspace multi-agent lokal dengan antarmuka IDE gelap: Nuxt 4 + Vue 3 untuk sidebar dan tab task, scene kantor 2D pixel-art, FastAPI untuk API/orchestrator, MySQL untuk penyimpanan dan indeks RAG, serta OpenRouter atau Gemini untuk generasi agent.

## Prasyarat

- Node.js 20 atau lebih baru
- Python 3.10 atau lebih baru
- MySQL 8 yang berjalan lokal
- API key dan model Gemini atau OpenRouter, jika ingin menjalankan alur agent
- Akses Gemini ke model embedding, jika ingin menggunakan RAG

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

Isi `DATABASE_URL` serta konfigurasi provider di `backend/.env`. Gunakan `AI_PROVIDER=openrouter`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL=nvidia/nemotron-3.5-super-vl:free`, dan `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1` untuk generasi teks melalui OpenRouter; semua agent memakai model yang sama dengan reasoning aktif (`OPENROUTER_REASONING_ENABLED=true`). Model gratis ini mendukung `response_format`, sesuai katalog OpenRouter yang diperiksa pada 23 Oktober 2026; ketersediaan dan batas penggunaan mengikuti akun OpenRouter. Backend meminta JSON terstruktur untuk rencana dan tetap memvalidasi hasilnya. Backend menolak slug MiniMax yang tersisa di environment proses dan menjelaskan bahwa environment proses mengalahkan nilai `.env`; atur environment proses ke NVIDIA Nemotron lalu restart backend. Atau gunakan `AI_PROVIDER=gemini`, `GEMINI_API_KEY`, dan `GEMINI_MODEL` untuk Gemini. API key hanya dibaca oleh backend dan tidak pernah dikirim ke browser.
Pada mode OpenRouter, dokumen RAG memakai pencocokan kata kunci lokal. Jika OpenRouter mengembalikan respons kosong, backend mencoba sekali lagi tanpa reasoning sebelum menandai langkah sebagai gagal. Jika OpenRouter menolak permintaan dengan HTTP 400, backend menampilkan pesan aman tanpa meneruskan detail mentah provider. Pada mode Gemini, `GEMINI_API_KEY` dan `GEMINI_EMBEDDING_MODEL=gemini-embedding-001` dipakai untuk embedding semantik.

Jalankan migrasi dan server:

```powershell
alembic upgrade head
$env:OPENROUTER_MODEL = "nvidia/nemotron-3.5-super-vl:free"
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
$env:OPENROUTER_MODEL = "nvidia/nemotron-3.5-super-vl:free"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Atur `NUXT_PUBLIC_API_BASE=http://127.0.0.1:8001` di `frontend/.env` agar Nuxt mengarah ke port tersebut. File `.env` lokal diabaikan Git.

## Yang tersedia pada MVP ini

- Scene kantor 2D pixel-art dengan empat karakter agent interaktif yang mengikuti baris sprite referensi (Project Manager, Desainer, Programmer, Researcher), karpet di bawah workstation dan meja kolaborasi, workstation dan kursi tetap, serta rak arsip RAG. Saat idle, agent dapat berjalan di atas karpet melalui jalur yang tidak melewati meja; hanya sepasang agent yang berbincang pada satu waktu, sementara lainnya tetap berjalan. Saat tugas baru diproses, mereka berkumpul di meja tengah sebelum langkah kerja dimulai.
- Kerangka IDE dengan activity bar Office/Agents/Tasks/Knowledge, sidebar yang dapat dicari, tab editor untuk kantor dan beberapa task, serta status bar provider/backend.
- Dokumen task dengan tab Overview, Agent Steps, Output, dan Sources; klik agent untuk membuka aktivitas dan langkahnya.
- Panel bawah Problems, Output, dan Terminal baca-saja. Shortcut: `Ctrl+N` task baru, `Ctrl+B` sidebar, `Ctrl+J` panel bawah, `Ctrl+K` pencarian.
- Denah menyorot agent serta langkah dari task terpilih dan menampilkan pembaruan aktivitas sesuai status backend; saat Project Manager menyusun rencana, seluruh tim berkumpul di meja tengah, lalu agent berpindah ke meja kerja masing-masing sesuai langkah aktif.
- Panel status agent, daftar riwayat task, aktivitas, langkah, dan hasil.
- Chat membuat task melalui REST API; dashboard melakukan polling status dari backend.
- Project Manager menyusun rencana JSON tervalidasi, lalu specialist bekerja berurutan dan Project Manager merangkum hasil.
- Agent dapat menghasilkan file kode atau Markdown dengan blok kode beratribut `path=...`; tab Output menyediakan pratinjau, unduh per file atau seluruh proyek sebagai ZIP (path folder dipertahankan), dan perbandingan dengan file yang ada. Untuk permintaan membuat aplikasi, rencana selalu menyertakan Desainer dan Programmer secara berurutan: Desainer memberi arahan implementasi UI dalam teks (warna HEX, selector/class CSS, lokasi file view/stylesheet, dan perilaku komponen), bukan mockup atau kode; Programmer menerapkan arahan itu dalam file proyek yang dapat diunduh. Simpan hanya setelah konfirmasi dan hanya ke dalam `WORKSPACE_ROOT`.
- Task gagal dapat dicoba ulang sebagai task baru; task aktif dapat dibatalkan secara kooperatif; task selesai, gagal, atau dibatalkan dapat diarsipkan dan dipulihkan.
- Pustaka RAG menerima dokumen PDF, TXT, MD, dan DOCX sampai 5 MB. Dengan `AI_PROVIDER=openrouter`, retrieval memakai pencocokan kata kunci lokal tanpa memanggil Gemini. Dengan `AI_PROVIDER=gemini`, embedding Gemini disimpan di MySQL dan lima potongan relevan dipakai sebagai konteks; mode embedding memerlukan `GEMINI_API_KEY`.
- Dokumen diunggah melalui UI dan dapat dihapus dari pustaka; jalankan `alembic upgrade head` untuk membuat tabel knowledge.
- Prompt generasi agent dan konteks jawaban dikirim ke provider pada `AI_PROVIDER`. Mode OpenRouter memproses dokumen RAG lokal; mode Gemini mengirim teks dokumen ke Gemini API untuk embedding. File asli tidak disimpan. Jangan unggah data sensitif yang tidak boleh diproses oleh layanan pihak ketiga tersebut.
- Task, langkah, aktivitas, pesan, artefak teks, agent, dan approval disimpan melalui model SQLAlchemy dan migrasi Alembic MySQL.
- Provider AI hanya dipanggil backend. Status konfigurasi tidak membuka nilai API key ke frontend.
- Penanganan error provider AI/database ditampilkan sebagai pesan aman; task gagal tidak ditandai selesai.

## Batas keamanan

Agent hanya menghasilkan draft dan artefak; agent tidak punya akses filesystem atau shell. File baru ditulis hanya setelah pengguna memilih lokasi relatif dan mengonfirmasi. Backend membatasi baca/tulis file ke `WORKSPACE_ROOT`, menolak path traversal, symbolic link keluar workspace, file kredensial umum, dan penimpaan tanpa konfirmasi kedua. Membatalkan task bersifat kooperatif: panggilan Gemini yang sedang berlangsung tidak dapat dihentikan, tetapi hasilnya tidak akan diterapkan setelah pembatalan terdeteksi.

Aplikasi ini tidak menjalankan shell, menginstal paket, menghapus file, atau melakukan pencarian web. Approval dicatat sebagai konsep API dan tidak memberi izin menjalankan tindakan sistem. Tinjau perubahan file sebelum menyimpannya; jangan mengarahkan `WORKSPACE_ROOT` ke folder yang berisi data sensitif.

Agent memerlukan MySQL dan konfigurasi API key serta model untuk provider yang dipilih. Mode OpenRouter tidak memerlukan Gemini; mode Gemini dan retrieval semantik dokumennya memerlukan `GEMINI_API_KEY` serta model `GEMINI_EMBEDDING_MODEL`. Nama model dan ketersediaan kuota bergantung pada konfigurasi akun; aplikasi tidak mengasumsikan kuota gratis tanpa batas.

## Pemeriksaan

Backend: `cd backend; python -m pytest`. Frontend checks: `cd frontend; npm run typecheck; npm run build`.
