from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image
import streamlit as st
from ultralytics import YOLO


@st.cache_resource
def load_model() -> Optional[YOLO]:
    """Load YOLO model once and cache the resource."""
    try:
        model_path = Path("model/best.pt")
        if model_path.exists():
            return YOLO(model_path)
    except Exception:
        pass
    return None


def detect(image: Any) -> Optional[Dict[str, Any]]:
    """Detect medicine and return the result with highest confidence."""
    model = load_model()
    if not model:
        return None

    try:
        results = model(image)
        if not results or len(results[0].boxes) == 0:
            return None

        result = results[0]
        # Get index of the best box based on highest confidence
        best_idx = int(result.boxes.conf.argmax())
        best_box = result.boxes[best_idx]

        # Generate annotated image
        annotated_image = Image.fromarray(result[best_idx].plot()[..., ::-1])

        return {
            "id": model.names[int(best_box.cls[0])],
            "confidence": float(best_box.conf[0]),
            "annotated_image": annotated_image,
        }
    except Exception:
        return None
