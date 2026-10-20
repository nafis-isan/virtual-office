import os
import re
import hashlib
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from fastapi import HTTPException

from app.core.config import settings

MAX_ARTIFACT_BYTES = 256 * 1024
PROTECTED_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}


def validate_relative_path(value: str) -> PurePosixPath:
    normalized = value.strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    windows_path = PureWindowsPath(value)
    if (
        not normalized
        or len(normalized) > 200
        or path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or any(part in {"", ".", ".."} for part in normalized.split("/"))
        or any(":" in part or re.search(r"[\x00-\x1f]", part) for part in normalized.split("/"))
        or any(part.casefold() == ".git" for part in path.parts)
        or path.name.casefold().startswith(".env")
        or path.suffix.casefold() in PROTECTED_SUFFIXES
    ):
        raise ValueError("Lokasi file tidak valid atau dilindungi.")
    return path


def _workspace_destination(
    relative_path: str,
    *,
    create_parent: bool = False,
) -> tuple[PurePosixPath, Path]:
    try:
        path = validate_relative_path(relative_path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    root = Path(settings.workspace_root).expanduser().resolve()
    destination = root.joinpath(*path.parts)
    try:
        resolved_parent = destination.parent.resolve(strict=False)
        if not resolved_parent.is_relative_to(root):
            raise HTTPException(status_code=422, detail="Lokasi file harus berada di dalam workspace.")
        if create_parent:
            destination.parent.mkdir(parents=True, exist_ok=True)
            resolved_parent = destination.parent.resolve(strict=True)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Lokasi workspace tidak dapat diakses.") from exc
    resolved_destination = resolved_parent / destination.name
    if not resolved_parent.is_relative_to(root) or not resolved_destination.is_relative_to(root):
        raise HTTPException(status_code=422, detail="Lokasi file harus berada di dalam workspace.")
    if destination.is_symlink():
        raise HTTPException(status_code=422, detail="File symbolic link tidak dapat dibaca atau ditulis.")
    return path, destination


def read_workspace_file(relative_path: str) -> tuple[str, str | None, str | None]:
    path, destination = _workspace_destination(relative_path)
    if not destination.exists():
        return path.as_posix(), None, None
    try:
        if not destination.is_file():
            raise HTTPException(status_code=422, detail="Lokasi tujuan bukan file.")
        if destination.stat().st_size > MAX_ARTIFACT_BYTES:
            raise HTTPException(status_code=413, detail="File tujuan melebihi batas pratinjau 256 KB.")
        data = destination.read_bytes()
        if len(data) > MAX_ARTIFACT_BYTES:
            raise HTTPException(status_code=413, detail="File tujuan melebihi batas pratinjau 256 KB.")
        return path.as_posix(), data.decode("utf-8"), hashlib.sha256(data).hexdigest()
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=415, detail="File tujuan bukan teks UTF-8 yang dapat dibandingkan.") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="File tujuan tidak dapat dibaca.") from exc


def save_workspace_file(
    relative_path: str,
    content: str,
    *,
    overwrite: bool,
    expected_sha256: str | None = None,
) -> str:
    path, destination = _workspace_destination(relative_path, create_parent=True)
    data = content.encode("utf-8")
    if len(data) > MAX_ARTIFACT_BYTES:
        raise HTTPException(status_code=413, detail="Ukuran file melebihi batas 256 KB.")
    parent = destination.parent
    try:
        if not overwrite:
            if expected_sha256 is not None:
                raise HTTPException(status_code=422, detail="Status pratinjau file tidak konsisten.")
            with destination.open("xb") as output:
                output.write(data)
        else:
            if expected_sha256 is None:
                raise HTTPException(status_code=422, detail="Pratinjau ulang file sebelum menimpanya.")
            current_data = destination.read_bytes()
            if hashlib.sha256(current_data).hexdigest() != expected_sha256:
                raise HTTPException(
                    status_code=409,
                    detail="File berubah setelah pratinjau. Tinjau perubahan terbaru sebelum menyimpan.",
                )
            with tempfile.NamedTemporaryFile(dir=parent, prefix=".nf-office-", delete=False) as output:
                temporary_path = Path(output.name)
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            try:
                os.replace(temporary_path, destination)
            finally:
                temporary_path.unlink(missing_ok=True)
    except FileExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail="File tujuan sudah ada. Konfirmasi penimpaan untuk melanjutkan.",
        ) from exc
    except FileNotFoundError as exc:
        if overwrite:
            raise HTTPException(
                status_code=409,
                detail="File berubah setelah pratinjau. Tinjau kembali sebelum menyimpan.",
            ) from exc
        raise HTTPException(status_code=500, detail="Folder workspace tidak ditemukan.") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="File tidak dapat disimpan ke workspace.") from exc
    return path.as_posix()
