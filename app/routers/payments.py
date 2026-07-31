"""
SMART BIN LTD - PAYMENTS ROUTER (M-PESA + Manual)
"""
import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Payment, Bill, House, Phase, Estate, Resident
from app.schemas import PaymentCreate, MpesaValidationRequest, MpesaConfirmationRequest, PaymentOut
from app.dependencies import get_current_user, require_role
from app.services.mpesa_service import mpesa_service
from app.services.sms_service import sms_service
from app.config import get_settings

router = APIRouter(prefix="/api/payments", tags=["payments"])
settings = get_settings()

@router.post("/validate")
def mpesa_validate(req: MpesaValidationRequest, db: Session = Depends(get_db)):
    account_number = req.BillRefNumber.strip()
    amount = Decimal(req.TransAmount)

    house = db.query(House).filter(House.account_number == account_number).first()
    if not house:
        return {"ResultCode": 1, "ResultDesc": f"Account {account_number} not found"}
    if house.status != "active":
        return {"ResultCode": 1, "ResultDesc": f"Account {account_number} is inactive"}

    open_bills = db.query(Bill).filter(
        Bill.house_id == house.id,
        Bill.status.in_(["pending", "partial", "overdue"])
    ).all()

    if not open_bills:
        return {"ResultCode": 1, "ResultDesc": f"No open bills for account {account_number}"}

    total_due = sum(b.balance for b in open_bills)
    if amount > total_due * Decimal("1.5"):
        return {"ResultCode": 1, "ResultDesc": f"Amount {amount} exceeds total due {total_due}"}

    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@router.post("/confirm")
def mpesa_confirm(req: MpesaConfirmationRequest, db: Session = Depends(get_db)):
    account_number = req.BillRefNumber.strip()
    amount = Decimal(req.TransAmount)
    mpesa_code = req.TransID
    phone = req.MSISDN

    house = db.query(House).filter(House.account_number == account_number).first()
    if not house:
        return {"ResultCode": 1, "ResultDesc": "Account not found"}

    bill = db.query(Bill).filter(
        Bill.house_id == house.id,
        Bill.status.in_(["pending", "partial", "overdue"])
    ).order_by(Bill.due_date.asc()).first()

    bill_id = bill.id if bill else None

    payment = Payment(
        id=str(uuid.uuid4()),
        bill_id=bill_id,
        house_id=house.id,
        amount=amount,
        mpesa_code=mpesa_code,
        mpesa_phone=phone,
        payment_method="mpesa",
        status="completed"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if bill:
        db.refresh(bill)
        new_balance = float(bill.balance)
    else:
        new_balance = 0.0

    resident = db.query(Resident).filter(
        Resident.house_id == house.id,
        Resident.is_primary == True,
        Resident.is_active == True
    ).first()

    if resident:
        sms_service.send_payment_confirmation(
            phone=resident.phone_number,
            name=resident.full_name,
            account_number=house.account_number,
            amount=float(amount),
            mpesa_code=mpesa_code,
            balance=new_balance,
            house_id=house.id,
            db=db
        )

    return {"ResultCode": 0, "ResultDesc": "Success"}

@router.post("/register-urls")
def register_mpesa_urls(user=Depends(require_role("super_admin", "admin"))):
    validation_url = settings.mpesa_validation_url
    confirmation_url = settings.mpesa_confirmation_url

    if not validation_url or not confirmation_url:
        raise HTTPException(
            status_code=400,
            detail="MPESA_VALIDATION_URL and MPESA_CONFIRMATION_URL must be set in .env"
        )

    result = mpesa_service.register_urls(validation_url, confirmation_url)
    return {"message": "URLs registered", "result": result}

@router.post("/manual", response_model=PaymentOut)
def create_manual_payment(
    req: PaymentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("super_admin", "admin", "clerk"))
):
    payment = Payment(
        id=str(uuid.uuid4()),
        bill_id=req.bill_id,
        house_id=req.house_id,
        amount=req.amount,
        payment_method=req.payment_method,
        payment_reference=req.payment_reference,
        status="completed"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment

@router.get("/")
def list_payments(
    house_id: str = None,
    method: str = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    offset = (page - 1) * limit

    q = db.query(
        Payment, Bill.bill_period.label("bill_period")
    ).outerjoin(Bill, Payment.bill_id == Bill.id)\
     .join(House, Payment.house_id == House.id)\
     .join(Phase, House.phase_id == Phase.id)\
     .join(Estate, Phase.estate_id == Estate.id)\
     .filter(Estate.company_id == user.company_id)

    if house_id:
        q = q.filter(Payment.house_id == house_id)
    if method:
        q = q.filter(Payment.payment_method == method)

    total = q.count()
    rows = q.order_by(Payment.paid_at.desc()).offset(offset).limit(limit).all()

    payments = []
    for p, period in rows:
        d = PaymentOut.model_validate(p)
        d.bill_period = period
        payments.append(d)

    from app.schemas import Pagination
    return {
        "payments": payments,
        "pagination": Pagination(
            page=page, limit=limit, total=total,
            total_pages=(total + limit - 1) // limit
        )
    }

@router.get("/house/{house_id}", response_model=list[PaymentOut])
def payments_by_house(house_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Payment).filter(Payment.house_id == house_id).order_by(Payment.paid_at.desc()).all()
