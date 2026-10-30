"""Olah data karyawan dan susun HTML dashboard.

File ini tidak memakai Streamlit, jadi bisa diuji terpisah:
    python core.py            -> membuat preview.html dari data cadangan
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import io
import json
import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
ASSETS = BASE / "assets"
TEMPLATE = BASE / "templates" / "dashboard.html"
LOCAL_FILE = BASE / "data" / "DATABASE_LABOUR_KARYAWAN.xlsx"
SHEET_NAME = "DATA_KARYAWAN"

# ---------------------------------------------------------------- sumber data
def sheet_id(url: str) -> str | None:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url or "")
    return m.group(1) if m else None


def read_google_sheet(url: str) -> pd.DataFrame:
    """Baca tab DATA_KARYAWAN dari Google Sheets yang dibagikan 'Siapa saja yang memiliki link'."""
    sid = sheet_id(url)
    if not sid:
        raise ValueError("Link Google Sheets tidak valid")
    # 1) unduh sebagai xlsx: tipe data (tanggal, angka) tetap utuh
    try:
        xurl = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=xlsx"
        return pd.read_excel(xurl, sheet_name=SHEET_NAME, dtype={"NIK": str})
    except Exception:
        pass
    # 2) cadangan: CSV per tab lewat gviz
    curl = f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
    return pd.read_csv(curl, dtype=str)


def read_local() -> pd.DataFrame:
    return pd.read_excel(LOCAL_FILE, sheet_name=SHEET_NAME, dtype={"NIK": str})


# ---------------------------------------------------------------- pembersihan
def to_date(s: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    for v_idx, v in s.items():
        if isinstance(v, (dt.datetime, dt.date, pd.Timestamp)):
            out[v_idx] = pd.Timestamp(v)
            continue
        if v is None or (isinstance(v, float) and pd.isna(v)):
            continue
        t = str(v).strip()
        for f in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d-%m-%y"):
            try:
                d = dt.datetime.strptime(t, f)
                if f.endswith("%y") and d.year > dt.date.today().year + 2:
                    d = d.replace(year=d.year - 100)  # 15/03/65 -> 1965, bukan 2065
                out[v_idx] = pd.Timestamp(d)
                break
            except ValueError:
                continue
    return out


POS_RULES = [
    ("Produksi", r"produksi|production|enamel|emulsion|mixing|filling|press|welding|las\b|painting|finishing|cutting|assembl|kiln|molding|gilas|giling|glaze"),
    ("Helper", r"helper|asisten|kenek|pembantu|labour|buruh"),
    ("Packing", r"pack|kemas|labeling|sortir|sorting|pilah"),
    ("Driver / Transport", r"driver|sopir|supir|kurir|forklift|pengemudi|rider|delivery|reach truck"),
    ("Gudang / Logistik", r"gudang|warehouse|logistic|logistik|inventory|bongkar|muat|checker|loading|tkbm|e-commerce|ecommerce|reliever|picker|stock"),
    ("Sales / SPG / BA", r"spg|spb|\bba\b|sales|promotor|merchandis|host|live|kasir|toko|store"),
    ("Teknisi / Maintenance", r"mekanik|mechanic|teknisi|technician|maintenance|electric|listrik|genset|utility|engineer"),
    ("Quality (QC / QA)", r"\bqc\b|\bqa\b|quality|inspect"),
    ("Admin / Office", r"inputor|input|admin|staff|staf|office|clerk|sekretar|\bhr|finance|accounting|purchasing|data entry|reception|resepsionis"),
    ("Keamanan / Kebersihan", r"security|satpam|cleaning|kebersihan|office boy|\bob\b|\bcs\b|janitor|garden|taman"),
    ("Operator mesin", r"operator|extruder|injection|injectition|moulding|mold|\bim\b|im\.|dry fact|printing|assy|reach"),
    ("Project / Supervisor", r"project|supervisor|leader|koordinator|coordinator|foreman|manager|\bspv\b"),
]


def pos_group(v) -> str:
    if not isinstance(v, str) or not v.strip():
        return "Lainnya"
    s = v.lower()
    for g, pat in POS_RULES:
        if re.search(pat, s):
            return g
    return "Lainnya"


def clean_kota(v) -> str:
    if not isinstance(v, str) or not v.strip():
        return "Tidak diketahui"
    v = re.sub(r"^(kab\.?|kota)\s*", "", v.strip(), flags=re.I).strip()
    v = v.title()
    return {"Jogja": "Yogyakarta", "Tebingtinggi": "Tebing Tinggi"}.get(v, v)


def prepare(raw: pd.DataFrame, today: dt.date) -> dict:
    """Ubah data mentah jadi data ringkas untuk dashboard (tanpa NIK, alamat, telepon)."""
    df = raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df[df["NAMA LENGKAP"].notna() & (df["NAMA LENGKAP"].astype(str).str.strip() != "")]
    T = pd.Timestamp(today)

    txt = lambda c: df[c].astype(str).str.strip().where(df[c].notna(), "")
    status = txt("STATUS").str.upper().replace({"MENINGGAL": "MENINGGAL DUNIA", "": "TIDAK DIKETAHUI"})
    site = txt("SITE")
    klien = site.str.replace(r"\s*\(.*?\)\s*", " ", regex=True).str.strip().replace("", "Tidak diketahui")
    gender = txt("JENIS KELAMIN").str.lower().map({"laki-laki": 0, "perempuan": 1}).fillna(0).astype(int)
    tl = to_date(df["TANGGAL LAHIR"])
    age = ((T - tl).dt.days / 365.25).fillna(30).round(1)
    doj = to_date(df["DOJ"])
    mk = ((T - doj).dt.days / 365.25).clip(lower=0).fillna(0).round(1)
    end = to_date(df["END"]) if "END" in df else pd.Series(pd.NaT, index=df.index)
    sisa = (end - T).dt.days
    tipe = txt("TIPE KONTRAK").str.upper().str.split(" - ").str[0].replace("", "PKWT")
    posisi = txt("POSISI").replace("", "Tidak diketahui")

    def kflag(s, st):
        if st != "AKTIF" or pd.isna(s):
            return 0
        return 1 if s < 0 else 2 if s <= 30 else 3 if s <= 60 else 4 if s <= 90 else 5

    def idx(series):
        order = series.value_counts().index.tolist()
        m = {v: i for i, v in enumerate(order)}
        return order, series.map(m).astype(int).tolist()

    K, ki = idx(klien)
    W, wi = idx(txt("KAB KOTA").map(clean_kota))
    P, pi = idx(posisi.map(pos_group))
    S, si = idx(status)
    TT, ti = idx(tipe)
    PR, pri = idx(posisi)
    no = pd.to_numeric(df["NO"], errors="coerce").fillna(0).astype(int).tolist() if "NO" in df else list(range(1, len(df) + 1))

    rows = []
    for j, i in enumerate(df.index):
        d = doj[i]
        if pd.isna(d):
            continue
        rows.append([str(df.at[i, "NAMA LENGKAP"]).strip(), ki[j], wi[j], pi[j], si[j], d.strftime("%Y-%m-%d"),
                     int(gender[i]), float(age[i]), ti[j], float(mk[i]), kflag(sisa[i], status[i]), pri[j], int(no[j])])
    return {"k": K, "w": W, "p": P, "s": S, "t": TT, "pr": PR, "r": rows}


# ---------------------------------------------------------------- HTML
def _uri(name: str) -> str:
    p = ASSETS / name
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


_IMG_CACHE: dict[str, str] = {}


def build_html(data: dict, today: dt.date, sumber: str) -> str:
    if not _IMG_CACHE:
        for key, f in {"HERO": "hero.jpg", "LOGO_TUTWURI": "logo_tutwuri.png", "LOGO_UPN": "logo_upn.png",
                       "LOGO_BLU": "logo_blu.png", "GEDUNG_UPN": "gedung_upn.jpg",
                       "LOGO_SHELTER": "logo_shelter.jpg"}.items():
            _IMG_CACHE[key] = _uri(f)
    html = TEMPLATE.read_text(encoding="utf-8")
    for k, v in _IMG_CACHE.items():
        html = html.replace("{{" + k + "}}", v)
    meta = {"today": today.isoformat(), "sumber": sumber}
    html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("__META__", json.dumps(meta, ensure_ascii=False))
    return _ascii_safe(html)


def _ascii_safe(html: str) -> str:
    """Ubah karakter non-ASCII (▲, ≤, “ ”) jadi kode aman agar tampil benar di bingkai Streamlit."""
    parts = re.split(r"(<script>.*?</script>)", html, flags=re.S)
    out = []
    for p in parts:
        if p.startswith("<script>"):
            out.append("".join(c if ord(c) < 128 else
                               (f"\\u{ord(c):04x}" if ord(c) < 0x10000 else
                                "".join(f"\\u{u:04x}" for u in (0xD800 + ((ord(c) - 0x10000) >> 10), 0xDC00 + ((ord(c) - 0x10000) & 0x3FF))))
                               for c in p))
        else:
            out.append(p.encode("ascii", "xmlcharrefreplace").decode())
    return "".join(out)


def data_hash(data: dict) -> str:
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()[:10]


if __name__ == "__main__":
    today = dt.date(2026, 10, 29)
    d = prepare(read_local(), today)
    out = BASE / "preview.html"
    out.write_text(build_html(d, today, "File cadangan (data/DATABASE_LABOUR_KARYAWAN.xlsx)"), encoding="utf-8")
    print(len(d["r"]), "baris ->", out)
