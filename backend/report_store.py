"""Local persistence for reports explicitly uploaded to OsteoLens.

The original bytes and extracted text are stored locally. No report is linked to
a case unless the uploader explicitly supplies a manifest Case ID.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from backend.public_access import report_owner
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import uuid
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_DATA_DIR = Path(os.environ.get("OSTEOLENS_REPORT_DATA_DIR", PROJECT_ROOT / "backend" / "data" / "reports")).resolve()
DATABASE_PATH = REPORT_DATA_DIR / "reports.sqlite3"
REPORT_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


class ReportStoreError(ValueError):
    pass


@contextmanager
def _database():
    REPORT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY,
            case_id TEXT NULL,
            filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            extraction_status TEXT NOT NULL,
            byte_size INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            analysis_path TEXT NOT NULL
        )"""
    )
    if "owner_id" not in {row[1] for row in connection.execute("PRAGMA table_info(reports)")}:
        connection.execute("ALTER TABLE reports ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'local'")
    connection.execute("CREATE INDEX IF NOT EXISTS reports_owner ON reports(owner_id)")
    connection.commit()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _validate_case_id(case_id: str | None) -> str | None:
    if case_id is None or not case_id.strip():
        return None
    manifest_path = PROJECT_ROOT / "src" / "data" / "cases.json"
    try:
        cases = json.loads(manifest_path.read_text(encoding="utf-8"))["cases"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ReportStoreError("The case manifest could not be read; report was not associated.") from exc
    valid_ids = {str(record["case_id"]) for record in cases}
    if case_id not in valid_ids:
        raise ReportStoreError(f"Unknown Case ID: {case_id}")
    return case_id


def validate_case_id(case_id: str | None) -> str | None:
    """Public validation used before analysis begins, so bad IDs store nothing."""
    return _validate_case_id(case_id)


def _safe_filename(filename: str) -> str:
    candidate = Path((filename or "report.txt").replace("\\", "/")).name
    candidate = re.sub(r"[^A-Za-z0-9._ -]", "_", candidate).strip(" .")
    return candidate[:180] or "report.txt"


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "report_id": row["report_id"],
        "case_id": row["case_id"],
        "filename": row["filename"],
        "uploaded_at": row["uploaded_at"],
        "extraction_status": row["extraction_status"],
        "byte_size": row["byte_size"],
    }


def save_report(result: dict[str, Any], original_bytes: bytes, case_id: str | None = None) -> dict[str, Any]:
    case_id = _validate_case_id(case_id)
    report_id = str(result.get("report_id") or "")
    if not REPORT_ID_PATTERN.fullmatch(report_id):
        raise ReportStoreError("The report analyser returned an invalid report identifier.")
    filename = _safe_filename(str(result.get("document", {}).get("filename", "report.txt")))
    extension = Path(filename).suffix.lower()
    if extension not in {".pdf", ".txt"}:
        raise ReportStoreError("Only PDF or TXT reports can be stored.")
    storage_root = REPORT_DATA_DIR.resolve()
    report_dir = (storage_root / report_id).resolve()
    if report_dir.parent != storage_root:
        raise ReportStoreError("Invalid report storage path.")
    if report_owner.get() != 'local':
        with _database() as connection:
            count, size = connection.execute("SELECT COUNT(*), COALESCE(SUM(byte_size),0) FROM reports WHERE owner_id = ?", (report_owner.get(),)).fetchone()
            total_size = connection.execute("SELECT COALESCE(SUM(byte_size),0) FROM reports WHERE owner_id != 'local'").fetchone()[0]
        if count >= 20 or size + len(original_bytes) > 50*1024*1024 or total_size + len(original_bytes) > 1024*1024*1024:
            raise ReportStoreError("Report storage limit reached. Delete previous uploads or try later.")
    report_dir.mkdir(parents=True, exist_ok=False)
    stored_file = report_dir / f"original{extension}"
    analysis_file = report_dir / "analysis.json"
    uploaded_at = datetime.now(timezone.utc).isoformat()
    document = result.get("document", {})
    record = {
        "report_id": report_id,
        "case_id": case_id,
        "filename": filename,
        "uploaded_at": uploaded_at,
        "extraction_status": str(document.get("extraction_method") or "processed"),
        "byte_size": len(original_bytes),
        "file_path": str(stored_file.relative_to(storage_root)),
        "analysis_path": str(analysis_file.relative_to(storage_root)),
        "owner_id": report_owner.get(),
    }
    try:
        stored_file.write_bytes(original_bytes)
        analysis_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        with _database() as connection:
            connection.execute(
                "INSERT INTO reports (report_id, case_id, filename, uploaded_at, extraction_status, byte_size, file_path, analysis_path, owner_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(record[key] for key in ("report_id", "case_id", "filename", "uploaded_at", "extraction_status", "byte_size", "file_path", "analysis_path", "owner_id")),
            )
    except Exception:
        shutil.rmtree(report_dir, ignore_errors=True)
        raise
    return {key: value for key, value in record.items() if key not in {"file_path", "analysis_path", "owner_id"}}


