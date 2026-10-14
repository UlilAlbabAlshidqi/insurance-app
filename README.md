# Estimasi Biaya Medis Tahunan (FastAPI + Next.js)

```
insurance-app/
├── backend/   FastAPI + model_final.joblib
└── frontend/  Next.js (App Router)
```

## 1. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Cek: http://localhost:8000/docs

`scikit-learn` sudah dipin ke 1.6.1 (versi yang dipakai model di pickle). Kalau load gagal di versi catboost lain,
samakan dengan `meta['model']['versions']` di metadata.json.

Opsional: salin `metadata.json` dari Drive ke `backend/`. Kalau ada, interval diambil dari file itu;
kalau tidak, dipakai nilai bawaan di `main.py` (0.6145 dan 1.4445).

## 2. Frontend
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```
Buka http://localhost:3000. Kalau backend nggak di port 8000, ubah `NEXT_PUBLIC_API_URL`.

## Contoh request
```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{
  "age":56,"gender":"Male","bmi":25.2,"children":2,"smoker":"Yes","region":"Northeast",
  "occupation":"Driver","annual_income_usd":77885,"exercise_level":"Moderate",
  "chronic_diseases":0,"alcohol_consumption_per_week":13,"insurance_plan":"Basic",
  "diabetes":"Yes","cholesterol":224,"sleep_hours":7.6,"stress_level":4.5,
  "marital_status":"Married","blood_pressure_systolic":150,"blood_pressure_diastolic":95}'
```

## Deploy
Tambahkan domain frontend ke `allow_origins` di `backend/main.py`.
