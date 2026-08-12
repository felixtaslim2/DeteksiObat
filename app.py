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

CONFIDENCE_THRESHOLD = 0.9

# 2. Minimal CSS overrides for elderly accessibility and medical color styling
st.markdown(
    """
    <style>
    html, body, p, span, li, label {
        font-size: 20px !important;
        line-height: 1.5 !important;
        color: var(--text-color);
    }
    div.stButton > button {
        width: 100% !important;
        height: 60px !important;
        font-size: 22px !important;
        font-weight: bold !important;
    }
    .app-header {
        background: linear-gradient(135deg, #2F80ED, #0056b3);
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid #2F80ED;
    }
    .app-header-title {
        font-size: 32px !important;
        font-weight: bold !important;
        color: #ffffff !important;
        margin-bottom: 8px;
    }
    .app-header-subtitle {
        font-size: 18px !important;
        color: #e0e8f5 !important;
    }
    .card-blue {
        background-color: #EAF3FF;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #D9DEE7;
        margin-bottom: 12px;
    }
    .card-green {
        background-color: #E8F5E9;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #c8e6c9;
        margin-bottom: 12px;
    }
    .card-yellow {
        background-color: #FFFDE7;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #fff59d;
        margin-bottom: 12px;
    }
    .card-red {
        background-color: #FFEBEE;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #ffcdd2;
        margin-bottom: 12px;
    }
    .card-title {
        font-size: 26px !important;
        font-weight: 700 !important;
        margin-bottom: 12px;
        color: var(--text-color);
    }
    .section-title {
        font-size: 34px !important;
        font-weight: 800 !important;
        line-height: 1.2 !important;
        margin-top: 10px !important;
        margin-bottom: 18px !important;
        color: var(--text-color);
    }
    .detected-medicine-name {
        font-size: 30px !important;
        font-weight: 800 !important;
        line-height: 1.2 !important;
        margin-bottom: 6px !important;
        color: #27AE60 !important;
    }
    @media (max-width: 600px) {
        .section-title {
            font-size: 28px !important;
        }
        .detected-medicine-name {
            font-size: 26px !important;
        }
        .card-title {
            font-size: 24px !important;
        }
    }
    @media (prefers-color-scheme: dark) {
        .card-blue {
            background-color: #1e293b;
            border-color: #334155;
            color: #F8FAFC !important;
        }
        .card-blue p, .card-blue span, .card-blue li, .card-blue label, .card-blue b, .card-blue div {
            color: #F8FAFC !important;
        }
        .card-blue .card-title {
            color: #FFFFFF !important;
        }
        .card-green {
            background-color: #064e3b;
            border-color: #047857;
            color: #F8FAFC !important;
        }
        .card-green p, .card-green span, .card-green li, .card-green label, .card-green b, .card-green div {
            color: #F8FAFC !important;
        }
        .card-green .card-title {
            color: #FFFFFF !important;
        }
        .card-yellow {
            background-color: #78350f;
            border-color: #b45309;
            color: #F8FAFC !important;
        }
        .card-yellow p, .card-yellow span, .card-yellow li, .card-yellow label, .card-yellow b, .card-yellow div {
            color: #F8FAFC !important;
        }
        .card-yellow .card-title {
            color: #FFFFFF !important;
        }
        .card-red {
            background-color: #7f1d1d;
            border-color: #b91c1c;
            color: #F8FAFC !important;
        }
        .card-red p, .card-red span, .card-red li, .card-red label, .card-red b, .card-red div {
            color: #F8FAFC !important;
        }
        .card-red .card-title {
            color: #FFFFFF !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def display_dosage(aturan: dict) -> None:
    """Display Cara Minum information in a structured container."""
    legacy = aturan.get("legacy_text", "")
    waktu = aturan.get("waktu", "")
    petunjuk = aturan.get("petunjuk", "")
    dosis = aturan.get("dosis", [])

    if legacy and not waktu and not petunjuk and not dosis:
        st.markdown(
            f"""
            <div class="card-blue">
                <div class="card-title">Cara Minum</div>
                <p>{legacy}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    content_html = ""
    if waktu:
        content_html += f"<div style='background-color: var(--background-color); border-left: 4px solid #2F80ED; padding: 10px; margin-bottom: 10px;'><b>Waktu Minum:</b> {waktu}</div>"

    if dosis:
        content_html += "<p><b>Dosis Pemakaian:</b></p><ul>"
        for d in dosis:
            if isinstance(d, dict):
                content_html += f"<li><b>Untuk:</b> {d.get('kelompok', '-')}<ul><li>Dosis: {d.get('jumlah', '-')} ({d.get('frekuensi', '-')})</li></ul></li>"
        content_html += "</ul>"

    if petunjuk:
        content_html += f"<p><b>Petunjuk Tambahan:</b> {petunjuk}</p>"

    st.markdown(
        f"""
        <div class="card-blue">
            <div class="card-title">Cara Minum</div>
            {content_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def display_medicine_info(med_info: dict) -> None:
    """Display medicine details using native Streamlit layout components."""
    # 4. Compact General Information Card
    st.markdown(
        f"""
        <div class="card-blue">
            <div class="card-title">Informasi Umum</div>
            <p><b>Bahan Aktif</b><br>{med_info.get('bahan_aktif', '-')}</p>
            <p><b>Golongan</b><br>{med_info.get('golongan', '-')}</p>
            <p><b>Kategori</b><br>{med_info.get('kategori', '-')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 5. Two-column row: Manfaat & Siapa yang dapat menggunakan
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div class="card-green">
                <div class="card-title">Manfaat</div>
                <p>{med_info["ringkasan_layar"].get("manfaat", "-")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="card-blue">
                <div class="card-title">Siapa yang dapat menggunakan</div>
                <p>{med_info["ringkasan_layar"].get("siapa", "-")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 6. Full-width Cara Minum card
    display_dosage(med_info["ringkasan_layar"].get("aturan_minum", {}))

    # 7. Two-column row: Efek Samping & Perhatian
    col3, col4 = st.columns(2)
    with col3:
        efek = ensure_list(
            med_info["ringkasan_layar"].get("efek_samping_utama", [])
        )
        if efek:
            efek_html = "<ul>" + "".join([f"<li>{item}</li>" for item in efek]) + "</ul>"
        else:
            efek_html = "<p>Informasi tidak tersedia.</p>"
        st.markdown(
            f"""
            <div class="card-yellow">
                <div class="card-title">Efek Samping</div>
                {efek_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col4:
        pantangan = ensure_list(
            med_info["ringkasan_layar"].get("pantangan_penting", [])
        )
        if pantangan:
            pantangan_html = "".join([f"<div style='background-color: var(--background-color); border-left: 4px solid #D9534F; padding: 10px; margin-bottom: 10px; color:#D9534F;'>{item}</div>" for item in pantangan])
        else:
            pantangan_html = "<p>Informasi tidak tersedia.</p>"
        st.markdown(
            f"""
            <div class="card-red">
                <div class="card-title">⚠️ Perhatian</div>
                {pantangan_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    db = load_database()
    model = load_model()

    if not db:
        st.error("Basis data obat tidak ditemukan atau rusak.")
        return
    if model is None:
        st.error("Model deteksi tidak ditemukan atau rusak.")
        return

    st.markdown(
        """
        <div class="app-header">
            <div class="app-header-title">💊 MediScan</div>
            <div class="app-header-subtitle">Kenali obat dan lihat informasi penggunaannya dengan mudah.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Input Gambar")
    input_method = st.radio(
        "Pilih Cara Memasukkan Gambar:",
        ("Kamera", "Unggah Gambar"),
        horizontal=True,
    )

    uploaded_image = None
    if "Kamera" in input_method:
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
            "Obat tidak terdeteksi. Silakan coba ambil foto dari jarak dekat."
        )
        return

    st.divider()
    st.markdown('<div class="section-title">Hasil Deteksi</div>', unsafe_allow_html=True)
    left_col, center_col, right_col = st.columns([1, 4, 1])
    with center_col:
        st.image(
            detection_result["annotated_image"],
            use_container_width=True,
        )

    confidence = detection_result["confidence"]
    if confidence < CONFIDENCE_THRESHOLD:
        st.warning(
            f"Obat tidak dapat dikenali dengan cukup yakin.\n\n"
            f"Akurasi deteksi hanya {int(confidence * 100)}%.\n\n"
            f"Silakan ambil foto ulang dengan pencahayaan yang lebih baik atau posisi obat lebih jelas."
        )
        return

    med_id = detection_result["id"]
    med_info = db.get(med_id)
    if not med_info:
        st.warning("Informasi detail obat tidak ditemukan di basis data.")
        return

    st.markdown(
        f'<div class="detected-medicine-name">{med_info["nama"]}</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Akurasi deteksi: {int(confidence * 100)}%")

    if st.button("Dengarkan Informasi"):
        with st.spinner("Sedang menyiapkan suara..."):
            audio_path = generate_tts(med_info["teks_suara_tts"])
        if audio_path:
            st.audio(audio_path, format="audio/mp3", autoplay=True)
        else:
            st.error("Gagal memutar suara. Pastikan koneksi internet aktif.")

    st.divider()
    st.markdown('<div class="section-title">Informasi Obat</div>', unsafe_allow_html=True)
    display_medicine_info(med_info)


if __name__ == "__main__":
    main()
