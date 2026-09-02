import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os

# =========================================================
# KONFIGURASI
# =========================================================

SHEET_URL = "https://docs.google.com/spreadsheets/d/1nljtizJIgcB1OPrag8XdaNDM-SAYiagnbLvvVRLSnYM/edit?usp=sharing"

DATA_FILE = "data_siswa.xlsx"
LOGO_FILE = "logo_sekolah.png"

FORM_TERBUKA = True

st.set_page_config(
    page_title="Verifikasi Data TKA",
    layout="centered"
)

# =========================================================
# TAMPILAN
# =========================================================

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

div.stButton > button:first-child:hover {
    background-color: #008fb3;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# KONEKSI GOOGLE SHEETS
# Google Sheets hanya digunakan untuk menyimpan HASIL
# VERIFIKASI, bukan sebagai sumber data siswa.
# =========================================================

conn = st.connection(
    "gsheets",
    type=GSheetsConnection
)

# =========================================================
# FUNGSI MEMBACA DATA SISWA DARI EXCEL GITHUB
# =========================================================

@st.cache_data
def muat_data_siswa():
    if not os.path.exists(DATA_FILE):
        st.error(
            f"File {DATA_FILE} tidak ditemukan di repository."
        )
        st.stop()

    df = pd.read_excel(DATA_FILE, dtype=str)

    # Membersihkan nama kolom
    df.columns = [
        str(c).strip().lower().replace(" ", "_")
        for c in df.columns
    ]

    # Membersihkan isi data
    for col in df.columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

    # Normalisasi tanggal lahir
    if "tgl_lahir" in df.columns:
        tanggal = pd.to_datetime(
            df["tgl_lahir"],
            errors="coerce"
        )

        df["tgl_lahir"] = tanggal.dt.strftime("%Y-%m-%d")
        df["tgl_lahir"] = df["tgl_lahir"].fillna("")

    return df


# =========================================================
# FUNGSI MEMBACA HASIL VERIFIKASI DARI GOOGLE SHEETS
# =========================================================

def muat_hasil_verifikasi():
    try:
        df = conn.read(
            spreadsheet=SHEET_URL,
            dtype=str
        )

        if df is None or df.empty:
            return pd.DataFrame()

        df.columns = [
            str(c).strip().lower().replace(" ", "_")
            for c in df.columns
        ]

        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

        return df

    except Exception:
        # Jika GSheet belum memiliki data, anggap kosong.
        return pd.DataFrame()


# =========================================================
# FUNGSI MENGGABUNGKAN DATA MASTER + HASIL VERIFIKASI
# =========================================================

def muat_data_lengkap():
    df_master = muat_data_siswa().copy()

    df_hasil = muat_hasil_verifikasi()

    # Jika belum ada hasil verifikasi,
    # tambahkan kolom hasil yang masih kosong.
    kolom_hasil = [
        "status",
        "catatan_perbaikan",
        "waktu_akses"
    ]

    for col in kolom_hasil:
        if col not in df_master.columns:
            df_master[col] = ""

    if df_hasil.empty or "nis" not in df_hasil.columns:
        return df_master

    # Ambil hanya kolom hasil dari Google Sheets
    kolom_merge = ["nis"]

    for col in kolom_hasil:
        if col in df_hasil.columns:
            kolom_merge.append(col)

    hasil = df_hasil[kolom_merge].copy()

    # Hindari duplikasi NIS
    hasil = hasil.drop_duplicates(
        subset=["nis"],
        keep="last"
    )

    # Hapus kolom hasil dari master sebelum merge
    for col in kolom_hasil:
        if col in df_master.columns:
            df_master.drop(
                columns=[col],
                inplace=True
            )

    # Gabungkan master dengan hasil verifikasi
    df_master = df_master.merge(
        hasil,
        on="nis",
        how="left"
    )

    for col in kolom_hasil:
        if col not in df_master.columns:
            df_master[col] = ""
        else:
            df_master[col] = (
                df_master[col]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    return df_master


# =========================================================
# HEADER
# =========================================================

col_logo, col_judul = st.columns([1, 5])

with col_logo:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=85)

with col_judul:
    st.markdown("""
        <div style='line-height: 1.2;'>
            <h3 style='margin-bottom: 0;'>
                VERIFIKASI DATA TKA 2026
            </h3>
            <p style='font-size: 18px; margin-top: 0;'>
                SMA KARTIKA XIX-1 BANDUNG
            </p>
        </div>
    """, unsafe_allow_html=True)

st.divider()


# =========================================================
# FORM DITUTUP
# =========================================================

if not FORM_TERBUKA:

    st.error("### PEMBERITAHUAN: VERIFIKASI DITUTUP")

    st.write(
        "Masa pengecekan data TKA 2025 telah berakhir, "
        "hubungi operator sekolah jika masih ada data "
        "yang salah. Terima kasih."
    )

    with st.expander("Panel Admin"):

        pw = st.text_input(
            "Password Admin",
            type="password"
        )

        if pw == "admin123":

            st.write("### Rekapitulasi Akhir")

            df_admin = muat_data_lengkap()

            st.dataframe(
                df_admin,
                use_container_width=True
            )

            csv = df_admin.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "Download Rekap Akhir (CSV)",
                csv,
                "rekap_tka_final.csv",
                "text/csv"
            )

    st.stop()


