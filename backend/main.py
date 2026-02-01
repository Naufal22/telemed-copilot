import os
import json
import requests
import time
from contextlib import asynccontextmanager
from typing import List, Optional, Set
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# --- 1. KONFIGURASI KEAMANAN ---
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = os.getenv("OPENROUTER_MODEL", "thudm/glm-4-9b-chat")

if not API_KEY:
    print("WARNING: API Key belum disetting di file .env!")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "drug_kb.jsonl")

# --- 2. GLOBAL DATABASE ---
DRUG_DB = []
DRUG_NAMES_INDEX = {}

# --- 3. LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global DRUG_DB, DRUG_NAMES_INDEX
    if os.path.exists(DATA_FILE):
        print(f"Loading data from {DATA_FILE}...")
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        DRUG_DB.append(data)
                        
                        # Buat index nama -> data
                        # Simpan setiap nama obat agar bisa dideteksi di transkrip
                        for name in data['names']:
                            if len(name) > 3: # Abaikan nama terlalu pendek
                                DRUG_NAMES_INDEX[name] = data
                                
                    except json.JSONDecodeError:
                        continue
            print(f"Sukses! {len(DRUG_DB)} obat dimuat. Index pencarian siap.")
        except Exception as e:
            print(f"Error loading data: {e}")
    else:
        print(f"ERROR: File database tidak ditemukan di {DATA_FILE}")
    
    yield
    
    DRUG_DB.clear()
    DRUG_NAMES_INDEX.clear()
    print("Database dibersihkan.")

# --- 4. APP SETUP ---
app = FastAPI(
    title="Telemed Copilot API",
    description="Backend RAG Real dengan Context Injection",
    version="1.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 5. MODELS ---
class DrugDetail(BaseModel):
    names: List[str]
    dosage: str
    warnings: str
    contra: str
    interactions: str

class TranscriptRequest(BaseModel):
    transcript: str

class MedicalNote(BaseModel):
    chief_complaint: str
    duration: str
    symptoms: List[str]
    medical_history: List[str]
    medications_mentioned: List[str]
    red_flags: List[str]
    missing_info: List[str]

# --- 6. HELPER FUNCTION (RAG RETRIEVER) ---
def retrieve_drug_context(transcript: str) -> str:
    """
    Mencari nama obat di dalam teks transkrip, 
    lalu mengambil detail warning/dosage-nya.
    """
    transcript_lower = transcript.lower()
    found_drugs_data = []
    seen_drug_entries = set()

    # Scan sederhana: Cek apakah nama obat ada di transkrip
    for drug_name, drug_data in DRUG_NAMES_INDEX.items():
        if drug_name in transcript_lower:
            # Gunakan dosage sebagai ID unik sementara
            drug_id = drug_data['dosage'][:20] 
            if drug_id not in seen_drug_entries:
                found_drugs_data.append(drug_data)
                seen_drug_entries.add(drug_id)
                
            # Batasi konteks maksimal 3 obat biar prompt tidak kepenuhan
            if len(found_drugs_data) >= 3:
                break
    
    # Susun teks konteks untuk LLM
    if not found_drugs_data:
        return "No specific drug information found in database."

    context_str = "--- OFFICIAL DRUG DATABASE CONTEXT ---\n"
    for d in found_drugs_data:
        main_name = d['names'][0].upper()
        context_str += f"DRUG: {main_name}\n"
        context_str += f"WARNINGS: {d['warnings'][:500]}...\n" # Potong biar hemat token
        context_str += f"DOSAGE: {d['dosage'][:300]}...\n\n"
    
    return context_str

# --- 7. ENDPOINTS ---
@app.get("/")
def root():
    return {"status": "ok", "message": "Telemed Copilot RAG API is running"}

@app.get("/drugs/search", response_model=List[str])
def search_drugs(q: str = Query(..., min_length=3)):
    keyword = q.lower()
    results = []
    for entry in DRUG_DB:
        for name in entry['names']:
            if keyword in name:
                display_name = entry['names'][0].title() 
                if display_name not in results:
                    results.append(display_name)
                break 
        if len(results) >= 10: break
    return results

@app.get("/drugs/{drug_name}", response_model=DrugDetail)
def get_drug_detail(drug_name: str):
    target = drug_name.lower()
    for entry in DRUG_DB:
        if target in entry['names']:
            return DrugDetail(
                names=entry['names'],
                dosage=entry['dosage'],
                warnings=entry['warnings'],
                contra=entry['contra'],
                interactions=entry['interactions']
            )
    raise HTTPException(status_code=404, detail="Obat tidak ditemukan")

# --- 8. ENDPOINT LLM DENGAN RAG ---
@app.post("/generate-note", response_model=MedicalNote)
def generate_medical_note(request: TranscriptRequest):
    start_time = time.time()
    
    print("\n[1/4] Menerima request...")
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key error")

    # [STEP RAG 1] Retrieve
    print(f"[2/4] Mencari konteks obat untuk transkrip sepanjang {len(request.transcript)} karakter...")
    drug_context = retrieve_drug_context(request.transcript)
    print(f"      -> Ditemukan konteks obat sepanjang {len(drug_context)} karakter.")
    
    # [STEP RAG 2] Augment - Prompt Tetap Sama
    system_prompt = f"""
    You are an expert AI Medical Scribe assisting a doctor. 
    
    Your task is to analyze the doctor-patient conversation and extract structured information.
    
    CONTEXT FROM DATABASE (Drug Info):
    {drug_context}
    
    INSTRUCTIONS:
    1. Analyze the transcript based on the drug context provided.
    2. For 'red_flags': 
       - Flag any contraindications or interactions (e.g. Aspirin + Ibuprofen).
       - Do NOT make definitive diagnoses.
    3. For 'missing_info':
       - List critical clinical information that was NOT asked.
    
    Strictly output ONLY a valid JSON object. 
    
    JSON SCHEMA:
    {{
        "chief_complaint": "string",
        "duration": "string",
        "symptoms": ["string", "string"],
        "medical_history": ["string"],
        "medications_mentioned": ["string"],
        "red_flags": ["string"],
        "missing_info": ["string"]
    }}
    """

    user_prompt = f"Here is the transcript:\n\n{request.transcript}"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
    }
    
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
    }

    print(f"[3/4] Mengirim ke LLM ({MODEL_ID})... Mohon tunggu...")
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=180
        )
        
        if response.status_code != 200:
            print(f"Error Detail: {response.text}")
        response.raise_for_status()
        
        content = response.json()['choices'][0]['message']['content']
        
        # --- \ROBUST JSON PARSER ---
        print(f"[DEBUG] Raw Content dari LLM (100 char pertama): {content[:100]}...") # Cek apa yang bikin error
        
        # Cari posisi kurung kurawal pertama '{' dan terakhir '}'
        start_index = content.find('{')
        end_index = content.rfind('}')
        
        if start_index != -1 and end_index != -1:
            # Potong teksnya, ambil hanya yang ada di dalam kurung
            json_str = content[start_index : end_index + 1]
            parsed_note = json.loads(json_str)
            
            end_time = time.time()
            print(f"[4/4] Selesai! Waktu total: {end_time - start_time:.2f} detik.")
            return parsed_note
        else:
            raise ValueError("LLM tidak mengembalikan format JSON yang valid (kurung kurawal tidak ditemukan).")

    except Exception as e:
        print(f" Error: {e}")
        # Tampilkan raw content biar kita tau salahnya dimana kalau masih error
        raise HTTPException(status_code=500, detail=f"Gagal memproses output AI. Error: {str(e)}")