"""
==============================================================================
SMART BIN LTD - DATABASE CONNECTION MODULE
==============================================================================
Replaces: src/config/database.js from the Node.js version.

WHAT THIS DOES:
1. Creates a SQLAlchemy "engine" — the connection pool to MySQL
2. Creates a "SessionLocal" factory — generates new DB sessions per request
3. Creates a "Base" class — all our 14 table models inherit from this
4. Provides get_db() — FastAPI dependency that gives each endpoint a session

WHY SQLALCHEMY INSTEAD OF RAW SQL?
- ORM: Python objects map directly to database rows
- Connection pooling: reuses connections instead of opening/closing each time
- Safety: prevents SQL injection automatically
- Migrations: Alembic can auto-generate schema changes

POOL SETTINGS (matching Node.js version):
- pool_size=20: keep 20 connections ready
- max_overflow=0: never create more than 20
- pool_recycle=3600: close connections after 1 hour (prevents stale connections)
- pool_pre_ping=True: test connection before use (handles MySQL timeouts)
==============================================================================
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import get_settings


# ==============================================================================
# STEP 1: LOAD SETTINGS
# ==============================================================================
settings = get_settings()

# ==============================================================================
# STEP 2: BUILD MySQL CONNECTION STRING
# ==============================================================================
# Format: dialect+driver://user:password@host:port/database?charset
# We use pymysql driver (pure Python, no extra system packages needed)
# utf8mb4 supports all Unicode characters including emojis
DATABASE_URL = (
    f"mysql+pymysql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    f"?charset=utf8mb4"
)

# ==============================================================================
# STEP 3: CREATE THE ENGINE (connection pool)
# ==============================================================================
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # Keep 20 connections warm and ready
    max_overflow=0,         # Never exceed pool_size (prevents memory spikes)
    pool_recycle=3600,      # Recycle connections every hour (MySQL kills idle after 8hrs)
    pool_pre_ping=True,     # Test connection before using it (handles network drops)
    echo=settings.env == "development"  # Log every SQL query in dev mode
)

# ==============================================================================
# STEP 4: CREATE SESSION FACTORY
# ==============================================================================
# autocommit=False: we control when data is saved (safer)
# autoflush=False: don't auto-send to DB until we explicitly commit
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ==============================================================================
# STEP 5: CREATE BASE CLASS FOR ALL MODELS
# ==============================================================================
# Every table (companies, users, estates, houses, etc.) inherits from Base.
# SQLAlchemy scans these classes and creates the corresponding MySQL tables.
Base = declarative_base()

# ==============================================================================
# STEP 6: FASTAPI DEPENDENCY — get_db()
# ==============================================================================
# FastAPI calls this automatically for every endpoint that needs a DB session.
# "yield" gives the endpoint a session, then closes it when the request ends.
# This prevents connection leaks (a common bug in beginner APIs).
#
# USAGE in a router:
#   @router.get("/estates")
#   def list_estates(db: Session = Depends(get_db)):
#       return db.query(Estate).all()
# ==============================================================================
def get_db() -> Session:
    """
    FastAPI dependency that yields a database session.
    Automatically closes the session after the HTTP request finishes.
    """
    db = SessionLocal()     # Open a new session from the pool
    try:
        yield db          # Hand it to the endpoint function
    finally:
        db.close()        # ALWAYS close, even if the endpoint crashes
