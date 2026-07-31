"""
==============================================================================
SMART BIN LTD - ESTATES ROUTER
==============================================================================
Replaces: src/routes/estates.js

ENDPOINTS:
  GET  /api/estates/          → List all estates for logged-in company
  GET  /api/estates/{id}      → Get single estate with its phases
  POST /api/estates/          → Create new estate (admin only)
  PUT  /api/estates/{id}      → Update estate (admin only)
  DELETE /api/estates/{id}    → Delete estate (super_admin only)

BUSINESS LOGIC:
- Every estate belongs to ONE company (multi-tenant isolation)
- Creating an estate auto-creates its phases (e.g., 4 phases = Phase 1-4)
- Only super_admin and admin can create/modify
- Clerks can only view
==============================================================================
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Estate, Phase
from app.schemas import EstateCreate, EstateUpdate, EstateOut, PhaseOut
from app.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/estates", tags=["estates"])


@router.get("/", response_model=list[EstateOut])
def list_estates(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    List all estates for the logged-in user's company.
    Automatically filters by company_id — clerks can't see other companies' data.
    """
    return db.query(Estate).filter(
        Estate.company_id == user.company_id
    ).order_by(Estate.created_at.desc()).all()


@router.get("/{estate_id}", response_model=EstateOut)
def get_estate(estate_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    Get a single estate with all its phases nested inside.
    Returns 404 if estate doesn't exist or belongs to another company.
    """
    estate = db.query(Estate).filter(
        Estate.id == estate_id,
        Estate.company_id == user.company_id
    ).first()
    
    if not estate:
        raise HTTPException(status_code=404, detail="Estate not found")
    
    # Load phases manually and attach to response
    phases = db.query(Phase).filter(Phase.estate_id == estate_id).order_by(Phase.phase_number).all()
    estate.phases = [PhaseOut.model_validate(p) for p in phases]
    return estate


@router.post("/", response_model=EstateOut)
def create_estate(req: EstateCreate, db: Session = Depends(get_db),
                  user=Depends(require_role("super_admin", "admin"))):
    """
    Create a new estate and auto-generate its phases.
    
    Example request:
    {
        "name": "GAKINDU COURT",
        "location": "Utawala, Nairobi",
        "total_phases": 4
    }
    
    This creates:
    - 1 estate row
    - 4 phase rows (Phase 1, Phase 2, Phase 3, Phase 4)
    """
    # Create the estate
    estate = Estate(
        id=str(uuid.uuid4()),
        company_id=user.company_id,
        name=req.name,
        location=req.location,
        total_phases=req.total_phases
    )
    db.add(estate)
    db.commit()
    db.refresh(estate)
    
    # Auto-create phases (1 to total_phases)
    for i in range(1, req.total_phases + 1):
        phase = Phase(
            id=str(uuid.uuid4()),
            estate_id=estate.id,
            phase_number=i,
            phase_name=f"Phase {i}"
        )
        db.add(phase)
    
    db.commit()
    db.refresh(estate)
    return estate


@router.put("/{estate_id}", response_model=EstateOut)
def update_estate(estate_id: str, req: EstateUpdate, db: Session = Depends(get_db),
                  user=Depends(require_role("super_admin", "admin"))):
    """
    Partial update — only send fields you want to change.
    """
    estate = db.query(Estate).filter(
        Estate.id == estate_id,
        Estate.company_id == user.company_id
    ).first()
    
    if not estate:
        raise HTTPException(status_code=404, detail="Estate not found")
    
    # Update only provided fields
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(estate, field, value)
    
    db.commit()
    db.refresh(estate)
    return estate


@router.delete("/{estate_id}")
def delete_estate(estate_id: str, db: Session = Depends(get_db),
                  user=Depends(require_role("super_admin"))):
    """
    Only super_admin can delete estates (dangerous operation).
    Cascade delete removes all phases, houses, residents, bills automatically.
    """
    estate = db.query(Estate).filter(
        Estate.id == estate_id,
        Estate.company_id == user.company_id
    ).first()
    
    if not estate:
        raise HTTPException(status_code=404, detail="Estate not found")
    
    db.delete(estate)
    db.commit()
    return {"message": "Estate deleted successfully"}
