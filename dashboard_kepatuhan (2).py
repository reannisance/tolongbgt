
import streamlit as st
import pandas as pd
import numpy as np
import calendar

# -------------------- PAGE SETUP -------------------- #
st.set_page_config(page_title="Dashboard Kepatuhan Pajak", layout="wide")
st.markdown("<h2 style='text-align: center;'>📊 Dashboard Kepatuhan Pajak</h2>", unsafe_allow_html=True)

# -------------------- INPUTS -------------------- #
with st.sidebar:
    st.markdown("## 🧭 Filter Data")
    jenis_pajak = st.selectbox("Pilih Jenis Pajak", ["HIBURAN", "MAKAN MINUM"])
    uploaded_file = st.file_uploader(f"📁 Upload File Excel untuk Pajak {jenis_pajak}", type=["xlsx"])
    if uploaded_file:
        xls = pd.ExcelFile(uploaded_file)
        sheet = st.selectbox("📑 Pilih Nama Sheet", xls.sheet_names)
        tahun_pajak = st.number_input("📅 Pilih Tahun Pajak", min_value=2000, max_value=2100, value=2024)
    else:
        sheet = None
        tahun_pajak = None

# -------------------- PROCESSING -------------------- #
if uploaded_file and sheet:
    df = pd.read_excel(uploaded_file, sheet_name=sheet)

    # Normalisasi nama kolom
    df.columns = df.columns.str.strip().str.upper()

    # Validasi kolom wajib
    kolom_wajib = ["NAMA OP", "UPPPD", "STATUS", "TMT"]
    if jenis_pajak == "HIBURAN":
        kolom_wajib.append("KLASIFIKASI")
    for kolom in kolom_wajib:
        if kolom not in df.columns:
            st.error(f"Kolom wajib '{kolom}' tidak ditemukan di file Excel.")
            st.stop()

    # Identifikasi kolom pembayaran (tipe datetime dan numerik)
    kolom_bulan = [col for col in df.columns if isinstance(col, pd.Timestamp) or '20' in str(col)]
    kolom_bulan = [col for col in kolom_bulan if str(tahun_pajak) in str(col)]

    # Format tanggal
    df['TMT'] = pd.to_datetime(df['TMT'], errors='coerce')

    # Hitung bulan aktif
    def hitung_bulan_aktif(tmt):
        if pd.isna(tmt): return 12
        mulai = max(tmt.to_period('M').start_time, pd.Timestamp(f"{tahun_pajak}-01-01"))
        akhir = pd.Timestamp(f"{tahun_pajak}-12-31")
        return max(0, (akhir.to_period("M") - mulai.to_period("M")).n + 1)

    df["Bulan Aktif"] = df["TMT"].apply(hitung_bulan_aktif)

    # Hitung bulan pembayaran
    df["Bulan Pembayaran"] = df[kolom_bulan].gt(0).sum(axis=1)

    # Hitung total pembayaran
    df["Total Pembayaran"] = df[kolom_bulan].sum(axis=1)

    # Hitung rata-rata
    df["Rata-rata"] = df["Total Pembayaran"] / df["Bulan Pembayaran"].replace(0, np.nan)

    # Kepatuhan
    def klasifikasi_kepatuhan(row):
        selisih = row["Bulan Aktif"] - row["Bulan Pembayaran"]
        if selisih <= 0:
            return "PATUH"
        elif selisih <= 3:
            return "KURANG PATUH"
        else:
            return "TIDAK PATUH"

    df["Kepatuhan"] = df.apply(klasifikasi_kepatuhan, axis=1)
    df["Kepatuhan (%)"] = (df["Bulan Pembayaran"] / df["Bulan Aktif"].replace(0, np.nan)) * 100

    # -------------------- FILTER -------------------- #
    # Sidebar filter
    daftar_upppd = ['Semua'] + sorted(df['UPPPD'].dropna().unique().tolist())
    upppd = st.sidebar.selectbox("🏢 Pilih UPPPD", daftar_upppd)
    if upppd != "Semua":
        df = df[df["UPPPD"] == upppd]

    if jenis_pajak == "HIBURAN":
        daftar_klasifikasi = ['Semua'] + sorted(df['KLASIFIKASI'].dropna().unique().tolist())
        klasifikasi = st.sidebar.selectbox("📂 Pilih Klasifikasi", daftar_klasifikasi)
        if klasifikasi != "Semua":
            df = df[df["KLASIFIKASI"] == klasifikasi]

    daftar_status = ['Semua'] + sorted(df['STATUS'].dropna().unique().tolist())
    status = st.sidebar.selectbox("📌 Pilih Status WP", daftar_status)
    if status != "Semua":
        df = df[df["STATUS"] == status]

    st.success("✅ Data berhasil diproses dan difilter!")

    # -------------------- DATA OUTPUT -------------------- #
    st.markdown("### 📄 Contoh Tabel Data")
    st.dataframe(df.head(10), use_container_width=True)

    # -------------------- VISUALISASI -------------------- #
    st.markdown("### 📈 Visualisasi Data")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 Pie Chart: Kepatuhan WP**")
        pie_data = df["Kepatuhan"].value_counts()
        st.plotly_chart({
            "data": [{
                "values": pie_data.values,
                "labels": pie_data.index,
                "type": "pie",
                "marker": {"colors": ["#A8D5BA", "#FFD6A5", "#FFAAA5"]}
            }],
            "layout": {"margin": {"l": 10, "r": 10, "t": 10, "b": 10}}
        })

    with col2:
        st.markdown("**📈 Tren Pembayaran Bulanan**")
        if len(kolom_bulan) > 0:
            tren = df[kolom_bulan].sum().reset_index()
            tren.columns = ["Bulan", "Total"]
            tren["Bulan"] = pd.to_datetime(tren["Bulan"]).dt.strftime('%b')
            st.line_chart(tren.set_index("Bulan"))

    # -------------------- TOP WP -------------------- #
    st.markdown("### 🏆 Top 5 WP dengan Pembayaran Tertinggi")
    top_wp = df[["NAMA OP", "UPPPD", "Total Pembayaran", "Kepatuhan"]].copy()
    top_wp["Total Pembayaran"] = top_wp["Total Pembayaran"].apply(lambda x: f"Rp {x:,.2f}")
    st.dataframe(top_wp.sort_values(by="Total Pembayaran", ascending=False).head(5), use_container_width=True)
