"""
SMART BIN LTD - BILLS ROUTER
"""
import uuid
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Bill, House, Phase, Estate, Resident
from app.schemas import BillCreate, BillBulkCreate, BillOut, BillSummary, Pagination
from app.dependencies import get_current_user, require_role
from app.services.sms_service import sms_service

router = APIRouter(prefix="/api/bills", tags=["bills"])

@router.get("/")
def list_bills(
    status: str = None,
    estate_id: str = None,
    overdue_only: bool = False,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    offset = (page - 1) * limit

    q = db.query(
        Bill, House.account_number, House.house_number, Phase.phase_number,
        Estate.name.label("estate_name"), Resident.full_name.label("resident_name"),
        Resident.phone_number
    ).join(House, Bill.house_id == House.id)\
     .join(Phase, House.phase_id == Phase.id)\
     .join(Estate, Phase.estate_id == Estate.id)\
     .outerjoin(Resident, (Resident.house_id == House.id) & (Resident.is_primary == True))\
     .filter(Estate.company_id == user.company_id)

    if status:
        q = q.filter(Bill.status == status)
    if estate_id:
        q = q.filter(Estate.id == estate_id)
    if overdue_only:
        q = q.filter(Bill.due_date < func.curdate(), Bill.status != "paid")

    total = q.count()
    rows = q.order_by(Bill.created_at.desc()).offset(offset).limit(limit).all()

    bills = []
    for b, acc, hnum, pnum, ename, rname, rphone in rows:
        d = BillOut.model_validate(b)
        d.account_number = acc
        d.house_number = hnum
        d.phase_number = pnum
        d.estate_name = ename
        d.resident_name = rname
        d.phone_number = rphone
        bills.append(d)

    return {
        "bills": bills,
        "pagination": Pagination(
            page=page, limit=limit, total=total,
            total_pages=(total + limit - 1) // limit
        )
    }

@router.get("/house/{house_id}", response_model=list[BillOut])
def bills_by_house(house_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Bill).filter(Bill.house_id == house_id).order_by(Bill.created_at.desc()).all()

@router.post("/", response_model=BillOut)
def create_bill(req: BillCreate, db: Session = Depends(get_db),
                user=Depends(require_role("super_admin", "admin", "clerk"))):
    bill = Bill(
        id=str(uuid.uuid4()),
        house_id=req.house_id,
        amount=req.amount,
        balance=req.amount,
        bill_period=req.bill_period,
        due_date=req.due_date,
        description=req.description,
        created_by=user.id
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill

@router.post("/bulk")
def bulk_create(req: BillBulkCreate, db: Session = Depends(get_db),
                user=Depends(require_role("super_admin", "admin"))):
    q = db.query(House).join(Phase, House.phase_id == Phase.id)\
        .join(Estate, Phase.estate_id == Estate.id)\
        .filter(Estate.company_id == user.company_id, House.status == "active")

    if req.estate_id:
        q = q.filter(Estate.id == req.estate_id)
    if req.phase_id:
        q = q.filter(Phase.id == req.phase_id)

    houses = q.all()
    bills = []
    for h in houses:
        b = Bill(
            id=str(uuid.uuid4()),
            house_id=h.id,
            amount=req.amount,
            balance=req.amount,
            bill_period=req.bill_period,
            due_date=req.due_date,
            description=req.description,
            created_by=user.id
        )
        db.add(b)
        bills.append(b)

    db.commit()
    return {
        "message": f"{len(bills)} bills created successfully",
        "bills_created": len(bills)
    }

@router.get("/summary/overdue", response_model=BillSummary)
def overdue_summary(db: Session = Depends(get_db), user=Depends(get_current_user)):
    result = db.query(
        func.count(Bill.id).label("total_overdue"),
        func.sum(Bill.balance).label("total_amount"),
        func.count(Bill.house_id.distinct()).label("affected_houses")
    ).join(House, Bill.house_id == House.id)\
     .join(Phase, House.phase_id == Phase.id)\
     .join(Estate, Phase.estate_id == Estate.id)\
     .filter(
         Estate.company_id == user.company_id,
         Bill.due_date < func.curdate(),
         Bill.status.in_(["pending", "partial"])
     ).first()

    return BillSummary(
        total_overdue=result.total_overdue or 0,
        total_amount=result.total_amount or Decimal("0.00"),
        affected_houses=result.affected_houses or 0
    )

@router.post("/{bill_id}/send-sms")
def send_bill_sms(bill_id: str, db: Session = Depends(get_db),
                  user=Depends(require_role("super_admin", "admin", "clerk"))):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    house = db.query(House).filter(House.id == bill.house_id).first()
    resident = db.query(Resident).filter(
        Resident.house_id == house.id,
        Resident.is_primary == True,
        Resident.is_active == True
    ).first()

    if not resident:
        raise HTTPException(status_code=404, detail="No primary resident found for this house")

    estate = db.query(Estate).join(Phase, Phase.estate_id == Estate.id)\
        .join(House, House.phase_id == Phase.id)\
        .filter(House.id == house.id).first()

    result = sms_service.send_bill_sms(
        phone=resident.phone_number,
        name=resident.full_name,
        account_number=house.account_number,
        amount=float(bill.balance),
        period=bill.bill_period,
        due_date=bill.due_date.strftime("%d %b %Y"),
        estate_name=estate.name if estate else "",
        house_id=house.id,
        db=db
    )

    return {"message": "SMS sent", "result": result}
