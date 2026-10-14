import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

BASE = Path(__file__).parent
model = joblib.load(BASE / "model" / "model_final.joblib")

# Interval 95% dari test set (rasio aktual / prediksi).
# Kalau ada backend/metadata.json, nilainya diambil dari sana.
RATIO_LOWER, RATIO_UPPER = 0.614462514402958, 1.4445040580246047
meta_path = BASE / "metadata.json"
if meta_path.exists():
    itv = json.loads(meta_path.read_text(encoding="utf-8"))["interval_estimasi"]
    RATIO_LOWER, RATIO_UPPER = itv["ratio_lower"], itv["ratio_upper"]

# Urutan kolom persis seperti X saat training
FITUR = [
    "age", "gender", "bmi", "children", "smoker", "region", "occupation",
    "annual_income_usd", "exercise_level", "chronic_diseases",
    "alcohol_consumption_per_week", "insurance_plan", "diabetes", "cholesterol",
    "sleep_hours", "stress_level", "marital_status", "bp_category",
    "bmi_x_smoker", "bmi_x_age", "bmi_x_diabetes", "bmi_x_chronic",
    "bmi_x_exercise", "bmi_category",
]

YN = {"No": 0, "Yes": 1}
EXERCISE = {"Low": 0, "Moderate": 1, "High": 2}
PLAN = {"Basic": 0, "Standard": 1, "Gold": 2, "Premium": 3}
BP = {"normal": 0, "elevated": 1, "stage_1": 2, "stage_2": 3}
BMI = {"underweight": 0, "normal": 1, "overweight": 2, "obese": 3}


class Payload(BaseModel):
    age: int = Field(ge=18, le=100)
    gender: Literal["Female", "Male"]
    bmi: float = Field(ge=10, le=70)
    children: int = Field(ge=0, le=10)
    smoker: Literal["No", "Yes"]
    region: Literal["Central", "Northeast", "Northwest", "Southeast", "Southwest"]
    occupation: Literal[
        "Construction Worker", "Doctor", "Driver", "Engineer", "Lawyer", "Manager",
        "Nurse", "Office Worker", "Retail Worker", "Teacher", "Technician",
    ]
    annual_income_usd: int = Field(ge=0)
    exercise_level: Literal["Low", "Moderate", "High"]
    chronic_diseases: int = Field(ge=0, le=10)
    alcohol_consumption_per_week: int = Field(ge=0, le=100)
    insurance_plan: Literal["Basic", "Standard", "Gold", "Premium"]
    diabetes: Literal["No", "Yes"]
    cholesterol: int = Field(ge=50, le=500)
    sleep_hours: float = Field(ge=0, le=24)
    stress_level: float = Field(ge=0, le=10)
    marital_status: Literal["Divorced", "Married", "Single", "Widowed"]
    blood_pressure_systolic: int = Field(ge=60, le=250)
    blood_pressure_diastolic: int = Field(ge=30, le=150)


def bp_label(sys_: int, dia: int) -> str:
    if sys_ >= 140 or dia >= 90:
        return "stage_2"
    if sys_ >= 130 or dia >= 80:
        return "stage_1"
    if sys_ >= 120:
        return "elevated"
    return "normal"


def bmi_label(b: float) -> str:  # WHO, batas bawah inklusif
    if b < 18.5:
        return "underweight"
    if b < 25:
        return "normal"
    if b < 30:
        return "overweight"
    return "obese"


def siapkan_input(p: Payload):
    bp, bc = bp_label(p.blood_pressure_systolic, p.blood_pressure_diastolic), bmi_label(p.bmi)
    smoker, diabetes, exercise = YN[p.smoker], YN[p.diabetes], EXERCISE[p.exercise_level]
    row = {
        "age": p.age,
        "gender": {"Female": 0, "Male": 1}[p.gender],
        "bmi": p.bmi,
        "children": p.children,
        "smoker": smoker,
        "region": p.region,
        "occupation": p.occupation,
        "annual_income_usd": p.annual_income_usd,
        "exercise_level": exercise,
        "chronic_diseases": p.chronic_diseases,
        "alcohol_consumption_per_week": p.alcohol_consumption_per_week,
        "insurance_plan": PLAN[p.insurance_plan],
        "diabetes": diabetes,
        "cholesterol": p.cholesterol,
        "sleep_hours": p.sleep_hours,
        "stress_level": p.stress_level,
        "marital_status": p.marital_status,
        "bp_category": BP[bp],
        "bmi_x_smoker": p.bmi * smoker,
        "bmi_x_age": p.bmi * p.age,
        "bmi_x_diabetes": p.bmi * diabetes,
        "bmi_x_chronic": p.bmi * p.chronic_diseases,
        "bmi_x_exercise": p.bmi * exercise,
        "bmi_category": BMI[bc],
    }
    return pd.DataFrame([row])[FITUR], bp, bc


PROD = os.getenv("ENV") == "production"
limiter = Limiter(key_func=get_remote_address)

# Di produksi, halaman /docs dimatikan (set ENV=production di Render)
app = FastAPI(
    title="Prediksi Biaya Medis Tahunan",
    docs_url=None if PROD else "/docs",
    redoc_url=None if PROD else "/redoc",
    openapi_url=None if PROD else "/openapi.json",
)
app.state.limiter = limiter


# ---- Batas harian (hitungan disimpan di memori server) ----
BATAS_HARIAN = 20
WIB = timezone(timedelta(hours=7))  # reset tiap tengah malam WIB
pemakaian_harian = {}  # ip -> (tanggal, jumlah prediksi sukses)


class LimitHarian(Exception):
    pass


def _hari_ini():
    return datetime.now(WIB).date()


def cek_harian(request: Request):
    """Jalan SEBELUM batas per menit, supaya pesan 'habis hari ini' langsung muncul."""
    tgl, n = pemakaian_harian.get(get_remote_address(request), (_hari_ini(), 0))
    if tgl == _hari_ini() and n >= BATAS_HARIAN:
        raise LimitHarian()


def catat_harian(request: Request):
    ip, hari = get_remote_address(request), _hari_ini()
    tgl, n = pemakaian_harian.get(ip, (hari, 0))
    pemakaian_harian[ip] = (hari, (n if tgl == hari else 0) + 1)


async def limit_menit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"jenis": "menit", "pesan": "Terlalu banyak permintaan. Tunggu sekitar 1 menit, lalu coba lagi."},
    )


async def limit_harian_handler(request: Request, exc: LimitHarian):
    return JSONResponse(
        status_code=429,
        content={"jenis": "hari", "pesan": "Jatah estimasi hari ini sudah habis. Silakan coba lagi besok."},
    )


app.add_exception_handler(RateLimitExceeded, limit_menit_handler)
app.add_exception_handler(LimitHarian, limit_harian_handler)

# Domain frontend yang diizinkan, contoh: ALLOWED_ORIGINS=https://insurance-app.vercel.app
ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"] + [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", dependencies=[Depends(cek_harian)])
@limiter.limit("10/minute")
def predict(request: Request, p: Payload):
    catat_harian(request)
    X, bp, bc = siapkan_input(p)
    pred = float(model.predict(X)[0])
    return {
        "prediksi_usd": round(pred, 2),
        "batas_bawah": round(pred * RATIO_LOWER, 2),
        "batas_atas": round(pred * RATIO_UPPER, 2),
        "bp_category": bp,
        "bmi_category": bc,
    }