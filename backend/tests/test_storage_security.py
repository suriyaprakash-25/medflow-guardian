from pathlib import Path

import pytest
from fastapi import HTTPException

from app.services.storage import StorageService


@pytest.mark.parametrize(
    "path",
    [
        "../secret.pdf",
        "patient/1/../../secret.pdf",
        "/patient/1/file.pdf",
        "patient/not-a-number/file.pdf",
        "patient/1/nested/file.pdf",
        "patient\\1\\file.pdf",
        "file.pdf",
        "",
    ],
)
def test_storage_object_key_validation_rejects_untrusted_paths(path):
    with pytest.raises(HTTPException) as exc:
        StorageService._validate_storage_path(path)
    assert exc.value.status_code == 400


def test_storage_object_key_validation_accepts_medflow_key():
    assert (
        StorageService._validate_storage_path("patient/42/abc123.pdf")
        == "patient/42/abc123.pdf"
    )


def test_local_storage_path_cannot_escape_root(tmp_path):
    service = StorageService.__new__(StorageService)
    service.use_local = True
    service.local_dir = Path(tmp_path).resolve()

    with pytest.raises(HTTPException):
        service._local_path("patient/1/../../outside.pdf")


def test_storage_backend_error_is_not_reflected_to_client():
    class BrokenBucket:
        def download(self, path):
            raise RuntimeError("service-role-key=super-secret-internal-value")

    class BrokenStorage:
        def from_(self, bucket):
            return BrokenBucket()

    class BrokenSupabase:
        storage = BrokenStorage()

    service = StorageService.__new__(StorageService)
    service.use_local = False
    service.bucket = "private"
    service.supabase = BrokenSupabase()

    with pytest.raises(HTTPException) as exc:
        service.download_document("patient/1/abc.pdf")

    assert exc.value.status_code == 503
    assert "super-secret" not in exc.value.detail
    assert exc.value.detail == "Document storage is temporarily unavailable"


def test_local_compensating_delete_removes_orphan(tmp_path):
    service = StorageService.__new__(StorageService)
    service.use_local = True
    service.local_dir = Path(tmp_path).resolve()

    object_path = service._local_path("patient/7/orphan.pdf")
    object_path.parent.mkdir(parents=True, exist_ok=True)
    object_path.write_bytes(b"protected")

    service.delete_document("patient/7/orphan.pdf")

    assert not object_path.exists()