def list_reports(case_id: str | None = None) -> list[dict[str, Any]]:
    case_id = _validate_case_id(case_id)
    with _database() as connection:
        if case_id is None:
            rows = connection.execute("SELECT * FROM reports WHERE owner_id = ? ORDER BY uploaded_at DESC", (report_owner.get(),)).fetchall()
        else:
            rows = connection.execute("SELECT * FROM reports WHERE case_id = ? AND owner_id = ? ORDER BY uploaded_at DESC", (case_id, report_owner.get())).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_report(report_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not REPORT_ID_PATTERN.fullmatch(report_id or ""):
        raise ReportStoreError("Invalid report ID.")
    with _database() as connection:
        row = connection.execute("SELECT * FROM reports WHERE report_id = ? AND owner_id = ?", (report_id, report_owner.get())).fetchone()
    if row is None:
        raise ReportStoreError("No locally stored report was found for this report ID.")
    record = _row_to_dict(row)
    root = REPORT_DATA_DIR.resolve()
    analysis_path = (root / row["analysis_path"]).resolve()
    if analysis_path.parent != (root / report_id).resolve() or not analysis_path.is_file():
        raise ReportStoreError("Stored report analysis is missing or invalid.")
    try:
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportStoreError("Stored report analysis could not be read.") from exc
    return record, analysis


def update_case_association(report_id: str, case_id: str | None) -> dict[str, Any]:
    case_id = _validate_case_id(case_id)
    if not REPORT_ID_PATTERN.fullmatch(report_id or ""):
        raise ReportStoreError("Invalid report ID.")
    with _database() as connection:
        cursor = connection.execute("UPDATE reports SET case_id = ? WHERE report_id = ? AND owner_id = ?", (case_id, report_id, report_owner.get()))
        if cursor.rowcount == 0:
            raise ReportStoreError("No locally stored report was found for this report ID.")
        row = connection.execute("SELECT * FROM reports WHERE report_id = ? AND owner_id = ?", (report_id, report_owner.get())).fetchone()
    return _row_to_dict(row)


def delete_report(report_id: str) -> dict[str, Any]:
    if not REPORT_ID_PATTERN.fullmatch(report_id or ""):
        raise ReportStoreError("Invalid report ID.")
    with _database() as connection:
        row = connection.execute("SELECT * FROM reports WHERE report_id = ? AND owner_id = ?", (report_id, report_owner.get())).fetchone()
        if row is None:
            raise ReportStoreError("No locally stored report was found for this report ID.")
        storage_root = REPORT_DATA_DIR.resolve()
        directory = (storage_root / report_id).resolve()
        if directory.parent != storage_root:
            raise ReportStoreError("Invalid report storage path.")
        connection.execute("DELETE FROM reports WHERE report_id = ? AND owner_id = ?", (report_id, report_owner.get()))
    shutil.rmtree(directory)
    return {"report_id": report_id, "deleted": True}


def purge_expired_reports():
    """Remove public-demo uploads after 24 hours; never touch local reports."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    with _database() as connection:
        rows = connection.execute("SELECT report_id FROM reports WHERE owner_id != 'local' AND uploaded_at < ?", (cutoff,)).fetchall()
        for row in rows:
            report_id = row['report_id']
            directory = (REPORT_DATA_DIR.resolve() / report_id).resolve()
            if REPORT_ID_PATTERN.fullmatch(report_id) and directory.parent == REPORT_DATA_DIR.resolve():
                shutil.rmtree(directory, ignore_errors=True)
                connection.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
                from backend.report_analyzer import clear_report_session
                clear_report_session(report_id)
