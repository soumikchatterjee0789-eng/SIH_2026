from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionOut, TransactionUpdate, CSVUploadPreview, CSVUploadResult, CSVRowPreview
from app.utils.response import success_response
from app.utils.errors import APIError, ErrorCode
from app.utils.deps import get_current_user, require_consent
from app.services import transaction_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB - reasonable ceiling for a CSV upload


@router.post("/upload")
async def upload_transactions(
    file: UploadFile = File(...),
    confirm: bool = Form(default=False),
    batch_token: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("transactions")),
):
    """
    Two-step flow (PRD Section 10):
      1. confirm=false (default): parse + validate the CSV, return a
         preview with per-row errors. Nothing is stored.
      2. confirm=true + batch_token from step 1: store only the
         previously-validated rows.
    """
    if not confirm:
        if not file.filename.lower().endswith(".csv"):
            raise APIError(400, "Please upload a .csv file.", ErrorCode.INVALID_INPUT)

        contents = await file.read()
        if len(contents) > MAX_UPLOAD_BYTES:
            raise APIError(400, "The file is too large. Please upload a CSV under 5MB.", ErrorCode.INVALID_INPUT)

        token, rows = transaction_service.parse_and_validate_csv(user.id, contents)
        preview_rows = [
            CSVRowPreview(
                row_number=r["row_number"], date=r["date"], description=r["description"],
                amount=r["amount"], type=r["type"], category=r["category"], valid=r["valid"], errors=r["errors"],
            )
            for r in rows
        ]
        valid_count = sum(1 for r in rows if r["valid"])
        result = CSVUploadPreview(
            batch_token=token,
            total_rows=len(rows),
            valid_rows=valid_count,
            invalid_rows=len(rows) - valid_count,
            rows=preview_rows,
        )
        return success_response(result.model_dump(mode="json"), message="Preview ready. Confirm to store the valid rows.")

    if not batch_token:
        raise APIError(400, "batch_token is required when confirm=true.", ErrorCode.INVALID_INPUT)

    inserted, skipped, source_batch_id = transaction_service.confirm_and_store(db, user.id, batch_token)
    log_action(
        db, user.id, "DATA_CREATED", "transaction_csv_upload",
        new_value=f"inserted={inserted}, skipped={skipped}, batch={source_batch_id}",
    )
    result = CSVUploadResult(inserted_count=inserted, skipped_count=skipped, source_batch_id=source_batch_id)
    return success_response(result.model_dump(mode="json"), message=f"{inserted} transactions stored.")


@router.get("")
def list_transactions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("transactions")),
):
    records = (
        db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.transaction_date.desc()).all()
    )
    return success_response([TransactionOut.model_validate(r).model_dump(mode="json") for r in records])


@router.put("/{transaction_id}")
def update_transaction(
    transaction_id: str,
    payload: TransactionUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("transactions")),
):
    record = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user.id).first()
    if record is None:
        raise APIError(404, "Transaction not found.", ErrorCode.DATA_NOT_FOUND)

    old_value = {
        "description": record.description, "amount": float(record.amount),
        "type": record.type, "category": record.category,
    }
    update_data = payload.model_dump(exclude_unset=True, exclude={"correction_reason"})
    for field, value in update_data.items():
        setattr(record, field, value)
    if update_data:
        record.is_corrected = True

    db.commit()
    db.refresh(record)

    log_action(
        db, user.id, "USER_CORRECTION", "transaction",
        old_value=str(old_value), new_value=str(update_data), reason=payload.correction_reason,
    )
    return success_response(
        TransactionOut.model_validate(record).model_dump(mode="json"),
        message="Transaction updated. Financial health and credit-readiness will reflect the correction on next fetch.",
    )


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("transactions")),
):
    record = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user.id).first()
    if record is None:
        raise APIError(404, "Transaction not found.", ErrorCode.DATA_NOT_FOUND)

    db.delete(record)
    db.commit()
    log_action(db, user.id, "DATA_DELETED", "transaction", old_value=str(transaction_id))
    return success_response(None, message="Transaction deleted.")
