"use client";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const sel = (name, label, options) => ({
  name,
  label,
  type: "select",
  options,
});
const num = (name, label, min, max, step = 1, unit = "") => ({
  name,
  label,
  type: "number",
  min,
  max,
  step,
  unit,
});

const SECTIONS = [
  {
    title: "Profil",
    fields: [
      num("age", "Usia", 18, 100, 1, "tahun"),
      sel("gender", "Jenis kelamin", ["Female", "Male"]),
      sel("marital_status", "Status pernikahan", [
        "Single",
        "Married",
        "Divorced",
        "Widowed",
      ]),
      num("children", "Jumlah anak", 0, 10),
      sel("occupation", "Pekerjaan", [
        "Construction Worker",
        "Doctor",
        "Driver",
        "Engineer",
        "Lawyer",
        "Manager",
        "Nurse",
        "Office Worker",
        "Retail Worker",
        "Teacher",
        "Technician",
      ]),
      num("annual_income_usd", "Pendapatan tahunan", 0, 1000000, 1000, "USD"),
      sel("region", "Wilayah", [
        "Central",
        "Northeast",
        "Northwest",
        "Southeast",
        "Southwest",
      ]),
    ],
  },
  {
    title: "Gaya hidup",
    fields: [
      sel("smoker", "Perokok", ["No", "Yes"]),
      sel("exercise_level", "Tingkat olahraga", ["Low", "Moderate", "High"]),
      num(
        "alcohol_consumption_per_week",
        "Alkohol per minggu",
        0,
        100,
        1,
        "porsi",
      ),
      num("sleep_hours", "Jam tidur", 0, 24, 0.1, "jam"),
      num("stress_level", "Tingkat stres", 0, 10, 0.1, "0–10"),
    ],
  },
  {
    title: "Kondisi kesehatan",
    fields: [
      num("bmi", "BMI", 10, 70, 0.1),
      num(
        "blood_pressure_systolic",
        "Tekanan darah sistolik",
        60,
        250,
        1,
        "mmHg",
      ),
      num(
        "blood_pressure_diastolic",
        "Tekanan darah diastolik",
        30,
        150,
        1,
        "mmHg",
      ),
      num("cholesterol", "Kolesterol", 50, 500, 1, "mg/dL"),
      num("chronic_diseases", "Jumlah penyakit kronis", 0, 10),
      sel("diabetes", "Diabetes", ["No", "Yes"]),
    ],
  },
  {
    title: "Asuransi",
    fields: [
      sel("insurance_plan", "Plan", ["Basic", "Standard", "Gold", "Premium"]),
    ],
  },
];

const CONTOH = {
  age: "56",
  gender: "Male",
  marital_status: "Married",
  children: "0",
  occupation: "Driver",
  annual_income_usd: "0",
  region: "Northeast",
  smoker: "Yes",
  exercise_level: "Moderate",
  alcohol_consumption_per_week: "13",
  sleep_hours: "7.6",
  stress_level: "4.5",
  bmi: "25.2",
  blood_pressure_systolic: "150",
  blood_pressure_diastolic: "95",
  cholesterol: "224",
  chronic_diseases: "0",
  diabetes: "Yes",
  insurance_plan: "Basic",
};

const NUMERIC = new Set(
  SECTIONS.flatMap((s) => s.fields)
    .filter((f) => f.type === "number")
    .map((f) => f.name),
);
const usd = (v) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);

