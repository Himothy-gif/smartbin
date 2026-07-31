"""
==============================================================================
SMART BIN LTD - SQLALCHEMY ORM MODELS
==============================================================================
Replaces: ALL raw PostgreSQL queries from the Node.js version.

WHAT IS AN ORM?
ORM = Object-Relational Mapping. Instead of writing SQL like:
    SELECT * FROM houses WHERE account_number = '348/4';
    
We write Python:
    db.query(House).filter(House.account_number == '348/4').first()

SQLAlchemy converts Python to SQL automatically. This prevents:
- SQL injection (user input is parameterized automatically)
- Syntax errors (Python catches typos before hitting the database)
- Connection leaks (sessions are managed by the engine we built)

HOW THIS FILE IS ORGANIZED:
Each class = one MySQL table. The class name is singular (House), 
the table name is plural (houses). Each attribute = one column.

RELATIONSHIPS:
- relationship() connects tables. Example: Estate.phases means
  "one estate has many phases." SQLAlchemy auto-joins them.
- back_populates means "when I look from the other side, I see this."
  Example: Phase.estate and Estate.phases point to each other.

UUID GENERATION:
MySQL's UUID() function runs on the server. But SQLAlchemy models
generate UUIDs in Python BEFORE inserting. This lets us use the ID
immediately (e.g., create a house, then create a bill for it in
the same transaction without waiting for MySQL to return the ID).
==============================================================================
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text, DECIMAL,
    ForeignKey, Enum, JSON, func
)
from sqlalchemy.orm import relationship
from app.database import Base


# ==============================================================================
# HELPER: Generate UUID v4 (random 36-char string like 'a1b2c3d4-e5f6-...')
# ==============================================================================
def generate_uuid():
    return str(uuid.uuid4())


# ==============================================================================
# TABLE 1: COMPANIES
# ==============================================================================
# PURPOSE: Each client (like Smart Bin Ltd) gets one company row.
#          Multi-tenant: one database can hold multiple companies.
#          All other tables link back to company_id for data isolation.
# ==============================================================================
class Company(Base):
    __tablename__ = "companies"     # MySQL table name
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    paybill_number = Column(String(50), nullable=False)   # M-PESA Paybill
    contact_phone = Column(String(20))
    contact_email = Column(String(255))
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())       # func.now() = CURRENT_TIMESTAMP
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # RELATIONSHIPS: One company has many estates, users, drivers, settings
    estates = relationship("Estate", back_populates="company", cascade="all, delete-orphan")
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    drivers = relationship("Driver", back_populates="company", cascade="all, delete-orphan")
    settings = relationship("Setting", back_populates="company", cascade="all, delete-orphan")
    
    # cascade="all, delete-orphan" means: if company is deleted, delete
    # all its estates, users, drivers, and settings automatically.
    # This prevents orphaned rows (data without a parent company).


# ==============================================================================
# TABLE 2: USERS (Admin Staff)
# ==============================================================================
# PURPOSE: Staff who log into the admin dashboard.
# ROLES:
#   super_admin = full access (create companies, manage everything)
#   admin       = manage one company's estates, bills, drivers
#   clerk       = read-only or limited write (view reports, mark collections)
# ==============================================================================
class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)       # bcrypt hash, never plain text
    role = Column(Enum("super_admin", "admin", "clerk", name="user_role"), default="clerk")
    is_active = Column(Boolean, default=True)               # Soft delete: set False instead of DELETE
    last_login = Column(DateTime)                           # Track when they last accessed
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    company = relationship("Company", back_populates="users")
    bills_created = relationship("Bill", back_populates="creator")
    audit_logs = relationship("AuditLog", back_populates="performer")


# ==============================================================================
# TABLE 3: ESTATES
# ==============================================================================
# PURPOSE: A physical location managed by the company.
#          Example: "GAKINDU COURT", "Greenwood Estate", "Sunset Apartments"
#          Each estate has 1+ phases (courts/blocks within the estate).
# ==============================================================================
class Estate(Base):
    __tablename__ = "estates"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    location = Column(String(500))          # Physical address or GPS description
    total_phases = Column(Integer, default=1)
    total_houses = Column(Integer, default=0)   # Auto-updated by trigger when houses added/deleted
    status = Column(Enum("active", "inactive", "suspended", name="estate_status"), default="active")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    company = relationship("Company", back_populates="estates")
    phases = relationship("Phase", back_populates="estate", cascade="all, delete-orphan")
    routes = relationship("Route", back_populates="estate", cascade="all, delete-orphan")


# ==============================================================================
# TABLE 4: PHASES
# ==============================================================================
# PURPOSE: A subdivision within an estate.
#          Example: Phase 1, Phase 2, Phase 3, Phase 4
#          The phase_number is used in account_number: "348/4" means
#          house 348 in phase 4.
# ==============================================================================
class Phase(Base):
    __tablename__ = "phases"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    estate_id = Column(String(36), ForeignKey("estates.id", ondelete="CASCADE"), nullable=False)
    phase_number = Column(Integer, nullable=False)          # 1, 2, 3, 4...
    phase_name = Column(String(255))                        # Optional friendly name
    total_houses = Column(Integer, default=0)               # Auto-updated by trigger
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    estate = relationship("Estate", back_populates="phases")
    houses = relationship("House", back_populates="phase", cascade="all, delete-orphan")
    
    # UNIQUE CONSTRAINT: (estate_id, phase_number) — no duplicate phase numbers
    # within the same estate. Enforced by MySQL, not shown here but in schema.


# ==============================================================================
# TABLE 5: HOUSES
# ==============================================================================
# PURPOSE: Individual household unit. The core entity of the system.
#          account_number is AUTO-GENERATED by MySQL trigger as "house_number/phase_number"
#          Example: house_number="348", phase=4 → account_number="348/4"
#          
#          This account_number is what residents use when paying via M-PESA Paybill.
# ==============================================================================
class House(Base):
    __tablename__ = "houses"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    phase_id = Column(String(36), ForeignKey("phases.id", ondelete="CASCADE"), nullable=False)
    house_number = Column(String(50), nullable=False)         # "348", "A12", "B5"
    account_number = Column(String(50), nullable=False)       # "348/4" — AUTO by trigger
    gps_coordinates = Column(String(100))                     # "-1.2921,36.8219" for maps
    bin_count = Column(Integer, default=1)                    # How many garbage bins
    status = Column(Enum("active", "inactive", "suspended", "vacant", name="house_status"), default="active")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    phase = relationship("Phase", back_populates="houses")
    residents = relationship("Resident", back_populates="house", cascade="all, delete-orphan")
    bills = relationship("Bill", back_populates="house", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="house", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="house", cascade="all, delete-orphan")
    sms_logs = relationship("SMSLog", back_populates="house")


# ==============================================================================
# TABLE 6: RESIDENTS
# ==============================================================================
# PURPOSE: People living in a house. One house can have multiple residents
#          (e.g., husband and wife both registered), but only ONE is_primary.
#          The primary resident receives all SMS notifications.
#          
#          phone_number format: 2547XXXXXXXX (international, no + sign)
#          This format is required by Africa's Talking SMS API.
# ==============================================================================
class Resident(Base):
    __tablename__ = "residents"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    house_id = Column(String(36), ForeignKey("houses.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=False)         # "254712345678"
    email = Column(String(255))
    id_number = Column(String(50))                          # Kenyan National ID
    password_hash = Column(String(255))                     # For resident portal login (optional)
    is_primary = Column(Boolean, default=True)              # Only primary gets SMS
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    house = relationship("House", back_populates="residents")


# ==============================================================================
# TABLE 7: BILLS
# ==============================================================================
# PURPOSE: Monthly invoice sent to each house.
#          amount = total due for the period
#          amount_paid = sum of all payments (auto-updated by trigger)
#          balance = amount - amount_paid (auto-updated by trigger)
#          status = pending → partial → paid → overdue (auto by cron job)
# ==============================================================================
class Bill(Base):
    __tablename__ = "bills"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    house_id = Column(String(36), ForeignKey("houses.id", ondelete="CASCADE"), nullable=False)
    bill_period = Column(String(50), nullable=False)          # "July 2026", "August 2026"
    amount = Column(DECIMAL(10, 2), nullable=False)         # 400.00
    amount_paid = Column(DECIMAL(10, 2), default=0.00)        # Auto-updated by trigger
    balance = Column(DECIMAL(10, 2), nullable=False)          # Auto-updated by trigger
    due_date = Column(Date, nullable=False)                 # "2026-08-15"
    status = Column(Enum("pending", "paid", "overdue", "partial", "cancelled", name="bill_status"), default="pending")
    description = Column(Text)                                # "Monthly garbage collection fee"
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    house = relationship("House", back_populates="bills")
    creator = relationship("User", back_populates="bills_created")
    payments = relationship("Payment", back_populates="bill")


# ==============================================================================
# TABLE 8: PAYMENTS
# ==============================================================================
# PURPOSE: Every payment recorded — whether M-PESA, cash, or bank transfer.
#          When inserted, MySQL trigger auto-updates the linked bill's balance.
#          
#          mpesa_code = M-PESA transaction ID (e.g., "QKJ8ABC123")
#          mpesa_phone = phone that paid (e.g., "254712345678")
#          payment_method: mpesa | cash | bank_transfer | other
# ==============================================================================
class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    bill_id = Column(String(36), ForeignKey("bills.id", ondelete="SET NULL"))
    house_id = Column(String(36), ForeignKey("houses.id", ondelete="CASCADE"), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    mpesa_code = Column(String(50))                           # "QKJ8ABC123"
    mpesa_phone = Column(String(20))                          # "254712345678"
    payment_method = Column(Enum("mpesa", "cash", "bank_transfer", "other", name="payment_method"), default="mpesa")
    payment_reference = Column(String(255))                 # Bank reference or note
    status = Column(Enum("pending", "completed", "failed", "refunded", name="payment_status"), default="completed")
    paid_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    
    bill = relationship("Bill", back_populates="payments")
    house = relationship("House", back_populates="payments")


# ==============================================================================
# TABLE 9: COLLECTIONS
# ==============================================================================
# PURPOSE: Track when garbage was collected from each house.
#          scheduled_date = when driver should come
#          completed_at = when driver marked it done (timestamp)
#          weight_kg = how much garbage (optional, for analytics)
#          waste_type = general | recyclable | organic | hazardous
#          photo_url = driver uploads photo as proof
# ==============================================================================
class Collection(Base):
    __tablename__ = "collections"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    house_id = Column(String(36), ForeignKey("houses.id", ondelete="CASCADE"), nullable=False)
    driver_id = Column(String(36), ForeignKey("drivers.id", ondelete="SET NULL"))
    scheduled_date = Column(Date, nullable=False)
    completed_at = Column(DateTime)                           # NULL until driver marks done
    weight_kg = Column(DECIMAL(8, 2))
    waste_type = Column(Enum("general", "recyclable", "organic", "hazardous", name="waste_type"), default="general")
    status = Column(Enum("scheduled", "completed", "missed", "cancelled", "skipped", name="collection_status"), default="scheduled")
    photo_url = Column(String(500))                           # S3 or local path to photo
    notes = Column(Text)                                      # "Gate was locked", "Bin missing"
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    house = relationship("House", back_populates="collections")
    driver = relationship("Driver", back_populates="collections")


# ==============================================================================
# TABLE 10: DRIVERS
# ==============================================================================
# PURPOSE: Garbage truck drivers. Each driver is assigned to a company.
#          license_number = driving license
#          vehicle_plate = truck registration (e.g., "KBC 123X")
#          is_active = FALSE if driver quit or is on leave
# ==============================================================================
class Driver(Base):
    __tablename__ = "drivers"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=False)
    license_number = Column(String(100))
    vehicle_plate = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    company = relationship("Company", back_populates="drivers")
    collections = relationship("Collection", back_populates="driver")
    routes = relationship("Route", back_populates="driver")


# ==============================================================================
# TABLE 11: ROUTES
# ==============================================================================
# PURPOSE: Daily route plan for a driver.
#          phase_ids = JSON array of phase UUIDs (e.g., ["uuid1", "uuid2"])
#          total_houses = how many houses in the route
#          completed_houses = how many marked done
#          status = pending → in_progress → completed → cancelled
# ==============================================================================
class Route(Base):
    __tablename__ = "routes"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    driver_id = Column(String(36), ForeignKey("drivers.id", ondelete="SET NULL"))
    estate_id = Column(String(36), ForeignKey("estates.id", ondelete="CASCADE"), nullable=False)
    route_date = Column(Date, nullable=False)
    phase_ids = Column(JSON)                                  # MySQL JSON type: ["phase-uuid-1", "phase-uuid-2"]
    total_houses = Column(Integer, default=0)
    completed_houses = Column(Integer, default=0)
    status = Column(Enum("pending", "in_progress", "completed", "cancelled", name="route_status"), default="pending")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    driver = relationship("Driver", back_populates="routes")
    estate = relationship("Estate", back_populates="routes")


# ==============================================================================
# TABLE 12: SMS LOGS
# ==============================================================================
# PURPOSE: Audit trail of every SMS sent.
#          provider_response = JSON from Africa's Talking (messageId, status, cost)
#          This table proves to the client that SMS were actually sent.
# ==============================================================================
class SMSLog(Base):
    __tablename__ = "sms_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    house_id = Column(String(36), ForeignKey("houses.id", ondelete="SET NULL"))
    phone_number = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    sms_type = Column(Enum("bill_issue", "payment_confirmation", "overdue_reminder", "service_alert", "general", name="sms_type"), nullable=False)
    status = Column(Enum("pending", "sent", "failed", "delivered", name="sms_status"), default="pending")
    provider_response = Column(JSON)                           # Africa's Talking API response
    sent_at = Column(DateTime)                                # NULL until actually sent
    created_at = Column(DateTime, default=func.now())
    
    house = relationship("House", back_populates="sms_logs")


# ==============================================================================
# TABLE 13: AUDIT LOGS
# ==============================================================================
# PURPOSE: Track WHO changed WHAT and WHEN.
#          Required for compliance and debugging.
#          old_data = JSON snapshot before change
#          new_data = JSON snapshot after change
# ==============================================================================
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    table_name = Column(String(100), nullable=False)          # "bills", "houses", etc.
    record_id = Column(String(36), nullable=False)            # UUID of the changed row
    action = Column(Enum("create", "update", "delete", name="audit_action"), nullable=False)
    old_data = Column(JSON)                                    # Before: {"amount": 400.00, "status": "pending"}
    new_data = Column(JSON)                                    # After:  {"amount": 400.00, "status": "paid"}
    performed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    performed_at = Column(DateTime, default=func.now())
    
    performer = relationship("User", back_populates="audit_logs")


# ==============================================================================
# TABLE 14: SETTINGS
# ==============================================================================
# PURPOSE: Key-value store for configurable values per company.
#          Example: default_bill_amount = 400
#                   sms_reminder_days = "3,7,14,30"
#                   company_logo_url = "https://..."
#          
#          UNIQUE constraint: (company_id, setting_key) — one value per key per company.
# ==============================================================================
class Setting(Base):
    __tablename__ = "settings"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    setting_key = Column(String(100), nullable=False)
    setting_value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    company = relationship("Company", back_populates="settings")
