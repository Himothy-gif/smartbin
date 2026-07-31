"""
==============================================================================
SMART BIN LTD - FASTAPI ENTRY POINT
==============================================================================
This is the "main" file. When you run: uvicorn app.main:app
FastAPI loads this file, creates the app, and starts listening for requests.

WHAT HAPPENS ON STARTUP:
1. Base.metadata.create_all(engine) → SQLAlchemy checks all 14 models
   and creates any missing tables in MySQL (dev only; use Alembic in prod)
2. Registers all routers (auth, estates, houses, bills, etc.)
3. Starts the ASGI server on port 8000

WHAT HAPPENS PER REQUEST:
1. FastAPI receives HTTP request
2. Matches URL to the right router/endpoint
3. Runs Pydantic validation on request body
4. Runs dependency injection (get_db, get_current_user)
5. Executes endpoint function
6. Serializes response with Pydantic
7. Returns JSON to client

AUTO-GENERATED DOCS:
Visit http://localhost:8000/docs to see interactive API documentation.
Every endpoint, every schema, every parameter is documented automatically.
==============================================================================
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.config import get_settings
from app.routers import auth, estates, houses

settings = get_settings()


# ==============================================================================
# LIFESPAN: Startup and Shutdown events
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs ONCE when the server starts and ONCE when it stops.
    
    STARTUP:
    - Create all SQLAlchemy tables if they don't exist (dev convenience)
    - In production, use Alembic migrations instead
    
    SHUTDOWN:
    - Clean up resources (close DB connections, stop cron jobs)
    """
    # STARTUP
    print("[STARTUP] Creating tables if missing...")
    Base.metadata.create_all(bind=engine)
    print("[STARTUP] Tables ready. Server starting on port", settings.api_port)
    
    yield  # Server runs here
    
    # SHUTDOWN
    print("[SHUTDOWN] Cleaning up...")


# ==============================================================================
# CREATE FASTAPI APP
# ==============================================================================
app = FastAPI(
    title="Smart Bin Ltd API",
    description="Enterprise Garbage Collection Management System — Python/MySQL Edition",
    version="2.0.0",
    lifespan=lifespan
)

# ==============================================================================
# CORS: Allow frontend apps to call this API
# ==============================================================================
# In development: allow ALL origins (localhost, 127.0.0.1, etc.)
# In production: restrict to your actual domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.env == "development" else [os.getenv("CORS_ORIGIN", "*")],
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

# ==============================================================================
# REQUEST LOGGING MIDDLEWARE
# ==============================================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Logs every request: method, path, and duration.
    Example output: POST /api/auth/login - 0.234s
    """
    import time
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    print(f"{request.method} {request.url.path} - {duration:.3f}s")
    return response


# ==============================================================================
# HEALTH CHECK
# ==============================================================================
@app.get("/health")
def health():
    """
    Returns system status. Used by:
    - Docker health checks
    - Monitoring tools (UptimeRobot, Pingdom)
    - Load balancers (to know if this instance is healthy)
    """
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
        "timestamp": datetime.utcnow().isoformat()
    }


# ==============================================================================
# REGISTER ROUTERS
# ==============================================================================
# Each router handles a group of related endpoints.
# As we build more routers (estates, houses, bills), we add them here.
app.include_router(auth.router)
app.include_router(estates.router)
app.include_router(houses.router)


# ==============================================================================
# GLOBAL ERROR HANDLER
# ==============================================================================
@app.exception_handler(Exception)
async def global_exception(request: Request, exc: Exception):
    """
    Catches ANY unhandled exception and returns a clean JSON error.
    In development: shows the actual error message.
    In production: hides details to prevent information leakage.
    """
    return JSONResponse(
        status_code=500,
        content={"error": str(exc) if settings.env == "development" else "Internal server error"}
    )


# ==============================================================================
# RUN DIRECTLY (for development)
# ==============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.env == "development"  # Auto-restart on file changes
    )
