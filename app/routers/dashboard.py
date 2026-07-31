"""
SMART BIN LTD - DASHBOARD ROUTER
"""
from datetime import date, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.database import get_db
from app.models import Bill, Payment, Collection, Estate, House, Phase, Resident, SMSLog
from app.schemas import DashboardStats, RevenueByEstate, CollectionPerformance, OverdueAging
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db), user=Depends(get_current_user)):
    today = date.today()
    first_of_month = today.replace(day=1)

    today_collections = db.query(func.count(Collection.id)).join(House, Collection.house_id == House.id)\
        .join(Phase, House.phase_id == Phase.id).join(Estate, Phase.estate_id == Estate.id)\
        .filter(Estate.company_id == user.company_id, Collection.scheduled_date == today).scalar() or 0

    today_completed = db.query(func.count(Collection.id)).join(House, Collection.house_id == House.id)\
        .join(Phase, House.phase_id == Phase.id).join(Estate, Phase.estate_id == Estate.id)\
        .filter(Estate.company_id == user.company_id, Collection.scheduled_date == today, Collection.status == "completed").scalar() or 0

    monthly_revenue = db.query(func.sum(Payment.amount)).join(House, Payment.house_id == House.id)\
        .join(Phase, House.phase_id == Phase.id).join(Estate, Phase.estate_id == Estate.id)\
        .filter(Estate.company_id == user.company_id, func.date(Payment.paid_at) >= first_of_month).scalar() or Decimal("0.00")

    monthly_transactions = db.query(func.count(Payment.id)).join(House, Payment.house_id == House.id)\
        .join(Phase, House.phase_id == Phase.id).join(Estate, Phase.estate_id == Estate.id)\
        .filter(Estate.company_id == user.company_id, func.date(Payment.paid_at) >= first_of_month).scalar() or 0

    outstanding = db.query(func.sum(Bill.balance)).join(House, Bill.house_id == House.id)\
        .join(Phase, House.phase_id == Phase.id).join(Estate, Phase.estate_id == Estate.id)\
        .filter(Estate.company_id == user.company_id, Bill.status.in_(["pending", "partial", "overdue"])).scalar() or Decimal("0.00")

    outstanding_count = db.query(func.count(Bill.id)).join(House, Bill.house_id == House.id)\
        .join(Phase, House.phase_id == Phase.id).join(Estate, Phase.estate_id == Estate.id)\
        .filter(Estate.company_id == user.company_id, Bill.status.in_(["pending", "partial", "overdue"])).scalar() or 0

    overdue = db.query(func.sum(Bill.balance)).join(House, Bill.house_id == House.id)\
        .join(Phase, House.phase_id == Phase.id).join(Estate, Phase.estate_id == Estate.id)\
        .filter(Estate.company_id == user.company_id, Bill.due_date < today, Bill.status.in_(["pending", "partial"])).scalar() or Decimal("0.00")

    overdue_count = db.query(func.count(Bill.id)).join(House, Bill.house_id == House.id)\
        .join(Phase, House.phase_id == Phase.id).join(Estate, Phase.estate_id == Estate.id)\
        .filter(Estate.company_id == user.company_id, Bill.due_date < today, Bill.status.in_(["pending", "partial"])).scalar() or 0

    estate_count = db.query(func.count(Estate.id)).filter(Estate.company_id == user.company_id).scalar() or 0
    house_count = db.query(func.count(House.id)).join(Phase, House.phase_id == Phase.id)\
        .join(Estate, Phase.estate_id == Estate.id).filter(Estate.company_id == user.company_id).scalar() or 0

    return DashboardStats(
        today={
            "collections_scheduled": today_collections,
            "collections_completed": today_completed,
            "completion_rate": round(today_completed / today_collections * 100, 1) if today_collections > 0 else 0
        },
        monthly={
            "revenue": monthly_revenue,
            "transactions": monthly_transactions
        },
        outstanding={
            "total": outstanding,
            "count": outstanding_count
        },
        overdue={
            "total": overdue,
            "count": overdue_count
        },
        estates=estate_count,
        houses=house_count
    )

