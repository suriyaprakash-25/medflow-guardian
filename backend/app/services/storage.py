import logging
import os
import uuid
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, UploadFile
from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".txt", ".docx", ".doc"}


class StorageService:
    """Private medical-document storage adapter.

    Production never falls back to local disk. Local storage is retained only for
    non-production development/test environments with placeholder credentials and
    is guarded against traversal by strict MedFlow object-key validation.
    """

    def __init__(self):
        self.use_local = (
            not settings.SUPABASE_URL
            or not settings.SUPABASE_KEY
            or "placeholder" in settings.SUPABASE_KEY
        )
        if self.use_local:
            if getattr(settings, "ENV", "development") == "production":
                raise RuntimeError(
                    "Missing usable Supabase credentials in production; local medical-document storage is forbidden."
                )
            logger.warning(
                "Using local medical-document storage because Supabase credentials are placeholders."
            )
            self.local_dir = Path(os.getcwd(), "local_storage").resolve()
            self.local_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.supabase: Client = create_client(
                settings.SUPABASE_URL, settings.SUPABASE_KEY
            )
            self.bucket = settings.SUPABASE_BUCKET

    @staticmethod
    def _validate_storage_path(storage_path: str) -> str:
        """Validate a MedFlow-owned object key before any storage operation."""
        if not storage_path or "\\" in storage_path:
            raise HTTPException(status_code=400, detail="Invalid storage object key")

        path = PurePosixPath(storage_path)
        parts = path.parts
        if (
            path.is_absolute()
            or ".." in parts
            or len(parts) != 3
            or parts[0] != "patient"
            or not parts[1].isdigit()
            or not parts[2]
        ):
            raise HTTPException(status_code=400, detail="Invalid storage object key")
        return str(path)

    def _local_path(self, storage_path: str) -> Path:
        key = self._validate_storage_path(storage_path)
        candidate = (self.local_dir / Path(*PurePosixPath(key).parts)).resolve()
        try:
            candidate.relative_to(self.local_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid storage object key") from exc
        return candidate

    def upload_document(self, file: UploadFile, patient_id: int) -> str:
        """Upload a document and return its private internal object key."""
        filename = file.filename or ""
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid file extension")

        safe_filename = f"{uuid.uuid4().hex}{file_ext}"
        storage_path = self._validate_storage_path(
            f"patient/{int(patient_id)}/{safe_filename}"
        )

        file.file.seek(0)
        file_bytes = file.file.read()

        if self.use_local:
            local_path = self._local_path(storage_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(file_bytes)
            return storage_path

        try:
            self.supabase.storage.from_(self.bucket).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": file.content_type},
            )
            return storage_path
        except Exception as exc:
            logger.exception("Private storage upload failed")
            raise HTTPException(
                status_code=503,
                detail="Document storage is temporarily unavailable",
            ) from exc

    def download_document(self, storage_path: str) -> bytes:
        """Fetch file bytes from the private storage backend."""
        storage_path = self._validate_storage_path(storage_path)

        if self.use_local:
            local_path = self._local_path(storage_path)
            if not local_path.exists():
                raise HTTPException(
                    status_code=404, detail="Document object was not found"
                )
            return local_path.read_bytes()

        try:
            return self.supabase.storage.from_(self.bucket).download(storage_path)
        except Exception as exc:
            logger.exception("Private storage download failed")
            raise HTTPException(
                status_code=503,
                detail="Document storage is temporarily unavailable",
            ) from exc

    def delete_document(self, storage_path: str) -> None:
        """Best-effort compensating deletion for failed document transactions."""
        storage_path = self._validate_storage_path(storage_path)

        if self.use_local:
            local_path = self._local_path(storage_path)
            try:
                local_path.unlink(missing_ok=True)
            except OSError as exc:
                logger.exception("Local storage cleanup failed")
                raise HTTPException(
                    status_code=503,
                    detail="Document storage cleanup failed",
                ) from exc
            return

        try:
            self.supabase.storage.from_(self.bucket).remove([storage_path])
        except Exception as exc:
            logger.exception("Private storage cleanup failed")
            raise HTTPException(
                status_code=503,
                detail="Document storage cleanup failed",
            ) from exc


storage_service = StorageService()
