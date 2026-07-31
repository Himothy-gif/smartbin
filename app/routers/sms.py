"""
SMART BIN LTD - SMS ROUTER
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import SMSLog, House, Phase, Estate, Resident, Bill
from app.dependencies import get_current_user, require_role
from app.services.sms_service import sms_service
from app.schemas import Pagination

router = APIRouter(prefix="/api/sms", tags=["sms"])

@router.post("/send")
def send_sms(
    phone: str,
    message: str,
    sms_type: str = "general",
    house_id: str = None,
    db: Session = Depends(get_db),
    user=Depends(require_role("super_admin", "admin", "clerk"))
):
    result = sms_service.send(phone, message, sms_type, house_id, db)
    return {"message": "SMS processed", "result": result}

@router.post("/bulk-reminder")
def send_bulk_reminders(
    days_overdue: int = 7,
    db: Session = Depends(get_db),
    user=Depends(require_role("super_admin", "admin"))
):
    from datetime import date, timedelta
    cutoff = date.today() - timedelta(days=days_overdue)

    rows = db.query(
        Bill, House, Resident, Estate.name.label("estate_name")
    ).join(House, Bill.house_id == House.id)\
     .join(Phase, House.phase_id == Phase.id)\
     .join(Estate, Phase.estate_id == Estate.id)\
     .outerjoin(Resident, (Resident.house_id == House.id) & (Resident.is_primary == True))\
     .filter(
         Estate.company_id == user.company_id,
         Bill.due_date <= cutoff,
         Bill.status.in_(["pending", "partial", "overdue"]),
         Resident.phone_number.isnot(None)
     ).all()

    sent_count = 0
    failed_count = 0

    for bill, house, resident, estate_name in rows:
        if not resident:
            continue

        days = (date.today() - bill.due_date).days
        result = sms_service.send_overdue_reminder(
            phone=resident.phone_number,
            name=resident.full_name,
            account_number=house.account_number,
            amount=float(bill.balance),
            days_overdue=days,
            house_id=house.id,
            db=db
        )

        if result.get("status") in ("sent", "Success"):
            sent_count += 1
        else:
            failed_count += 1

    return {
        "message": "Bulk reminders sent",
        "sent": sent_count,
        "failed": failed_count,
        "total_overdue": len(rows)
    }

@router.get("/logs")
def sms_logs(
    status: str = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    offset = (page - 1) * limit

    q = db.query(SMSLog).join(House, SMSLog.house_id == House.id, isouter=True)\
        .join(Phase, House.phase_id == Phase.id, isouter=True)\
        .join(Estate, Phase.estate_id == Estate.id, isouter=True)\
        .filter(Estate.company_id == user.company_id)

    if status:
        q = q.filter(SMSLog.status == status)

    total = q.count()
    logs = q.order_by(SMSLog.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "logs": logs,
        "pagination": Pagination(
            page=page, limit=limit, total=total,
            total_pages=(total + limit - 1) // limit
        )
    }

@router.get("/stats")
def sms_stats(db: Session = Depends(get_db), user=Depends(get_current_user)):
    stats = db.query(
        SMSLog.status,
        func.count(SMSLog.id).label("count")
    ).join(House, SMSLog.house_id == House.id, isouter=True)\
     .join(Phase, House.phase_id == Phase.id, isouter=True)\
     .join(Estate, Phase.estate_id == Estate.id, isouter=True)\
     .filter(Estate.company_id == user.company_id)\
     .group_by(SMSLog.status).all()

    return {
        "stats": [{"status": s.status, "count": s.count} for s in stats],
        "total": sum(s.count for s in stats)
    }
