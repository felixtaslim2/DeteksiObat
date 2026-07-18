import json
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st


def ensure_list(value: Any) -> List[str]:
    """Helper to convert string or list into a clean list of strings."""
    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if item is not None and str(item).strip()
        ]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


@st.cache_data
def load_database() -> Dict[str, Dict[str, Any]]:
    """Loads drug data from data/medicines.json and returns a dictionary keyed by ID."""
    try:
        path = Path("data/medicines.json")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Root JSON must be a list")

        normalized = {}
        for item in data:
            if isinstance(item, dict) and "id" in item:
                med_id = item["id"]
                ringkasan = item.get("ringkasan_layar", {})

                # Normalize aturan_minum structure safely
                aturan = ringkasan.get("aturan_minum", {})
                if isinstance(aturan, str):
                    aturan_norm = {
                        "waktu": "",
                        "petunjuk": "",
                        "dosis": [],
                        "legacy_text": aturan.strip(),
                    }
                elif isinstance(aturan, dict):
                    aturan_norm = {
                        "waktu": str(aturan.get("waktu", "")).strip(),
                        "petunjuk": str(aturan.get("petunjuk", "")).strip(),
                        "dosis": aturan.get("dosis", []),
                        "legacy_text": "",
                    }
                else:
                    aturan_norm = {
                        "waktu": "",
                        "petunjuk": "",
                        "dosis": [],
                        "legacy_text": "",
                    }

                normalized[med_id] = {
                    "id": med_id,
                    "nama": str(item.get("nama", "")).strip(),
                    "bahan_aktif": str(item.get("bahan_aktif", "")).strip(),
                    "golongan": str(item.get("golongan", "")).strip(),
                    "kategori": str(item.get("kategori", "")).strip(),
                    "ringkasan_layar": {
                        "manfaat": str(ringkasan.get("manfaat", "")).strip(),
                        "siapa": str(ringkasan.get("siapa", "")).strip(),
                        "aturan_minum": aturan_norm,
                        "efek_samping_utama": ensure_list(
                            ringkasan.get("efek_samping_utama")
                        ),
                        "pantangan_penting": ensure_list(
                            ringkasan.get("pantangan_penting")
                        ),
                    },
                    "teks_suara_tts": str(item.get("teks_suara_tts", "")).strip(),
                }
        return normalized
    except Exception as e:
        st.error(f"Gagal memuat database obat: {e}")
        return {}
