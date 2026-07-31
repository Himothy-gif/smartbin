"""
==============================================================================
SMART BIN LTD - PYDANTIC SCHEMAS (Request/Response Validation)
==============================================================================
Replaces: Joi validation from src/middleware/validation.js

WHAT IS PYDANTIC?
Pydantic is Python's data validation library. It ensures that:
- "email" field actually contains an email address
- "amount" is a positive number
- "phone_number" matches the format 2547XXXXXXXX
- Required fields are present before the endpoint runs

WHY NOT JUST DICTS?
Without validation, a user could send:
    {"email": "not-an-email", "amount": -500}
    
And your code would crash mid-execution. Pydantic catches this BEFORE
the endpoint function even runs, returning a clean 422 error.

TWO TYPES OF SCHEMAS:
1. Request schemas (ending in Create/Update/Request) — what the CLIENT sends
2. Response schemas (ending in Out) — what the SERVER returns

BaseModel vs BaseModel with from_attributes=True:
- from_attributes=True means Pydantic can read SQLAlchemy objects directly
- Without it, you'd have to manually convert every field
==============================================================================
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
import re


# ==============================================================================
# AUTH SCHEMAS
# ==============================================================================
class LoginRequest(BaseModel):
    """
    What the client sends when logging in.
    email: must be a valid email format
    password: minimum 6 characters
    """
    email: EmailStr
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    """
    What the server returns after successful login.
    token: JWT string to be stored in localStorage/cookies
    user: basic info about the logged-in user
    """
    token: str
    user: dict


class UserOut(BaseModel):
    """
    User profile returned by /api/auth/me
    """
    id: str
    email: str
    full_name: str
    role: str
    company_id: str
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# COMPANY SCHEMAS
# ==============================================================================
class CompanyOut(BaseModel):
    id: str
    name: str
    paybill_number: str
    contact_phone: Optional[str]
    contact_email: Optional[str]
    address: Optional[str]
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# ESTATE SCHEMAS
# ==============================================================================
class EstateCreate(BaseModel):
    """
    Admin sends this to create a new estate.
    Example: {"name": "GAKINDU COURT", "location": "Utawala, Nairobi", "total_phases": 4}
    """
    name: str = Field(..., min_length=2, max_length=255)
    location: Optional[str] = Field(None, max_length=500)
    total_phases: int = Field(default=1, ge=1)  # ge=1 means "greater than or equal to 1"


class EstateUpdate(BaseModel):
    """
    Partial update — all fields are optional.
    Only send the fields you want to change.
    """
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    location: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, pattern="^(active|inactive|suspended)$")


class PhaseOut(BaseModel):
    id: str
    estate_id: str
    phase_number: int
    phase_name: Optional[str]
    total_houses: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class EstateOut(BaseModel):
    id: str
    company_id: str
    name: str
    location: Optional[str]
    total_phases: int
    total_houses: int
    status: str
    created_at: datetime
    updated_at: datetime
    phases: Optional[List[PhaseOut]] = None  # Nested phases, populated by endpoint
    
    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# HOUSE SCHEMAS
# ==============================================================================
class HouseCreate(BaseModel):
    phase_id: str
    house_number: str = Field(..., max_length=50)
    gps_coordinates: Optional[str] = Field(None, max_length=100)
    bin_count: int = Field(default=1, ge=0)


class HouseUpdate(BaseModel):
    house_number: Optional[str] = Field(None, max_length=50)
    gps_coordinates: Optional[str] = Field(None, max_length=100)
    bin_count: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(active|inactive|suspended|vacant)$")


class HouseOut(BaseModel):
    """
    Response includes JOINed data from other tables.
    phase_number, estate_name, resident_name are added by the endpoint,
    not stored directly in the houses table.
    """
    id: str
    phase_id: str
    house_number: str
    account_number: str
    gps_coordinates: Optional[str]
    bin_count: int
    status: str
    created_at: datetime
    updated_at: datetime
    phase_number: Optional[int] = None
    estate_name: Optional[str] = None
    resident_name: Optional[str] = None
    resident_phone: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# RESIDENT SCHEMAS
# ==============================================================================
class ResidentCreate(BaseModel):
    house_id: str
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: str = Field(..., max_length=20)
    email: Optional[EmailStr] = None
    id_number: Optional[str] = Field(None, max_length=50)
    is_primary: bool = True
    
    @field_validator("phone_number")
    def validate_phone(v, info):
        """
        Custom validator: ensures phone is in international format.
        Accepts: 2547XXXXXXXX or +2547XXXXXXXX
        Rejects: 07XXXXXXXX (missing country code)
        """
        clean = v.replace("+", "")
        if not re.match(r"^254[0-9]{9}$", clean):
            raise ValueError("Phone must be in format 2547XXXXXXXX (country code required)")
        return clean


class ResidentUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    id_number: Optional[str] = Field(None, max_length=50)
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


class ResidentOut(BaseModel):
    id: str
    house_id: str
    full_name: str
    phone_number: str
    email: Optional[str]
    id_number: Optional[str]
    is_primary: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# BILL SCHEMAS
# ==============================================================================
class BillCreate(BaseModel):
    house_id: str
    amount: Decimal = Field(..., gt=0)  # gt=0 = must be positive
    bill_period: str = Field(..., max_length=50)
    due_date: date
    description: Optional[str] = Field(None, max_length=500)


class BillBulkCreate(BaseModel):
    """
    Create bills for ALL houses in an estate or phase at once.
    estate_id OR phase_id must be provided (not both required).
    """
    estate_id: Optional[str] = None
    phase_id: Optional[str] = None
    amount: Decimal = Field(..., gt=0)
    bill_period: str = Field(..., max_length=50)
    due_date: date
    description: Optional[str] = Field(None, max_length=500)


class BillOut(BaseModel):
    id: str
    house_id: str
    bill_period: str
    amount: Decimal
    amount_paid: Decimal
    balance: Decimal
    due_date: date
    status: str
    description: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    # JOINed fields added by endpoint
    account_number: Optional[str] = None
    house_number: Optional[str] = None
    phase_number: Optional[int] = None
    estate_name: Optional[str] = None
    resident_name: Optional[str] = None
    phone_number: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class BillSummary(BaseModel):
    """
    Dashboard summary: how many overdue bills, total amount, affected houses.
    """
    total_overdue: int
    total_amount: Decimal
    affected_houses: int


# ==============================================================================
# PAYMENT SCHEMAS
# ==============================================================================
class PaymentCreate(BaseModel):
    house_id: str
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field(default="cash", pattern="^(mpesa|cash|bank_transfer|other)$")
    payment_reference: Optional[str] = Field(None, max_length=255)
    bill_id: Optional[str] = None


class MpesaValidationRequest(BaseModel):
    """
    What Safaricom sends to our Validation URL BEFORE taking money.
    We check if the account exists and is active. If not, we reject
    the payment and Safaricom refunds the user immediately.
    """
    BillRefNumber: str      # The account number (e.g., "348/4")
    TransAmount: str        # Amount as string (Safaricom sends strings)
    MSISDN: str             # Phone number that is paying
    TransactionType: Optional[str] = None
    TransID: Optional[str] = None
    TransTime: Optional[str] = None
    BusinessShortCode: Optional[str] = None
    InvoiceNumber: Optional[str] = None
    FirstName: Optional[str] = None
    MiddleName: Optional[str] = None
    LastName: Optional[str] = None
    OrgAccountBalance: Optional[str] = None


class MpesaConfirmationRequest(BaseModel):
    """
    What Safaricom sends to our Confirmation URL AFTER money is taken.
    We record the payment, update the bill balance (trigger), and send SMS.
    """
    BillRefNumber: str
    TransAmount: str
    TransID: str            # M-PESA transaction code (e.g., "QKJ8ABC123")
    MSISDN: str
    TransTime: Optional[str] = None


class PaymentOut(BaseModel):
    id: str
    bill_id: Optional[str]
    house_id: str
    amount: Decimal
    mpesa_code: Optional[str]
    mpesa_phone: Optional[str]
    payment_method: str
    payment_reference: Optional[str]
    status: str
    paid_at: datetime
    created_at: datetime
    bill_period: Optional[str] = None  # JOINed from bills table
    
    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# COLLECTION SCHEMAS
# ==============================================================================
class CollectionSchedule(BaseModel):
    """
    Admin sends this to schedule collections for multiple houses.
    house_ids = array of house UUIDs
    scheduled_date = when driver should collect
    driver_id = optional, can assign later
    """
    house_ids: List[str]
    scheduled_date: date
    driver_id: Optional[str] = None


class CollectionComplete(BaseModel):
    """
    Driver sends this when they finish collecting from a house.
    """
    weight_kg: Optional[Decimal] = None
    waste_type: Optional[str] = Field(None, pattern="^(general|recyclable|organic|hazardous)$")
    notes: Optional[str] = None


class CollectionOut(BaseModel):
    id: str
    house_id: str
    driver_id: Optional[str]
    scheduled_date: date
    completed_at: Optional[datetime]
    weight_kg: Optional[Decimal]
    waste_type: str
    status: str
    photo_url: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    # JOINed fields
    account_number: Optional[str] = None
    house_number: Optional[str] = None
    phase_number: Optional[int] = None
    estate_name: Optional[str] = None
    driver_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# DRIVER SCHEMAS
# ==============================================================================
class DriverCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: str = Field(..., max_length=20)
    license_number: Optional[str] = Field(None, max_length=100)
    vehicle_plate: Optional[str] = Field(None, max_length=50)


class DriverUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=20)
    license_number: Optional[str] = Field(None, max_length=100)
    vehicle_plate: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class DriverOut(BaseModel):
    id: str
    company_id: str
    full_name: str
    phone_number: str
    license_number: Optional[str]
    vehicle_plate: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# DASHBOARD SCHEMAS
# ==============================================================================
class DashboardStats(BaseModel):
    today: dict
    monthly: dict
    outstanding: dict
    overdue: dict
    estates: int
    houses: int


class RevenueByEstate(BaseModel):
    name: str
    revenue: Decimal
    transactions: int


class CollectionPerformance(BaseModel):
    date: date
    scheduled: int
    completed: int
    missed: int


class OverdueAging(BaseModel):
    aging_bucket: str
    count: int
    amount: Decimal


# ==============================================================================
# PORTAL SCHEMAS (Public-facing, no auth required)
# ==============================================================================
class PortalAccount(BaseModel):
    account_number: str
    house_number: str
    phase: int
    estate: str
    resident_name: Optional[str]
    phone: Optional[str]


class PortalSummary(BaseModel):
    total_billed: Decimal
    total_paid: Decimal
    balance: Decimal
    status: str


class PortalStatement(BaseModel):
    account: PortalAccount
    summary: PortalSummary
    bills: List[BillOut]
    payments: List[PaymentOut]
    payment_instructions: str


class Pagination(BaseModel):
    """
    Every list endpoint returns this so the frontend knows
    how many pages exist and which page it's on.
    """
    page: int
    limit: int
    total: int
    total_pages: int
