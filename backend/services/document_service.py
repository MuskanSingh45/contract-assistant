"""Uploads: validation, storage, contract/version creation. Shapes: docs/api/contracts.md, versions.md."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from backend.core.config import settings
from backend.core.exceptions import AppError
from backend.documents.parser import detect_mime_type
from backend.services.common import get_contract, latest_version, new_id, utc_now
from backend.utils.hashing import sha256_bytes


def _validate(filename: str | None, data: bytes) -> str:
    if not filename or not data:
        raise AppError("EMPTY_UPLOAD", "No file was uploaded, or the file is empty.", 400)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise AppError("FILE_TOO_LARGE", f"File is larger than {settings.max_upload_mb} MB.", 413)
    mime = detect_mime_type(filename, data[:8])
    if not mime:
        raise AppError("INVALID_DOCUMENT", "Unsupported document format. Upload a PDF or DOCX file.", 415)
    return mime


def _safe_name(filename: str) -> str:
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9._ -]", "_", name) or "document"


def _store(contract_id: str, version_id: str, filename: str, data: bytes) -> str:
    folder = Path(settings.upload_dir) / contract_id / version_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / _safe_name(filename)
    path.write_bytes(data)
    return str(path)


def _insert_version(conn, contract_id: str, number: int, filename: str, data: bytes, mime: str) -> str:
    version_id = new_id("ver")
    path = _store(contract_id, version_id, filename, data)
    conn.execute(
        """INSERT INTO contract_versions (id, contract_id, version_number, file_name, file_path, file_hash,
               mime_type, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (version_id, contract_id, number, _safe_name(filename), path, sha256_bytes(data), mime, utc_now()),
    )
    return version_id


def create_contract(conn: sqlite3.Connection, filename: str | None, data: bytes, name: str | None) -> tuple[str, str]:
    mime = _validate(filename, data)
    contract_id = new_id("ctr")
    now = utc_now()
    display_name = (name or "").strip() or Path(filename).stem
    conn.execute(
        "INSERT INTO contracts (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (contract_id, display_name, now, now),
    )
    version_id = _insert_version(conn, contract_id, 1, filename, data, mime)
    conn.commit()
    return contract_id, version_id


def create_version(conn: sqlite3.Connection, contract_id: str, filename: str | None, data: bytes) -> str:
    get_contract(conn, contract_id)
    mime = _validate(filename, data)
    latest = latest_version(conn, contract_id)
    if latest and latest["file_hash"] == sha256_bytes(data):
        raise AppError("DUPLICATE_VERSION", "This file is identical to the latest version.", 409)
    number = (latest["version_number"] if latest else 0) + 1
    version_id = _insert_version(conn, contract_id, number, filename, data, mime)
    conn.execute("UPDATE contracts SET updated_at = ? WHERE id = ?", (utc_now(), contract_id))
    conn.commit()
    return version_id
