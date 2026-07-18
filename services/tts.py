import asyncio
import hashlib
from pathlib import Path
from typing import Optional

import edge_tts


def generate_tts(text: str) -> Optional[str]:
    """Generate TTS audio using edge-tts and save to a temp MP3 file."""
    try:
        temp_dir = Path("temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        text_hash = hashlib.md5(
            f"{text}_id-ID-GadisNeural".encode("utf-8")
        ).hexdigest()
        file_path = temp_dir / f"tts_{text_hash}.mp3"

        # Reuse existing audio file if it exists
        if file_path.exists():
            return str(file_path)

        communicate = edge_tts.Communicate(text, "id-ID-GadisNeural")
        asyncio.run(communicate.save(str(file_path)))

        if file_path.exists() and file_path.stat().st_size > 0:
            return str(file_path)
    except Exception:
        pass
    return None
