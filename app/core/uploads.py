import mimetypes
import shutil
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

UPLOAD_ROOT = Path("uploads")
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 MB
STORAGE_PREFIXES = ("members/", "nominees/")
SPACES_REQUIRED_SETTINGS = (
    "SPACES_BUCKET",
    "SPACES_REGION",
    "SPACES_ENDPOINT",
    "SPACES_ACCESS_KEY",
    "SPACES_SECRET_KEY",
)


@lru_cache(maxsize=1)
def _spaces_client():
    values = {name: getattr(settings, name) for name in SPACES_REQUIRED_SETTINGS}
    if not any(values.values()):
        return None

    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"Missing DigitalOcean Spaces settings: {', '.join(missing)}")

    return boto3.client(
        "s3",
        endpoint_url=settings.SPACES_ENDPOINT,
        region_name=settings.SPACES_REGION,
        aws_access_key_id=settings.SPACES_ACCESS_KEY,
        aws_secret_access_key=settings.SPACES_SECRET_KEY,
    )


def detect_image_ext(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    return None


def read_image(file: UploadFile, label: str) -> tuple[bytes, str]:
    data = file.file.read(MAX_IMAGE_SIZE + 1)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{label} is empty")
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{label} must be 2 MB or less")
    ext = detect_image_ext(data)
    if ext is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{label} must be a JPG or PNG image")
    return data, ext


def _save_files(folder: str, code: str, files: dict[str, tuple[bytes, str]]) -> dict[str, str]:
    client = _spaces_client()
    paths = {}
    for name, (data, ext) in files.items():
        key = f"{folder}/{code}/{name}.{ext}"
        if client:
            client.put_object(
                Bucket=settings.SPACES_BUCKET,
                Key=key,
                Body=data,
                ContentType=f"image/{'jpeg' if ext == 'jpg' else ext}",
            )
            paths[name] = key
        else:
            path = UPLOAD_ROOT / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            paths[name] = path.as_posix()
    return paths


def _delete_files(folder: str, code: str) -> None:
    client = _spaces_client()
    if client:
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=settings.SPACES_BUCKET,
            Prefix=f"{folder}/{code}/",
        ):
            objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
            if objects:
                result = client.delete_objects(
                    Bucket=settings.SPACES_BUCKET,
                    Delete={"Objects": objects, "Quiet": True},
                )
                if result.get("Errors"):
                    raise RuntimeError("Could not delete all documents from Spaces")

    local_folder = (UPLOAD_ROOT / folder / code).resolve()
    upload_root = UPLOAD_ROOT.resolve()
    if local_folder.is_relative_to(upload_root) and local_folder.is_dir():
        shutil.rmtree(local_folder)


def save_member_files(member_code: str, files: dict[str, tuple[bytes, str]]) -> dict[str, str]:
    return _save_files("members", member_code, files)


def delete_member_files(member_code: str) -> None:
    _delete_files("members", member_code)


def save_nominee_files(member_code: str, files: dict[str, tuple[bytes, str]]) -> dict[str, str]:
    return _save_files("nominees", member_code, files)


def delete_nominee_files(member_code: str) -> None:
    _delete_files("nominees", member_code)


def read_member_file(storage_path: str) -> tuple[bytes, str]:
    path = Path(storage_path)
    if path.is_file():
        resolved_path = path.resolve()
        if not resolved_path.is_relative_to(UPLOAD_ROOT.resolve()):
            raise FileNotFoundError("Document not found")
        data = resolved_path.read_bytes()
        media_type = mimetypes.guess_type(resolved_path.name)[0] or "application/octet-stream"
        return data, media_type

    client = _spaces_client()
    if not client or not storage_path.startswith(STORAGE_PREFIXES) or ".." in path.parts:
        raise FileNotFoundError("Document not found")

    try:
        result = client.get_object(Bucket=settings.SPACES_BUCKET, Key=storage_path)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") in {"NoSuchKey", "404", "NotFound"}:
            raise FileNotFoundError("Document not found") from error
        raise

    data = result["Body"].read()
    media_type = result.get("ContentType") or mimetypes.guess_type(path.name)[0]
    return data, media_type or "application/octet-stream"