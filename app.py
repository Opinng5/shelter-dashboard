"""Dashboard Analisis Karyawan - PT Shelter Indonesia Gemilang (Streamlit).

Jalankan:  streamlit run app.py
Data dibaca dari Google Sheets (tab DATA_KARYAWAN) dan diperbarui otomatis.
"""
import datetime as dt
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

import core

# Link Google Sheets. Bisa diganti lewat Secrets: SHEET_URL = "https://docs.google.com/..."
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1RJzsCjuPdPftZnmSHl9HmFXRJ-mNiVX5gQtqAvdt1SU/edit"


def secret(key, default):
    try:
        return st.secrets.get(key, default)
    except Exception:  # belum ada secrets.toml
        return default


SHEET_URL = secret("SHEET_URL", DEFAULT_SHEET_URL)
REFRESH_SECONDS = int(secret("REFRESH_SECONDS", 60))

st.set_page_config(
    page_title="Dashboard Analisis Karyawan | SHELTER",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Sembunyikan elemen bawaan Streamlit supaya dashboard tampil penuh seperti desain
st.markdown(
    """
    <style>
      header[data-testid="stHeader"], footer, #MainMenu,
      [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display:none !important;}
      .block-container, [data-testid="stMainBlockContainer"] {padding:0 !important; max-width:100% !important;}
      [data-testid="stAppViewContainer"], .stApp {background:#EEF6FD;}
      [data-testid="stVerticalBlock"] {gap:0 !important;}
      iframe {display:block; border:0; width:100%;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def load_data(url: str):
    """Ambil data terbaru. Disimpan sementara selama REFRESH_SECONDS detik."""
    if url:
        try:
            return core.read_google_sheet(url), "Google Sheets DATA KARYAWAN"
        except Exception as e:  # jaringan putus / sheet belum dibagikan
            return core.read_local(), f"File cadangan (Google Sheets gagal dibaca: {type(e).__name__})"
    return core.read_local(), "File cadangan (data/DATABASE_LABOUR_KARYAWAN.xlsx)"


@st.fragment(run_every=REFRESH_SECONDS)
def dashboard():
    raw, sumber = load_data(SHEET_URL)
    today = dt.datetime.now(ZoneInfo("Asia/Jakarta")).date()
    data = core.prepare(raw, today)
    html = core.build_html(data, today, sumber)
    # Tinggi awal 941px (ukuran desain); halaman menyesuaikan sendiri dengan lebar layar.
    components.html(html, height=941, scrolling=False)


dashboard()
