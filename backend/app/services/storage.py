import uuid
import os
from fastapi import UploadFile, HTTPException
from supabase import create_client, Client
from app.core.config import settings

class StorageService:
    def __init__(self):
        self.use_local = not settings.SUPABASE_URL or not settings.SUPABASE_KEY or "placeholder" in settings.SUPABASE_KEY
        if self.use_local:
            if getattr(settings, "ENV", "development") == "production":
                raise Exception("CRITICAL SECURITY ERROR: Missing Supabase credentials in production! Local fallback is forbidden for medical documents.")
            print("WARNING: Using local file storage. Supabase key is placeholder or missing.")
            self.local_dir = os.path.join(os.getcwd(), "local_storage")
            os.makedirs(self.local_dir, exist_ok=True)
        else:
            self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            self.bucket = settings.SUPABASE_BUCKET

    def upload_document(self, file: UploadFile, patient_id: int) -> str:
        """
        Securely uploads a document and returns the internal storage path.
        Enforces validation and path structure.
        """
        # Validate extensions
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in [".pdf", ".jpg", ".jpeg", ".png", ".txt", ".docx", ".doc"]:
            raise HTTPException(status_code=400, detail="Invalid file extension")
        
        safe_filename = f"{uuid.uuid4().hex}{file_ext}"
        storage_path = f"patient/{patient_id}/{safe_filename}"
        
        file.file.seek(0)
        file_bytes = file.file.read()
        
        if self.use_local:
            local_path = os.path.join(self.local_dir, storage_path.replace("/", os.sep))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(file_bytes)
            return storage_path

        try:
            self.supabase.storage.from_(self.bucket).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": file.content_type}
            )
            return storage_path
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload document to storage: {str(e)}")

    def download_document(self, storage_path: str) -> bytes:
        """
        Securely fetches file bytes from the private storage bucket.
        """
        if self.use_local:
            local_path = os.path.join(self.local_dir, storage_path.replace("/", os.sep))
            if not os.path.exists(local_path):
                raise HTTPException(status_code=404, detail="File not found in local storage")
            with open(local_path, "rb") as f:
                return f.read()

        try:
            return self.supabase.storage.from_(self.bucket).download(storage_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to download document from storage: {str(e)}")

storage_service = StorageService()
