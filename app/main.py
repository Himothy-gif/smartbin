"""
SMART BIN LTD - FASTAPI ENTRY POINT
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.config import get_settings
from app.routers import auth, estates, houses, residents, bills, payments, sms, dashboard, portal

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] Creating tables if missing...")
    Base.metadata.create_all(bind=engine)
    print(f"[STARTUP] Tables ready. Server starting on port {settings.api_port}")
    yield
    print("[SHUTDOWN] Cleaning up...")

app = FastAPI(
    title="Smart Bin Ltd API",
    description="Enterprise Garbage Collection Management System — Python/MySQL Edition",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.env == "development" else [os.getenv("CORS_ORIGIN", "*")],
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    print(f"{request.method} {request.url.path} - {duration:.3f}s")
    return response

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": datetime.utcnow().isoformat()
    }

app.include_router(auth.router)
app.include_router(estates.router)
app.include_router(houses.router)
app.include_router(residents.router)
app.include_router(bills.router)
app.include_router(payments.router)
app.include_router(sms.router)
app.include_router(dashboard.router)
app.include_router(portal.router)

@app.get("/")
def root():
    return {"message": "Smart Bin Ltd API v2.0.0", "docs": "/docs", "dashboard": "/static/index.html"}

@app.exception_handler(Exception)
async def global_exception(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc) if settings.env == "development" else "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.api_port, reload=settings.env == "development")
