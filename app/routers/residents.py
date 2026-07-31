"""
==============================================================================
SMART BIN LTD - RESIDENTS ROUTER
==============================================================================
Replaces: src/routes/residents.js

ENDPOINTS:
  GET  /api/residents/house/{house_id}  → List residents of a house
  POST /api/residents/                  → Add resident to house
  PUT  /api/residents/{resident_id}     → Update resident

BUSINESS LOGIC:
- One house can have multiple residents, but only ONE is_primary
- Primary resident receives all SMS notifications
- phone_number must be in format 2547XXXXXXXX (Africa's Talking requirement)
- This is "Faith. E" from the SMS — the person who pays the bill
==============================================================================
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Resident
from app.schemas import ResidentCreate, ResidentUpdate, ResidentOut
from app.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/residents", tags=["residents"])


@router.get("/house/{house_id}", response_model=list[ResidentOut])
def list_by_house(house_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """List all residents of a house, primary first."""
    return db.query(Resident).filter(Resident.house_id == house_id)\
        .order_by(Resident.is_primary.desc(), Resident.created_at).all()


@router.post("/", response_model=ResidentOut)
def create_resident(req: ResidentCreate, db: Session = Depends(get_db),
                    user=Depends(require_role("super_admin", "admin", "clerk"))):
    """
    Add a resident to a house.
    Example: Faith. E, phone 254712345678, house 348/4
    """
    r = Resident(id=str(uuid.uuid4()), **req.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.put("/{resident_id}", response_model=ResidentOut)
def update_resident(resident_id: str, req: ResidentUpdate, db: Session = Depends(get_db),
                    user=Depends(require_role("super_admin", "admin", "clerk"))):
    """Update resident details."""
    r = db.query(Resident).filter(Resident.id == resident_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Resident not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return r
