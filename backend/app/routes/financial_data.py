"""
Financial Data routes (PRD Section 9 + Section 21).

The PRD's API contract lists a single generic family of endpoints under
/api/financial-data. Since income, expense, savings, and borrowing records
each have distinct shapes (PRD Section 9), we expose them as documented
sub-resources under that same base path:

    /api/financial-data/income
    /api/financial-data/expenses
    /api/financial-data/savings
    /api/financial-data/borrowing

...plus a combined read endpoint at /api/financial-data that returns all
four groups the user currently has active consent for. This keeps the
contract's base path stable while making each record type's schema
explicit and independently documented (see README's "API contract notes").

Every write requires an ACTIVE consent for that specific data category
(PRD Section 4.1). Every update marks is_corrected=True and triggers a
recalculation-on-read model: analytics/score endpoints always recompute
live from current data, so a correction is reflected immediately without
a separate "recalculate" call (PRD Section 4.4 / 17).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.financial import IncomeRecord, ExpenseRecord, SavingsRecord, BorrowingRecord
from app.schemas.financial import (
    IncomeCreate, IncomeUpdate, IncomeOut,
    ExpenseCreate, ExpenseUpdate, ExpenseOut,
    SavingsCreate, SavingsOut,
    BorrowingCreate, BorrowingOut,
    EXPENSE_CATEGORIES,
)
from app.utils.response import success_response
from app.utils.errors import APIError, ErrorCode
from app.utils.deps import get_current_user, require_consent
from app.services.audit_service import log_action
from app.models.consent import Consent

router = APIRouter(prefix="/api/financial-data", tags=["Financial Data"])


# ---------------------------------------------------------------------------
# Combined read
# ---------------------------------------------------------------------------
@router.get("")
def get_financial_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    active_categories = {
        c.data_category
        for c in db.query(Consent).filter(Consent.user_id == user.id, Consent.is_active.is_(True)).all()
    }

    income = (
        [IncomeOut.model_validate(r).model_dump(mode="json") for r in
         db.query(IncomeRecord).filter(IncomeRecord.user_id == user.id)]
        if "income" in active_categories else []
    )
    expenses = (
        [ExpenseOut.model_validate(r).model_dump(mode="json") for r in
         db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user.id)]
        if "expenses" in active_categories else []
    )
    savings = (
        [SavingsOut.model_validate(r).model_dump(mode="json") for r in
         db.query(SavingsRecord).filter(SavingsRecord.user_id == user.id)]
        if "savings" in active_categories else []
    )
    borrowing = (
        [BorrowingOut.model_validate(r).model_dump(mode="json") for r in
         db.query(BorrowingRecord).filter(BorrowingRecord.user_id == user.id)]
        if "borrowing" in active_categories else []
    )

    return success_response({"income": income, "expenses": expenses, "savings": savings, "borrowing": borrowing})


# ---------------------------------------------------------------------------
# Income
# ---------------------------------------------------------------------------
@router.post("/income")
def add_income(
    payload: IncomeCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("income")),
):
    record = IncomeRecord(user_id=user.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    log_action(db, user.id, "DATA_CREATED", "income_record", new_value=str(payload.model_dump(mode="json")))
    return success_response(IncomeOut.model_validate(record).model_dump(mode="json"), message="Income added.")


@router.get("/income")
def list_income(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("income")),
):
    records = db.query(IncomeRecord).filter(IncomeRecord.user_id == user.id).order_by(IncomeRecord.record_date.desc()).all()
    return success_response([IncomeOut.model_validate(r).model_dump(mode="json") for r in records])


@router.put("/income/{record_id}")
def update_income(
    record_id: str,
    payload: IncomeUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("income")),
):
    record = db.query(IncomeRecord).filter(IncomeRecord.id == record_id, IncomeRecord.user_id == user.id).first()
    if record is None:
        raise APIError(404, "Income record not found.", ErrorCode.DATA_NOT_FOUND)

    old_value = {"source": record.source, "amount": float(record.amount), "frequency": record.frequency}
    update_data = payload.model_dump(exclude_unset=True, exclude={"correction_reason"})
    for field, value in update_data.items():
        setattr(record, field, value)
    if update_data:
        record.is_corrected = True

    db.commit()
    db.refresh(record)

    log_action(
        db, user.id, "USER_CORRECTION", "income_record",
        old_value=str(old_value), new_value=str(update_data), reason=payload.correction_reason,
    )
    return success_response(
        IncomeOut.model_validate(record).model_dump(mode="json"),
        message="Income updated. Financial health and credit-readiness will reflect the correction on next fetch.",
    )


@router.delete("/income/{record_id}")
def delete_income(
    record_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("income")),
):
    record = db.query(IncomeRecord).filter(IncomeRecord.id == record_id, IncomeRecord.user_id == user.id).first()
    if record is None:
        raise APIError(404, "Income record not found.", ErrorCode.DATA_NOT_FOUND)

    db.delete(record)
    db.commit()
    log_action(db, user.id, "DATA_DELETED", "income_record", old_value=str(record_id))
    return success_response(None, message="Income record deleted.")


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------
@router.post("/expenses")
def add_expense(
    payload: ExpenseCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("expenses")),
):
    if payload.category not in EXPENSE_CATEGORIES:
        raise APIError(400, f"category must be one of {sorted(EXPENSE_CATEGORIES)}.", ErrorCode.VALIDATION_ERROR)

    record = ExpenseRecord(user_id=user.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    log_action(db, user.id, "DATA_CREATED", "expense_record", new_value=str(payload.model_dump(mode="json")))
    return success_response(ExpenseOut.model_validate(record).model_dump(mode="json"), message="Expense added.")


@router.get("/expenses")
def list_expenses(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("expenses")),
):
    records = (
        db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user.id).order_by(ExpenseRecord.record_date.desc()).all()
    )
    return success_response([ExpenseOut.model_validate(r).model_dump(mode="json") for r in records])


@router.put("/expenses/{record_id}")
def update_expense(
    record_id: str,
    payload: ExpenseUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("expenses")),
):
    record = db.query(ExpenseRecord).filter(ExpenseRecord.id == record_id, ExpenseRecord.user_id == user.id).first()
    if record is None:
        raise APIError(404, "Expense record not found.", ErrorCode.DATA_NOT_FOUND)

    if payload.category is not None and payload.category not in EXPENSE_CATEGORIES:
        raise APIError(400, f"category must be one of {sorted(EXPENSE_CATEGORIES)}.", ErrorCode.VALIDATION_ERROR)

    old_value = {"category": record.category, "amount": float(record.amount), "frequency": record.frequency}
    update_data = payload.model_dump(exclude_unset=True, exclude={"correction_reason"})
    for field, value in update_data.items():
        setattr(record, field, value)
    if update_data:
        record.is_corrected = True

    db.commit()
    db.refresh(record)

    log_action(
        db, user.id, "USER_CORRECTION", "expense_record",
        old_value=str(old_value), new_value=str(update_data), reason=payload.correction_reason,
    )
    return success_response(
        ExpenseOut.model_validate(record).model_dump(mode="json"),
        message="Expense updated. Financial health and credit-readiness will reflect the correction on next fetch.",
    )


@router.delete("/expenses/{record_id}")
def delete_expense(
    record_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("expenses")),
):
    record = db.query(ExpenseRecord).filter(ExpenseRecord.id == record_id, ExpenseRecord.user_id == user.id).first()
    if record is None:
        raise APIError(404, "Expense record not found.", ErrorCode.DATA_NOT_FOUND)

    db.delete(record)
    db.commit()
    log_action(db, user.id, "DATA_DELETED", "expense_record", old_value=str(record_id))
    return success_response(None, message="Expense record deleted.")


# ---------------------------------------------------------------------------
# Savings
# ---------------------------------------------------------------------------
@router.post("/savings")
def add_savings(
    payload: SavingsCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("savings")),
):
    record = SavingsRecord(user_id=user.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    log_action(db, user.id, "DATA_CREATED", "savings_record", new_value=str(payload.model_dump(mode="json")))
    return success_response(SavingsOut.model_validate(record).model_dump(mode="json"), message="Savings snapshot added.")


@router.get("/savings")
def list_savings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("savings")),
):
    records = (
        db.query(SavingsRecord).filter(SavingsRecord.user_id == user.id).order_by(SavingsRecord.record_date.desc()).all()
    )
    return success_response([SavingsOut.model_validate(r).model_dump(mode="json") for r in records])


@router.delete("/savings/{record_id}")
def delete_savings(
    record_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("savings")),
):
    record = db.query(SavingsRecord).filter(SavingsRecord.id == record_id, SavingsRecord.user_id == user.id).first()
    if record is None:
        raise APIError(404, "Savings record not found.", ErrorCode.DATA_NOT_FOUND)

    db.delete(record)
    db.commit()
    log_action(db, user.id, "DATA_DELETED", "savings_record", old_value=str(record_id))
    return success_response(None, message="Savings record deleted.")


# ---------------------------------------------------------------------------
# Borrowing (optional - PRD Section 9)
# ---------------------------------------------------------------------------
@router.post("/borrowing")
def add_borrowing(
    payload: BorrowingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("borrowing")),
):
    record = BorrowingRecord(user_id=user.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    log_action(db, user.id, "DATA_CREATED", "borrowing_record", new_value=str(payload.model_dump(mode="json")))
    return success_response(BorrowingOut.model_validate(record).model_dump(mode="json"), message="Borrowing info added.")


@router.get("/borrowing")
def list_borrowing(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("borrowing")),
):
    records = (
        db.query(BorrowingRecord)
        .filter(BorrowingRecord.user_id == user.id)
        .order_by(BorrowingRecord.record_date.desc())
        .all()
    )
    return success_response([BorrowingOut.model_validate(r).model_dump(mode="json") for r in records])


@router.delete("/borrowing/{record_id}")
def delete_borrowing(
    record_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("borrowing")),
):
    record = db.query(BorrowingRecord).filter(BorrowingRecord.id == record_id, BorrowingRecord.user_id == user.id).first()
    if record is None:
        raise APIError(404, "Borrowing record not found.", ErrorCode.DATA_NOT_FOUND)

    db.delete(record)
    db.commit()
    log_action(db, user.id, "DATA_DELETED", "borrowing_record", old_value=str(record_id))
    return success_response(None, message="Borrowing record deleted.")