function errorText(data) {
  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`)
      .join("; ");
  }
  return "Server menolak permintaan.";
}

function Emblem() {
  return (
    <svg className="emblem" viewBox="0 0 64 72" aria-hidden="true">
      <path
        d="M32 3 6 13v20c0 18 11 31 26 37 15-6 26-19 26-37V13Z"
        fill="#b9e3dd"
        stroke="#0f766e"
        strokeWidth="3"
        strokeLinejoin="round"
      />
      <path d="M27 21h10v10h10v10H37v10H27V41H17V31h10Z" fill="#0f766e" />
    </svg>
  );
}

function RangeBar({ result }) {
  const max = result.batas_atas * 1.08;
  const pct = (v) => `${(v / max) * 100}%`;
  return (
    <div
      className="range"
      role="img"
      aria-label={`Prediksi ${usd(result.prediksi_usd)}, rentang ${usd(result.batas_bawah)} sampai ${usd(result.batas_atas)}`}
    >
      <div className="track">
        <div
          className="span"
          style={{
            left: pct(result.batas_bawah),
            width: `calc(${pct(result.batas_atas)} - ${pct(result.batas_bawah)})`,
          }}
        />
        <div className="tick" style={{ left: pct(result.prediksi_usd) }} />
      </div>
      <div className="ends">
        <span style={{ left: pct(result.batas_bawah) }}>
          {usd(result.batas_bawah)}
        </span>
        <span style={{ left: pct(result.batas_atas) }}>
          {usd(result.batas_atas)}
        </span>
      </div>
    </div>
  );
}

export default function Page() {
  const [form, setForm] = useState(CONTOH);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (name) => (e) =>
    setForm((f) => ({ ...f, [name]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const payload = Object.fromEntries(
      Object.entries(form).map(([k, v]) => [k, NUMERIC.has(k) ? Number(v) : v]),
    );
    try {
      const res = await fetch(`${API}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.status === 429) {
        throw new Error(
          data.jenis === "hari"
            ? "Maaf, kamu sudah tidak bisa menggunakannya lagi hari ini. Silakan coba lagi besok."
            : "Terlalu banyak permintaan dalam waktu singkat. Tunggu sekitar 1 menit, lalu coba lagi.",
        );
      }
      if (!res.ok) throw new Error(errorText(data));
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(
        err instanceof TypeError
          ? `Tidak bisa terhubung ke ${API}. Pastikan backend FastAPI sudah jalan.`
          : err.message,
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header>
        <h1>Estimasi biaya medis tahunan</h1>
        <p>
          Isi data pelanggan, lalu lihat perkiraan biaya setahun dalam USD
          beserta rentang 95%.
        </p>
      </header>

      <div className="layout">
        <form onSubmit={submit}>
          {SECTIONS.map((s) => (
            <fieldset key={s.title}>
              <legend>{s.title}</legend>
              <div className="grid">
                {s.fields.map((f) => (
                  <label key={f.name}>
                    <span>
                      {f.label}
                      {f.unit && <em> ({f.unit})</em>}
                    </span>
                    {f.type === "select" ? (
                      <select value={form[f.name]} onChange={set(f.name)}>
                        {f.options.map((o) => (
                          <option key={o}>{o}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="number"
                        required
                        min={f.min}
                        max={f.max}
                        step={f.step}
                        value={form[f.name]}
                        onChange={set(f.name)}
                      />
                    )}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
          <div className="actions">
            <button type="submit" disabled={loading}>
              {loading ? "Menghitung…" : "Hitung estimasi"}
            </button>
            <button
              type="button"
              className="ghost"
              onClick={() => setForm(CONTOH)}
            >
              Isi data contoh
            </button>
          </div>
        </form>

        <aside aria-live="polite">
          <div className="aside-head">
            <Emblem />
            <strong>
              Estimasi biaya medis
              <small>Berdasarkan 7.500 data pelanggan</small>
            </strong>
          </div>
          {error && <p className="error">{error}</p>}
          {!error && !result && (
            <p className="empty">
              Hasil muncul di sini setelah kamu menekan “Hitung estimasi”.
            </p>
          )}
          {result && (
            <>
              <p className="label">Perkiraan biaya setahun</p>
              <p className="big">{usd(result.prediksi_usd)}</p>
              <RangeBar result={result} />
              <p className="note">
                Sekitar 95% kasus di data uji jatuh di rentang{" "}
                {usd(result.batas_bawah)} sampai {usd(result.batas_atas)}.
                Rentangnya lebar karena ada variasi biaya yang tidak bisa
                dijelaskan fitur yang tersedia.
              </p>
              <dl>
                <dt>Kategori BMI</dt>
                <dd>{result.bmi_category}</dd>
                <dt>Kategori tekanan darah</dt>
                <dd>{result.bp_category}</dd>
              </dl>
            </>
          )}
        </aside>
      </div>
      <footer>
        Model menangkap pola asosiasi di data, bukan hubungan sebab-akibat.
        Bukan nasihat medis atau penawaran asuransi.
      </footer>
    </main>
  );
}
