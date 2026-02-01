# 🩺 Telemed Copilot — Clinical Note Structurer + Drug Label Reference (RAG)

**Telemed Copilot** adalah aplikasi demo telehealth yang membantu:
1) Mengubah **transkrip percakapan dokter–pasien** menjadi **catatan medis terstruktur (JSON / SOAP-lite)** secara otomatis, dan  
2) (Opsional) Menampilkan **referensi label obat** berbasis **RAG (Retrieval‑Augmented Generation)** dari **openFDA/DailyMed** agar output lebih *grounded* (tidak ngarang).

> ⚠️ **Disclaimer (Penting)**  
> Proyek ini **bukan alat diagnosis**, **bukan pengganti dokter**, dan **tidak memberikan saran terapi**. Output hanya untuk **bantuan dokumentasi** dan **referensi label obat**. Keputusan klinis tetap pada tenaga kesehatan.

---


## 🎯 Masalah yang Diselesaikan (Impact)
### 1) Dokumentasi konsultasi telemed itu berat & tidak terstruktur
Percakapan chat/telepon/video bisa panjang. Dokter/care team sering butuh catatan rapi untuk rekam medis, ringkasan, dan handover.

### 2) Informasi obat rentan halusinasi jika hanya mengandalkan LLM
LLM bisa salah atau “ngarang” dosis/peringatan. Dengan RAG, sistem mengambil konteks dari **label obat** sebagai sumber referensi yang bisa dicek.

---

## ✅ Output Utama
**Input**: 1 sesi percakapan dokter–pasien (dipilih berdasarkan `ID` dari dataset CSV)

**Output**:
- **Note JSON terstruktur**:
  - `chief_complaint`
  - `duration`
  - `symptoms`
  - `medical_history`
  - `medications_mentioned`
  - `red_flags_mentioned_in_text` *(berdasarkan teks, bukan diagnosis)*
  - `missing_info` *(checklist info yang belum ada di transcript)*
- **Drug Label Reference (RAG) — opsional**:
  - `dosage_and_administration`, `warnings`, `contraindications`, `drug_interactions`
  - tombol opsional untuk merangkum label agar lebih “human‑friendly”

---

## 🚀 Fitur Utama
1) **Automated Medical Scribing (LLM → JSON)**  
   Mengonversi percakapan mentah menjadi catatan terstruktur (SOAP‑lite/JSON).

2) **Medication Detection**  
   Mengekstrak nama obat yang disebut di percakapan.

3) **RAG Drug Label Reference (openFDA/DailyMed)**  
   Sistem mengambil konteks dari database lokal `drug_kb.jsonl` (hasil ekstraksi subset openFDA).

4) **Hemat Kuota & Token**  
   - **LLM Call #1 (wajib):** Generate note JSON dari **1 transcript (1 sesi)**  
   - **LLM Call #2 (opsional):** Ringkas label obat **hanya jika user klik**, biasanya **1 obat saja**  
   - **Caching** hasil agar testing tidak boros.

5) **UI Interaktif (Streamlit)**  
   Pilih `ID` → lihat transcript → generate note → lihat referensi obat.

---

## 📸 Demo & Tampilan Aplikasi (Opsional)
Tambahkan screenshot setelah jadi (placeholder):
- `assets/analysis-result-summary.png`
- `assets/analysis-result-risk&missing.png`
- `assets/analysis-result-drugs.png`

---

## 🧠 Cara Kerja (Singkat)
### A) Note Extraction
1. Dataset percakapan (CSV) di‑load oleh Python → user memilih **1 ID sesi**  
2. Sistem menyusun transcript lengkap untuk ID tersebut  
3. Transcript → **LLM** → output **JSON valid**

### B) RAG Obat (Retrieval → optional LLM summary)
1. Dari JSON note, baca `medications_mentioned`  
2. Lookup obat di **Knowledge Base lokal**: `drug_kb.jsonl`  
3. Tampilkan potongan label (dosage/warnings/contra/interactions)  
4. (Opsional) klik “Summarize Medication” → ringkasan bullet + tetap menampilkan sumber potongan label

> Penting: **LLM tidak membaca seluruh dataset percakapan** dan **tidak membaca ZIP openFDA besar**.  
> Dataset besar diproses offline oleh Python. LLM hanya menerima **1 transcript** dan/atau **potongan label relevan**.

---

## 🗂️ Sumber Data
### 1) Dataset Percakapan Dokter–Pasien (CSV)
Kolom yang dipakai:
- `ID`
- `Patient_Answer`
- `Doctor_response`