@router.get("/revenue-by-estate", response_model=list[RevenueByEstate])
def revenue_by_estate(month: str = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(
        Estate.name,
        func.sum(Payment.amount).label("revenue"),
        func.count(Payment.id).label("transactions")
    ).join(Phase, Phase.estate_id == Estate.id)\
     .join(House, House.phase_id == Phase.id)\
     .join(Payment, Payment.house_id == House.id)\
     .filter(Estate.company_id == user.company_id)\
     .group_by(Estate.id)

    if month:
        try:
            year, mon = map(int, month.split("-"))
            q = q.filter(func.year(Payment.paid_at) == year, func.month(Payment.paid_at) == mon)
        except ValueError:
            pass

    results = q.all()
    return [RevenueByEstate(name=r.name, revenue=r.revenue or Decimal("0.00"), transactions=r.transactions) for r in results]

@router.get("/collection-performance", response_model=list[CollectionPerformance])
def collection_performance(days: int = 30, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from_date = date.today() - timedelta(days=days)

    results = db.query(
        Collection.scheduled_date.label("date"),
        func.count(Collection.id).filter(Collection.status.in_(["scheduled", "completed", "missed"])).label("scheduled"),
        func.count(Collection.id).filter(Collection.status == "completed").label("completed"),
        func.count(Collection.id).filter(Collection.status == "missed").label("missed")
    ).join(House, Collection.house_id == House.id)\
     .join(Phase, House.phase_id == Phase.id)\
     .join(Estate, Phase.estate_id == Estate.id)\
     .filter(Estate.company_id == user.company_id, Collection.scheduled_date >= from_date)\
     .group_by(Collection.scheduled_date).order_by(Collection.scheduled_date.desc()).all()

    return [CollectionPerformance(date=r.date, scheduled=r.scheduled, completed=r.completed, missed=r.missed) for r in results]

@router.get("/overdue-aging", response_model=list[OverdueAging])
def overdue_aging(db: Session = Depends(get_db), user=Depends(get_current_user)):
    today = date.today()

    results = db.query(
        case(
            (Bill.due_date >= today - timedelta(days=30), "1-30 days"),
            (Bill.due_date >= today - timedelta(days=60), "31-60 days"),
            (Bill.due_date >= today - timedelta(days=90), "61-90 days"),
            else_="90+ days"
        ).label("aging_bucket"),
        func.count(Bill.id).label("count"),
        func.sum(Bill.balance).label("amount")
    ).join(House, Bill.house_id == House.id)\
     .join(Phase, House.phase_id == Phase.id)\
     .join(Estate, Phase.estate_id == Estate.id)\
     .filter(Estate.company_id == user.company_id, Bill.due_date < today, Bill.status.in_(["pending", "partial"]))\
     .group_by("aging_bucket").all()

    return [OverdueAging(aging_bucket=r.aging_bucket, count=r.count, amount=r.amount or Decimal("0.00")) for r in results]

@router.get("/recent-activity")
def recent_activity(db: Session = Depends(get_db), user=Depends(get_current_user)):
    payments = db.query(
        Payment, House.account_number, Resident.full_name.label("resident_name")
    ).join(House, Payment.house_id == House.id)\
     .outerjoin(Resident, (Resident.house_id == House.id) & (Resident.is_primary == True))\
     .join(Phase, House.phase_id == Phase.id)\
     .join(Estate, Phase.estate_id == Estate.id)\
     .filter(Estate.company_id == user.company_id)\
     .order_by(Payment.paid_at.desc()).limit(5).all()

    recent_payments = [{
        "type": "payment",
        "account_number": p[1],
        "resident_name": p[2],
        "amount": float(p[0].amount),
        "method": p[0].payment_method,
        "time": p[0].paid_at.isoformat()
    } for p in payments]

    collections = db.query(
        Collection, House.account_number
    ).join(House, Collection.house_id == House.id)\
     .join(Phase, House.phase_id == Phase.id)\
     .join(Estate, Phase.estate_id == Estate.id)\
     .filter(Estate.company_id == user.company_id)\
     .order_by(Collection.created_at.desc()).limit(5).all()

    recent_collections = [{
        "type": "collection",
        "account_number": c[1],
        "status": c[0].status,
        "date": c[0].scheduled_date.isoformat(),
        "time": c[0].created_at.isoformat()
    } for c in collections]

    return {"payments": recent_payments, "collections": recent_collections}
