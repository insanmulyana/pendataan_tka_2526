import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os

#KONFIGURASI
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Vr8LdlC2COe-zqPKFyrtqMvGFUF3XbjhaOlfkGO-oz0/edit?usp=sharing"
LOGO_FILE = "logo_sekolah.png"

FORM_TERBUKA = False  # Ubah ke True untuk buka kembali

st.set_page_config(page_title="Verifikasi Data TKA", layout="centered")

st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #28a745; 
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 2rem;
        font-weight: bold;
        transition: 0.3s;
        width: 100%;
    }
    div.stButton > button:first-child:hover { background-color: #008fb3; color: white; }
    </style>
    """, unsafe_allow_html=True)

#KONEKSI_DATA
conn = st.connection("gsheets", type=GSheetsConnection)

def muat_data_bersih():
    st.cache_data.clear()
    df = conn.read(spreadsheet=SHEET_URL, dtype=str)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    return df
    
col_logo, col_judul = st.columns([1, 5])
with col_logo:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=85)
with col_judul:
    st.markdown("""
        <div style='line-height: 1.2;'>
            <h3 style='margin-bottom: 0;'>VERIFIKASI DATA TKA 2025</h3>
            <p style='font-size: 18px; margin-top: 0;'>SMA KARTIKA XIX-1 BANDUNG</p>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# --- 5. LOGIKA PENUTUPAN LINK ---
if not FORM_TERBUKA:
    st.error("### PEMBERITAHUAN: VERIFIKASI DITUTUP")
    st.write("Masa pengecekan data TKA 2025 telah berakhir, hubungi operator sekolah jika masih ada data yang salah. Terima kasih.")
    
    # Panel Admin tetap bisa dibuka meski form ditutup (untuk download hasil akhir)
    with st.expander("Panel Admin"):
        pw = st.text_input("Password Admin", type="password")
        if pw == "admin123":
            st.write("### Rekapitulasi Akhir")
            df_admin = muat_data_bersih()
            st.dataframe(df_admin)
            csv = df_admin.to_csv(index=False).encode('utf-8')
            st.download_button("Download Rekap Akhir (CSV)", csv, "rekap_tka_final.csv", "text/csv")
    st.stop() # Menghentikan proses kode di bawahnya agar form login tidak muncul

#LOGIN_SISWA
with st.sidebar:
    st.header("Login Siswa")
    input_nis = st.text_input("Masukkan NIS").strip()
    input_tgl = st.text_input("Tanggal Lahir (YYYY-MM-DD)", placeholder="Contoh: 2008-05-10").strip()

#VERIFIKASI
if input_nis and input_tgl:
    df_siswa = muat_data_bersih()
    
    siswa = df_siswa[
        (df_siswa['nis'].astype(str) == str(input_nis)) & 
        (df_siswa['tgl_lahir'].astype(str) == str(input_tgl))
    ]

    if not siswa.empty:
        idx = siswa.index[0]
        st.success(f"Data ditemukan: {siswa.at[idx, 'nama']}")
        
        def val(k): return str(siswa.at[idx, k]) if k in siswa.columns and pd.notna(siswa.at[idx, k]) else ""

        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Nama Lengkap", value=val('nama'), disabled=True)
            st.text_input("Tempat Lahir", value=val('tempat_lahir'), disabled=True)
            st.text_input("Nama Ayah", value=val('nama_ayah'), disabled=True)
        with col2:
            st.text_input("Kelas", value=val('kelas'), disabled=True)
            st.text_input("Tanggal Lahir", value=val('tgl_lahir'), disabled=True)
        
        status_skrg = val('status')
        waktu_val = val('waktu_akses')
        waktu_info = f" | Diakses: {waktu_val}" if waktu_val else ""
        st.write(f"Status: **{status_skrg if status_skrg else 'Belum Verifikasi'}**{waktu_info}")

        with st.expander("Klik di sini jika ada kesalahan data"):
            st.write("Tuliskan detail perbaikan (Nama/TTL/Ayah/Kelas):")
            perbaikan_val = st.text_area("Detail Perbaikan:", value=val('catatan_perbaikan'))
        
        if st.button("SIMPAN KONFIRMASI"):
            df_final = muat_data_bersih()
            idx_f = df_final[df_final['nis'].astype(str) == str(input_nis)].index[0]
            
            if perbaikan_val.strip():
                df_final.at[idx_f, 'status'] = 'Perlu Perbaikan'
                df_final.at[idx_f, 'catatan_perbaikan'] = perbaikan_val
            else:
                df_final.at[idx_f, 'status'] = 'Data Sudah Benar'
                df_final.at[idx_f, 'catatan_perbaikan'] = ""
            
            df_final.at[idx_f, 'waktu_akses'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.update(spreadsheet=SHEET_URL, data=df_final)
            st.success("Berhasil disimpan! Anda bisa menutup halaman ini.")
    else:
        st.error("Data tidak ditemukan. Cek NIS & format tanggal (YYYY-MM-DD).")

#PANEL ADMIN
st.write("")
with st.expander("Panel Admin"):
    pw = st.text_input("Password Admin", type="password", key="pw_bawah")
    if pw == "admin123":
        df_admin = muat_data_bersih()
        st.dataframe(df_admin)

