"""
==============================================================================
SMART BIN LTD - HOUSES ROUTER
==============================================================================
ENDPOINTS:
  GET  /api/houses/phase/{phase_id}    → List houses in a phase
  GET  /api/houses/by-account          → Get house by account number (query param)
  POST /api/houses/                    → Create house (auto-generates account_number)
  PUT  /api/houses/{house_id}          → Update house

TRIGGER MAGIC:
  account_number = CONCAT(house_number, '/', phase_number)
  Example: house_number="348", phase=4 → account_number="348/4"
==============================================================================
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import House, Phase, Estate, Resident
from app.schemas import HouseCreate, HouseUpdate, HouseOut
from app.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/houses", tags=["houses"])


@router.get("/phase/{phase_id}", response_model=list[HouseOut])
def list_by_phase(phase_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    results = db.query(
        House, Phase.phase_number, Estate.name.label("estate_name")
    ).join(Phase, House.phase_id == Phase.id)\
     .join(Estate, Phase.estate_id == Estate.id)\
     .filter(House.phase_id == phase_id, Estate.company_id == user.company_id)\
     .order_by(House.house_number)\
     .all()
    
    out = []
    for h, pnum, ename in results:
        d = HouseOut.model_validate(h)
        d.phase_number = pnum
        d.estate_name = ename
        out.append(d)
    return out


@router.get("/by-account", response_model=HouseOut)
def get_by_account(account_number: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    Look up a house by its account number (e.g., "348/4").
    Query parameter format: /api/houses/by-account?account_number=348/4
    This is what M-PESA validation URL uses to verify payments.
    """
    row = db.query(
        House, Phase.phase_number, Estate.name.label("estate_name"),
        Resident.full_name.label("resident_name"), Resident.phone_number.label("resident_phone")
    ).join(Phase, House.phase_id == Phase.id)\
     .join(Estate, Phase.estate_id == Estate.id)\
     .outerjoin(Resident, (Resident.house_id == House.id) & (Resident.is_primary == True))\
     .filter(House.account_number == account_number, Estate.company_id == user.company_id)\
     .first()
    
    if not row:
        raise HTTPException(status_code=404, detail="House not found")
    
    h, pnum, ename, rname, rphone = row
    d = HouseOut.model_validate(h)
    d.phase_number = pnum
    d.estate_name = ename
    d.resident_name = rname
    d.resident_phone = rphone
    return d


@router.post("/", response_model=HouseOut)
def create_house(req: HouseCreate, db: Session = Depends(get_db),
                 user=Depends(require_role("super_admin", "admin", "clerk"))):
    house = House(
        id=str(uuid.uuid4()),
        **req.model_dump()
    )
    db.add(house)
    db.commit()
    db.refresh(house)
    return house


@router.put("/{house_id}", response_model=HouseOut)
def update_house(house_id: str, req: HouseUpdate, db: Session = Depends(get_db),
                 user=Depends(require_role("super_admin", "admin", "clerk"))):
    house = db.query(House).filter(House.id == house_id).first()
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(house, field, value)
    
    db.commit()
    db.refresh(house)
    return house