Satu sesi = banyak baris dengan `ID` yang sama. Aplikasi menggabungkan semua baris untuk membentuk transcript.

### 2) openFDA Drug Labeling (JSON)
Label obat resmi dari openFDA/DailyMed. Untuk efisiensi demo, proyek memakai **subset (1 ZIP)** lalu diproses menjadi `drug_kb.jsonl`.

---

## 🛠️ Tech Stack
- **Python 3.9+**
- **UI:** Streamlit
- **LLM:** OpenRouter API (contoh: `z-ai/glm-4.5-air:free`)
- **Data:** Pandas (CSV), JSONL

---

## 📁 Struktur Folder (Saran)
```
telemed-copilot/
  app.py                      # Streamlit app (versi paling simpel)
  prompts.py                  # prompt templates (hemat token)
  data/
    conversations.csv         # dataset percakapan (CSV)
    drug_kb.jsonl             # hasil ekstraksi openFDA (subset)
  cache/
    note_cache.json           # cache hasil LLM call #1
    medsum_cache.json         # cache hasil LLM call #2 (opsional)
  assets/                     # screenshot demo (opsional)
  requirements.txt
  .env.example
  README.md
```

---

## ⚙️ Persiapan `drug_kb.jsonl` (Subset openFDA via Kaggle API — disarankan di Colab)
Karena file openFDA besar, langkah ini lebih nyaman dilakukan di **Google Colab**.

### A) Setup Kaggle API (Colab)
1) Download API token `kaggle.json` dari akun Kaggle (Account → API → Create New Token)  
2) Upload `kaggle.json` ke Colab, lalu jalankan:

```bash
pip -q install kaggle
mkdir -p ~/.kaggle
cp kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

### B) Download dataset openFDA dan ambil 1 ZIP saja
```bash
kaggle datasets download -d ddrbcn/openfda-drug-labeling
unzip -q openfda-drug-labeling.zip -d openfda_raw
```

Pilih **1 file ZIP** label obat dari folder `openfda_raw/` (contoh salah satu `*.zip`), lalu parse dan ekstrak field penting berikut:
- `openfda.brand_name`, `openfda.generic_name`
- `dosage_and_administration`
- `warnings`
- `contraindications`
- `drug_interactions`

Outputkan menjadi `drug_kb.jsonl` dengan format minimal:
```json
{"names":["ibuprofen","advil"],"dosage":"...","warnings":"...","contra":"...","interactions":"..."}
```

Setelah selesai, download `drug_kb.jsonl` dan taruh di `data/drug_kb.jsonl` pada repo lokal.


---

## 💻 Cara Menjalankan di Lokal (Windows)
### 1) Clone repo
```bash
git clone https://github.com/USERNAME_ANDA/telemed-copilot.git
cd telemed-copilot
```

### 2) Buat virtual environment & install dependencies
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3) Konfigurasi API Key (OpenRouter)
Buat file `.env` di root folder (atau set environment variable):

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=z-ai/glm-4.5-air:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### 4) Jalankan aplikasi
```bash
streamlit run app.py
```

Buka di browser: `http://localhost:8501`

---

## 🧪 Cara Demo (Recommended)
1) Pilih satu `ID` percakapan (mis. `RES0001`) → lihat transcript  
2) Klik **Generate Note** → tampil JSON note + meds  
3) Jika meds terdeteksi → tampil potongan label (dosage/warnings/contra/interactions)  
4) (Opsional) klik **Summarize Medication** → ringkasan bullet + tetap tampilkan sumber potongan label  
5) Ganti `ID` lain untuk menunjukkan generalisasi

---

## 🔒 Safety Notes (Wajib untuk Health)
- Output tidak boleh diagnosis atau terapi.
- `red_flags_mentioned_in_text` harus berbasis teks yang disebut (bukan asumsi).
- Jika label obat tidak ditemukan → tampilkan “Not Found” (jangan mengarang).

---

## 🗺️ Roadmap (Upgrade Setelah Versi 1 Hari Jadi)
- Retrieval lebih canggih: TF‑IDF/embeddings untuk memilih potongan label paling relevan (lebih hemat token)
- Bilingual output (EN → ID) sebagai opsi
- Validasi schema JSON (pydantic/jsonschema) agar output selalu konsisten
- Logging & monitoring untuk evaluasi kualitas output LLM

---

## 👤 Kontak
**Muhammad Naufal Aqil**  
WhatsApp: **+62 859 7488 7883**  
LinkedIn: **https://linkedin.com/in/muhammad-naufal-aqil-b6114424a/**  
GitHub: **https://github.com/Naufal22**

---