# =========================================================
# LOGIN SISWA
# =========================================================

with st.sidebar:

    st.header("Login Siswa")

    input_nis = st.text_input(
        "Masukkan NIS"
    ).strip()

    input_tgl = st.text_input(
        "Tanggal Lahir (YYYY-MM-DD)",
        placeholder="Contoh: 2008-05-10"
    ).strip()


# =========================================================
# VERIFIKASI SISWA
# =========================================================

if input_nis and input_tgl:

    df_siswa = muat_data_siswa()

    # Normalisasi input tanggal
    try:
        tanggal_input = pd.to_datetime(
            input_tgl,
            errors="raise"
        ).strftime("%Y-%m-%d")
    except Exception:
        st.error(
            "Format tanggal tidak valid. "
            "Gunakan format YYYY-MM-DD."
        )
        st.stop()

    # Cari siswa dari EXCEL
    siswa = df_siswa[
        (df_siswa["nis"].astype(str) == str(input_nis))
        &
        (df_siswa["tgl_lahir"].astype(str) == tanggal_input)
    ]

    if not siswa.empty:

        idx = siswa.index[0]

        st.success(
            f"Data ditemukan: {siswa.at[idx, 'nama']}"
        )

        # -------------------------------------------------
        # Ambil hasil verifikasi sebelumnya dari GSheet
        # -------------------------------------------------

        df_hasil = muat_hasil_verifikasi()

        status_skrg = ""
        catatan_lama = ""
        waktu_lama = ""

        if not df_hasil.empty and "nis" in df_hasil.columns:

            hasil_siswa = df_hasil[
                df_hasil["nis"].astype(str)
                == str(input_nis)
            ]

            if not hasil_siswa.empty:

                idx_hasil = hasil_siswa.index[-1]

                if "status" in hasil_siswa.columns:
                    status_skrg = str(
                        hasil_siswa.at[
                            idx_hasil,
                            "status"
                        ]
                    ).strip()

                if "catatan_perbaikan" in hasil_siswa.columns:
                    catatan_lama = str(
                        hasil_siswa.at[
                            idx_hasil,
                            "catatan_perbaikan"
                        ]
                    ).strip()

                if "waktu_akses" in hasil_siswa.columns:
                    waktu_lama = str(
                        hasil_siswa.at[
                            idx_hasil,
                            "waktu_akses"
                        ]
                    ).strip()

        # -------------------------------------------------
        # Tampilan data siswa
        # -------------------------------------------------

        col1, col2 = st.columns(2)

        with col1:

            st.text_input(
                "Nama Lengkap",
                value=str(
                    siswa.at[idx, "nama"]
                ),
                disabled=True
            )

            st.text_input(
                "Tempat Lahir",
                value=str(
                    siswa.at[idx, "tempat_lahir"]
                ),
                disabled=True
            )

            st.text_input(
                "Nama Ayah",
                value=str(
                    siswa.at[idx, "nama_ayah"]
                ),
                disabled=True
            )

        with col2:

            st.text_input(
                "Kelas",
                value=str(
                    siswa.at[idx, "kelas"]
                ),
                disabled=True
            )

            st.text_input(
                "Tanggal Lahir",
                value=str(
                    siswa.at[idx, "tgl_lahir"]
                ),
                disabled=True
            )

        # -------------------------------------------------
        # Status
        # -------------------------------------------------

        if status_skrg:

            waktu_info = (
                f" | Diakses: {waktu_lama}"
                if waktu_lama
                else ""
            )

            st.write(
                f"Status: **{status_skrg}**"
                f"{waktu_info}"
            )

        else:

            st.write(
                "Status: **Belum Verifikasi**"
            )

        # -------------------------------------------------
        # Catatan Perbaikan
        # -------------------------------------------------

        with st.expander(
            "Klik di sini jika ada kesalahan data"
        ):

            st.write(
                "Tuliskan detail perbaikan "
                "(Nama/TTL/Ayah/Kelas):"
            )

            perbaikan_val = st.text_area(
                "Detail Perbaikan:",
                value=catatan_lama
            )

        # -------------------------------------------------
        # SIMPAN
        # -------------------------------------------------

        if st.button("SIMPAN KONFIRMASI"):

            # Ambil hasil verifikasi yang sudah ada
            df_hasil = muat_hasil_verifikasi()

            # Jika GSheet belum memiliki struktur,
            # buat berdasarkan data master.
            if df_hasil.empty:

                df_hasil = pd.DataFrame(
                    columns=[
                        "nis",
                        "nama",
                        "kelas",
                        "nama_ayah",
                        "tempat_lahir",
                        "tgl_lahir",
                        "status",
                        "catatan_perbaikan",
                        "waktu_akses"
                    ]
                )

            # Pastikan semua kolom tersedia
            kolom_wajib = [
                "nis",
                "nama",
                "kelas",
                "nama_ayah",
                "tempat_lahir",
                "tgl_lahir",
                "status",
                "catatan_perbaikan",
                "waktu_akses"
            ]

            for col in kolom_wajib:
                if col not in df_hasil.columns:
                    df_hasil[col] = ""

            # Cari NIS di hasil verifikasi
            posisi = df_hasil.index[
                df_hasil["nis"].astype(str)
                == str(input_nis)
            ].tolist()

            # Data yang akan disimpan
            data_baru = {
                "nis": str(input_nis),
                "nama": str(
                    siswa.at[idx, "nama"]
                ),
                "kelas": str(
                    siswa.at[idx, "kelas"]
                ),
                "nama_ayah": str(
                    siswa.at[idx, "nama_ayah"]
                ),
                "tempat_lahir": str(
                    siswa.at[idx, "tempat_lahir"]
                ),
                "tgl_lahir": str(
                    siswa.at[idx, "tgl_lahir"]
                ),
                "status": (
                    "Perlu Perbaikan"
                    if perbaikan_val.strip()
                    else "Data Sudah Benar"
                ),
                "catatan_perbaikan": (
                    perbaikan_val.strip()
                ),
                "waktu_akses": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            }

            # Update data yang sudah ada
            if posisi:

                idx_update = posisi[-1]

                for col in kolom_wajib:
                    df_hasil.at[
                        idx_update,
                        col
                    ] = data_baru[col]

            # Jika belum ada, tambahkan baris baru
            else:

                df_hasil = pd.concat(
                    [
                        df_hasil,
                        pd.DataFrame([data_baru])
                    ],
                    ignore_index=True
                )

            # Pastikan hanya kolom yang diperlukan
            df_hasil = df_hasil[kolom_wajib]

            # -------------------------------------------------
            # SIMPAN KE GOOGLE SHEETS
            # -------------------------------------------------

            conn.update(
                spreadsheet=SHEET_URL,
                data=df_hasil
            )

            # Bersihkan cache supaya pembacaan berikutnya
            # mengambil hasil terbaru
            st.cache_data.clear()

            st.success(
                "Berhasil disimpan! "
                "Anda bisa menutup halaman ini."
            )

            st.info(
                "Hasil verifikasi telah dicatat."
            )

    else:

        st.error(
            "Data tidak ditemukan. "
            "Cek NIS & format tanggal "
            "(YYYY-MM-DD)."
        )


# =========================================================
# PANEL ADMIN
# =========================================================

st.write("")

with st.expander("Panel Admin"):

    pw = st.text_input(
        "Password Admin",
        type="password",
        key="pw_bawah"
    )

    if pw == "admin123":

        st.success("Login admin berhasil.")

        df_admin = muat_data_lengkap()

        st.write(
            f"Jumlah data siswa: **{len(df_admin)}**"
        )

        st.dataframe(
            df_admin,
            use_container_width=True
        )

        csv = df_admin.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "Download Rekap Verifikasi (CSV)",
            csv,
            "rekap_verifikasi_tka.csv",
            "text/csv"
        )
