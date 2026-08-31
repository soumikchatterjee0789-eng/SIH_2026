"""
Transaction ingestion service.

Implements the PRD Section 10 CSV flow:
    1. Validate the CSV
    2. Detect invalid rows
    3. Show preview
    4. Ask user for confirmation
    5. Store only after confirmation
    6. Categorize transactions
    7. Allow user correction

Preview results are cached in-memory (per-process) keyed by
(user_id, batch_token) so that "confirm=true" can re-use the already
validated rows without re-parsing or trusting client-supplied data, AND
so that one user can never confirm/store another user's preview batch
just by knowing (or guessing) their batch_token. This is a deliberately
simple approach appropriate for a hackathon MVP - in production this
cache would move to Redis or a short-lived DB table.
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.utils.errors import APIError, ErrorCode

VALID_TYPES = {"income", "expense"}
DEFAULT_CATEGORY = "Other"
REQUIRED_COLUMNS = {"date", "description", "amount", "type"}

# Simple in-memory preview cache: {(user_id, batch_token): [validated_row_dict, ...]}
_PREVIEW_CACHE: dict[tuple[str, str], list[dict]] = {}


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _validate_row(row_number: int, row: dict) -> dict:
    errors: list[str] = []

    raw_date = (row.get("date") or "").strip()
    raw_description = (row.get("description") or "").strip()
    raw_amount = (row.get("amount") or "").strip()
    raw_type = (row.get("type") or "").strip().lower()
    raw_category = (row.get("category") or "").strip() or DEFAULT_CATEGORY

    parsed_date = _parse_date(raw_date)
    if parsed_date is None:
        errors.append("date is missing or not in YYYY-MM-DD format")

    if not raw_description:
        errors.append("description is required")

    amount_value = None
    try:
        amount_value = float(raw_amount)
        if amount_value <= 0:
            errors.append("amount must be greater than 0")
    except (TypeError, ValueError):
        errors.append("amount is missing or not a valid number")

    if raw_type not in VALID_TYPES:
        errors.append("type must be 'income' or 'expense'")

    return {
        "row_number": row_number,
        "date": raw_date or None,
        "description": raw_description or None,
        "amount": raw_amount or None,
        "type": raw_type or None,
        "category": raw_category,
        "valid": len(errors) == 0,
        "errors": errors,
        # internal parsed values, only used if valid
        "_parsed_date": parsed_date,
        "_parsed_amount": amount_value,
    }


def parse_and_validate_csv(user_id: str, file_bytes: bytes) -> tuple[str, list[dict]]:
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise APIError(400, "The file could not be read as UTF-8 text. Please upload a plain CSV file.", ErrorCode.INVALID_INPUT)

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise APIError(400, "The CSV file appears to be empty.", ErrorCode.INVALID_INPUT)

    header = {h.strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - header
    if missing:
        raise APIError(
            400,
            f"The CSV is missing required column(s): {', '.join(sorted(missing))}.",
            ErrorCode.INVALID_TRANSACTION,
        )

    normalized_rows = []
    for i, raw_row in enumerate(reader, start=1):
        normalized = {(k or "").strip().lower(): v for k, v in raw_row.items()}
        normalized_rows.append(_validate_row(i, normalized))

    if not normalized_rows:
        raise APIError(400, "The CSV file has no data rows.", ErrorCode.INVALID_INPUT)

    batch_token = str(uuid.uuid4())
    _PREVIEW_CACHE[(user_id, batch_token)] = normalized_rows
    return batch_token, normalized_rows


def get_cached_preview(user_id: str, batch_token: str) -> list[dict]:
    rows = _PREVIEW_CACHE.get((user_id, batch_token))
    if rows is None:
        raise APIError(
            400,
            "This upload preview has expired, was never created, or does not belong to you. "
            "Please re-upload the CSV file.",
            ErrorCode.INVALID_INPUT,
        )
    return rows


def _auto_categorize(description: str, existing_category: str) -> str:
    """Very small keyword-based categorizer used when a CSV row's category
    column is empty/'Other'. Kept intentionally simple and transparent -
    PRD Section 35 prefers a transparent approach over an opaque model."""
    if existing_category and existing_category != DEFAULT_CATEGORY:
        return existing_category

    text = description.lower()
    keyword_map = {
        "Food": ["food", "restaurant", "grocery", "swiggy", "zomato", "canteen"],
        "Rent/Hostel": ["rent", "hostel", "pg fee", "housing"],
        "Education": ["tuition", "fees", "course", "book", "exam", "scholarship"],
        "Transport": ["uber", "ola", "bus", "metro", "fuel", "petrol", "auto"],
        "Utilities": ["electricity", "water bill", "recharge", "internet", "wifi"],
        "Healthcare": ["pharmacy", "hospital", "doctor", "medicine"],
        "Business": ["supplier", "inventory", "wholesale", "vendor"],
        "Entertainment": ["movie", "netflix", "spotify", "game"],
        "Shopping": ["amazon", "flipkart", "myntra", "mall"],
    }
    for category, keywords in keyword_map.items():
        if any(kw in text for kw in keywords):
            return category
    return DEFAULT_CATEGORY


def confirm_and_store(db: Session, user_id: str, batch_token: str) -> tuple[int, int, str]:
    rows = get_cached_preview(user_id, batch_token)
    valid_rows = [r for r in rows if r["valid"]]

    source_batch_id = str(uuid.uuid4())
    inserted = 0

    for r in valid_rows:
        category = _auto_categorize(r["description"], r["category"])
        txn = Transaction(
            user_id=user_id,
            transaction_date=r["_parsed_date"],
            description=r["description"],
            amount=r["_parsed_amount"],
            type=r["type"],
            category=category,
            source_batch_id=source_batch_id,
        )
        db.add(txn)
        inserted += 1

    db.commit()

    # Clear the cache entry now that it has been consumed.
    _PREVIEW_CACHE.pop((user_id, batch_token), None)

    skipped = len(rows) - inserted
    return inserted, skipped, source_batch_id
