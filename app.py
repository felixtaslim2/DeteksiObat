from PIL import Image
import streamlit as st

from services.database import ensure_list, load_database
from services.detector import detect, load_model
from services.tts import generate_tts

# 1. Page Configuration
st.set_page_config(
    page_title="Deteksi Obat Lansia",
    layout="centered",
)

CONFIDENCE_THRESHOLD = 0.85

# 2. Minimal CSS overrides for elderly accessibility (large fonts & large buttons)
st.markdown(
    """
    <style>
    html, body, p, span, li, label {
        font-size: 20px !important;
    }
    div.stButton > button {
        width: 100% !important;
        height: 60px !important;
        font-size: 22px !important;
        font-weight: bold !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def display_dosage(aturan: dict) -> None:
    """Display Cara Minum information in a structured container."""
    with st.container(border=True):
        st.markdown("### 🥄 Cara Minum")

        legacy = aturan.get("legacy_text", "")
        waktu = aturan.get("waktu", "")
        petunjuk = aturan.get("petunjuk", "")
        dosis = aturan.get("dosis", [])

        if legacy and not waktu and not petunjuk and not dosis:
            st.write(legacy)
            return

        if waktu:
            st.info(f"**⏰ Waktu Minum:** {waktu}")

        if dosis:
            st.markdown("**📋 Dosis Pemakaian:**")
            for d in dosis:
                if isinstance(d, dict):
                    st.write(f"- **Untuk:** {d.get('kelompok', '-')}")
                    st.write(
                        f"  - Dosis: {d.get('jumlah', '-')} ({d.get('frekuensi', '-')})"
                    )

        if petunjuk:
            st.markdown(f"**💡 Petunjuk Tambahan:** {petunjuk}")


def display_medicine_info(med_info: dict) -> None:
    """Display medicine details using native Streamlit layout components."""
    # 4. Compact General Information Card
    with st.container(border=True):
        st.markdown("### 💊 Informasi Umum")
        st.write(f"**Nama Obat:** {med_info.get('nama', '-')}")
        st.write(f"**Bahan Aktif:** {med_info.get('bahan_aktif', '-')}")
        st.write(f"**Golongan:** {med_info.get('golongan', '-')}")
        st.write(f"**Kategori:** {med_info.get('kategori', '-')}")

    # 5. Two-column row: Manfaat & Siapa yang dapat menggunakan
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("### 💊 Manfaat")
            st.write(med_info["ringkasan_layar"].get("manfaat", "-"))
    with col2:
        with st.container(border=True):
            st.markdown("### 👤 Sasaran Pengguna")
            st.write(med_info["ringkasan_layar"].get("siapa", "-"))

    # 6. Full-width Cara Minum card
    display_dosage(med_info["ringkasan_layar"].get("aturan_minum", {}))

    # 7. Two-column row: Efek Samping & Perhatian
    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.markdown("### ⚠️ Efek Samping")
            efek = ensure_list(
                med_info["ringkasan_layar"].get("efek_samping_utama", [])
            )
            if efek:
                for item in efek:
                    st.markdown(f"- {item}")
            else:
                st.write("Informasi tidak tersedia.")
    with col4:
        with st.container(border=True):
            st.markdown("### 🚨 Perhatian Penting")
            pantangan = ensure_list(
                med_info["ringkasan_layar"].get("pantangan_penting", [])
            )
            if pantangan:
                for item in pantangan:
                    st.warning(item)
            else:
                st.write("Informasi tidak tersedia.")


def main() -> None:
    db = load_database()
    model = load_model()

    if not db:
        st.error("⚠️ Basis data obat tidak ditemukan atau rusak.")
        return
    if model is None:
        st.error("⚠️ Model deteksi tidak ditemukan atau rusak.")
        return

    st.title("Identifikasi Obat")
    st.write("Ambil foto atau unggah gambar obat untuk melihat informasi pemakaian.")

    input_method = st.radio(
        "Pilih Cara Memasukkan Gambar:",
        ("📸 Kamera", "📷 Unggah Gambar"),
        horizontal=True,
    )

    uploaded_image = None
    if "📸 Kamera" in input_method:
        uploaded_image = st.camera_input("Silakan hadapkan kamera ke obat Anda")
    else:
        uploaded_image = st.file_uploader(
            "Pilih file gambar obat (JPG, JPEG, PNG):",
            type=["jpg", "jpeg", "png"],
        )

    if uploaded_image is None:
        return

    if uploaded_image.size == 0:
        st.error("Gambar tidak boleh kosong. Harap unggah gambar yang valid.")
        return

    try:
        valid_image = Image.open(uploaded_image)
        img_format = valid_image.format.lower() if valid_image.format else ""
        if img_format not in ["jpeg", "jpg", "png"]:
            st.error(
                "Format gambar tidak didukung. Harap gunakan format JPG, JPEG, atau PNG."
            )
            return
    except Exception:
        st.error("Gagal membaca file gambar. Pastikan file tidak rusak.")
        return

    # Cache YOLO detection results in session state
    image_id = f"{getattr(uploaded_image, 'name', 'camera')}_{uploaded_image.size}"
    if st.session_state.get("last_image_id") != image_id:
        st.session_state.last_image_id = image_id
        with st.spinner("Sedang mengenali obat..."):
            st.session_state.detection_result = detect(valid_image)

    detection_result = st.session_state.detection_result
    if detection_result is None:
        st.warning(
            "⚠️ Obat tidak terdeteksi. Silakan coba ambil foto dari jarak dekat."
        )
        return

    st.divider()
    st.image(
        detection_result["annotated_image"],
        caption="Hasil Deteksi",
        use_container_width=True,
    )

    confidence = detection_result["confidence"]
    if confidence < CONFIDENCE_THRESHOLD:
        st.warning(
            f"⚠️ Obat tidak dapat dikenali dengan cukup yakin.\n\n"
            f"Akurasi deteksi hanya {int(confidence * 100)}%.\n\n"
            f"Silakan ambil foto ulang dengan pencahayaan yang lebih baik atau posisi obat lebih jelas."
        )
        return

    med_id = detection_result["id"]
    med_info = db.get(med_id)
    if not med_info:
        st.warning("⚠️ Informasi detail obat tidak ditemukan di basis data.")
        return

    st.success(
        f"### 🎯 Hasil Deteksi: {med_info['nama']} (Akurasi: {int(confidence * 100)}%)"
    )

    if st.button("🔊 Dengarkan Informasi"):
        with st.spinner("Sedang menyiapkan suara..."):
            audio_path = generate_tts(med_info["teks_suara_tts"])
        if audio_path:
            st.audio(audio_path, format="audio/mp3", autoplay=True)
        else:
            st.error("⚠️ Gagal memutar suara. Pastikan koneksi internet aktif.")

    display_medicine_info(med_info)


if __name__ == "__main__":
    main()
