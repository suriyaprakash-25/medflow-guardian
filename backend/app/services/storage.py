import uuid
import os
from fastapi import UploadFile, HTTPException
from supabase import create_client, Client
from app.core.config import settings

class StorageService:
    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise Exception("Supabase is not properly configured. Cannot initialize StorageService.")
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.bucket = settings.SUPABASE_BUCKET

    def upload_document(self, file: UploadFile, patient_id: int) -> str:
        """
        Securely uploads a document and returns the internal storage path.
        Enforces validation and path structure.
        """
        # Validate extensions
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in [".pdf", ".jpg", ".jpeg", ".png", ".txt"]:
            raise HTTPException(status_code=400, detail="Invalid file extension")
        
        safe_filename = f"{uuid.uuid4().hex}{file_ext}"
        storage_path = f"patient/{patient_id}/{safe_filename}"
        
        file.file.seek(0)
        file_bytes = file.file.read()
        
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
        try:
            return self.supabase.storage.from_(self.bucket).download(storage_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to download document from storage: {str(e)}")

storage_service = StorageService()
