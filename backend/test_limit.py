import json
import time
import urllib.error
import urllib.request

URL = "http://localhost:8000/predict"

body = {"age":56,"gender":"Male","bmi":25.2,"children":2,"smoker":"Yes","region":"Northeast",
        "occupation":"Driver","annual_income_usd":77885,"exercise_level":"Moderate",
        "chronic_diseases":0,"alcohol_consumption_per_week":13,"insurance_plan":"Basic",
        "diabetes":"Yes","cholesterol":224,"sleep_hours":7.6,"stress_level":4.5,
        "marital_status":"Married","blood_pressure_systolic":150,"blood_pressure_diastolic":95}


def kirim():
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        return urllib.request.urlopen(req).status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def ronde(nama, jumlah):
    hasil = [kirim() for _ in range(jumlah)]
    print(nama, [kode for kode, _ in hasil])
    for pesan in sorted({m for kode, m in hasil if kode == 429}):
        print("   alasan 429:", pesan)


# Ronde 1: batas per menit (10) harus kena di request ke-11
ronde("Ronde 1 (12 request):", 12)

print("Tunggu 61 detik biar jatah per menit reset...")
time.sleep(61)

# Ronde 2: 10 request lolos lagi -> total hari ini 20
ronde("Ronde 2 (12 request):", 12)

print("Tunggu 61 detik lagi...")
time.sleep(61)

# Ronde 3: jatah menit sudah reset, tapi jatah harian (20) sudah habis
ronde("Ronde 3 (3 request): ", 3)