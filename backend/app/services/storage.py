"""
Local file storage for uploaded resumes (spec section 9; STORAGE_BACKEND=local
today, swappable for S3 later per .env.example's STORAGE_BACKEND).
"""
import uuid
from pathlib import Path

from app.core.config import settings


def get_storage_root() -> Path:
    root = Path(settings.STORAGE_URL)
    root.mkdir(parents=True, exist_ok=True)
    return root


def resume_storage_path(user_id: uuid.UUID, resume_id: uuid.UUID, extension: str) -> Path:
    directory = get_storage_root() / "resumes" / str(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{resume_id}.{extension.lstrip('.')}"


def delete_file(path: str) -> None:
    file_path = Path(path)
    if file_path.exists():
        file_path.unlink()
