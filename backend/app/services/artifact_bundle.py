import io
import logging
import zipfile
from collections.abc import Iterable

from app.services.artifacts import validate_relative_path

logger = logging.getLogger(__name__)


def build_project_archive(files: Iterable[tuple[str, str]]) -> bytes:
    latest_files: dict[str, tuple[str, str]] = {}
    for name, content in files:
        try:
            path = validate_relative_path(name)
        except ValueError:
            logger.warning("Skipping protected artifact from project archive")
            continue
        normalized_name = path.as_posix()
        latest_files[normalized_name.casefold()] = (normalized_name, content)

    if not latest_files:
        raise ValueError("Tidak ada file proyek yang aman untuk diunduh.")

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, content in latest_files.values():
            bundle.writestr(name, content)
    return archive.getvalue()
