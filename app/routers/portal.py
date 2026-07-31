"""
SMART BIN LTD - PUBLIC PORTAL ROUTER
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import Depends
from app.database import get_db
from app.models import House, Phase, Estate, Resident, Bill, Payment
from app.schemas import PortalStatement, PortalAccount, PortalSummary
from app.config import company_config

router = APIRouter(prefix="/api/portal", tags=["portal"])

@router.get("/statement", response_model=PortalStatement)
def get_statement(account_number: str, db: Session = Depends(get_db)):
    house = db.query(House).filter(House.account_number == account_number).first()
    if not house:
        raise HTTPException(status_code=404, detail="Account not found")

    phase = db.query(Phase).filter(Phase.id == house.phase_id).first()
    estate = db.query(Estate).filter(Estate.id == phase.estate_id).first() if phase else None

    resident = db.query(Resident).filter(
        Resident.house_id == house.id,
        Resident.is_primary == True
    ).first()

    bills = db.query(Bill).filter(Bill.house_id == house.id).order_by(Bill.created_at.desc()).all()
    payments = db.query(Payment).filter(Payment.house_id == house.id).order_by(Payment.paid_at.desc()).all()

    total_billed = sum(b.amount for b in bills)
    total_paid = sum(p.amount for p in payments)
    balance = total_billed - total_paid

    has_overdue = any(
        b.due_date < func.curdate() and b.status in ["pending", "partial"]
        for b in bills
    )
    if balance <= 0:
        status = "paid"
    elif has_overdue:
        status = "overdue"
    else:
        status = "pending"

    account = PortalAccount(
        account_number=house.account_number,
        house_number=house.house_number,
        phase=phase.phase_number if phase else 0,
        estate=estate.name if estate else "",
        resident_name=resident.full_name if resident else None,
        phone=resident.phone_number if resident else None
    )

    summary = PortalSummary(
        total_billed=total_billed,
        total_paid=total_paid,
        balance=balance,
        status=status
    )

    from app.schemas import BillOut, PaymentOut
    return PortalStatement(
        account=account,
        summary=summary,
        bills=[BillOut.model_validate(b) for b in bills],
        payments=[PaymentOut.model_validate(p) for p in payments],
        payment_instructions=company_config.get_payment_instructions(account_number, float(balance))
    )

@router.get("/payments")
def get_payments(account_number: str, db: Session = Depends(get_db)):
    house = db.query(House).filter(House.account_number == account_number).first()
    if not house:
        raise HTTPException(status_code=404, detail="Account not found")

    payments = db.query(Payment).filter(Payment.house_id == house.id).order_by(Payment.paid_at.desc()).all()
    return {"account_number": account_number, "payments": payments}
