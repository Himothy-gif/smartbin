"""
==============================================================================
SMART BIN LTD - AUTHENTICATION ROUTER
==============================================================================
Replaces: src/routes/auth.js from the Node.js version.

ENDPOINTS:
  POST /api/auth/login    → Verify email+password, return JWT token
  GET  /api/auth/me       → Return current user profile (protected)

HOW LOGIN WORKS:
1. Client sends {email, password}
2. We hash the password with bcrypt and compare to stored hash
3. If match, create JWT token with userId, email, role, companyId
4. Return token + user object
5. Client stores token and sends it in Authorization header forever after

SECURITY NOTES:
- bcrypt is intentionally SLOW (takes ~100ms to hash). This prevents
  brute-force attacks — an attacker can only try ~10 passwords/second.
- JWT tokens are signed but NOT encrypted. Never put passwords in them.
- Tokens expire after 7 days. Client must re-login.
==============================================================================
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.config import get_settings
from app.dependencies import get_current_user


# ==============================================================================
# ROUTER SETUP
# ==============================================================================
# prefix="/api/auth" means all routes in this file start with /api/auth
# tags=["auth"] groups them in FastAPI's auto-generated docs at /docs
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ==============================================================================
# PASSWORD HASHING
# ==============================================================================
# CryptContext manages multiple hash algorithms. We only use bcrypt.
# "deprecated='auto'" means: if we ever add a new algorithm, old passwords
# still work (backward compatible).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==============================================================================
# SETTINGS (for JWT secret and expiry)
# ==============================================================================
settings = get_settings()


# ==============================================================================
# HELPER: Create JWT Token
# ==============================================================================
def create_token(user: User) -> str:
    """
    Creates a signed JWT token containing the user's identity.
    
    PAYLOAD (what's inside the token):
    {
        "userId": "a1b2c3d4-...",
        "email": "admin@smartbin.co.ke",
        "role": "super_admin",
        "companyId": "e5f6g7h8-...",
        "exp": 1753987200  ← Unix timestamp, 7 days from now
    }
    
    The token is signed with JWT_SECRET. If someone tampers with it,
    the signature becomes invalid and jwt.decode() will reject it.
    """
    # Calculate expiry: now + 7 days
    expire = datetime.utcnow() + timedelta(days=7)
    
    payload = {
        "userId": user.id,
        "email": user.email,
        "role": user.role,
        "companyId": user.company_id,
        "exp": expire  # jwt.encode auto-converts datetime to Unix timestamp
    }
    
    # HS256 = HMAC-SHA256. Fast and secure for our use case.
    # For higher security (but slower), use RS256 with public/private keys.
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


# ==============================================================================
# ENDPOINT 1: LOGIN
# ==============================================================================
@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    
    REQUEST BODY (JSON):
    {
        "email": "admin@smartbin.co.ke",
        "password": "admin123"
    }
    
    RESPONSE (JSON):
    {
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "user": {
            "id": "...",
            "email": "admin@smartbin.co.ke",
            "full_name": "System Administrator",
            "role": "super_admin",
            "company_id": "..."
        }
    }
    
    ERRORS:
    - 401: Invalid email or password (we don't say which — security)
    """
    
    # STEP 1: Find user by email
    # We use .first() because email has a UNIQUE constraint — only one result possible
    user = db.query(User).filter(User.email == req.email).first()
    
    # STEP 2: Verify user exists and is active
    # If user is None OR is_active is False, same error message.
    # This prevents "email enumeration" attacks (attacker can't tell
    # if an email exists by checking error messages).
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # STEP 3: Verify password
    # bcrypt.verify() hashes the input password and compares to stored hash.
    # It handles salt extraction automatically — we don't need to store salt separately.
    if not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # STEP 4: Update last_login timestamp
    # This helps admins see who is actively using the system.
    user.last_login = datetime.utcnow()
    db.commit()  # Save the timestamp update
    
    # STEP 5: Generate JWT token
    token = create_token(user)
    
    # STEP 6: Return token + user info
    # We DON'T return the password_hash — never expose it.
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "company_id": user.company_id,
        }
    }


# ==============================================================================
# ENDPOINT 2: GET CURRENT USER
# ==============================================================================
@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """
    Return the currently logged-in user's profile.
    
    HEADERS REQUIRED:
        Authorization: Bearer <your-jwt-token>
    
    This endpoint proves the auth system works. If you send a valid token,
    you get your profile back. If not, 401 error.
    
    The get_current_user dependency (from app/dependencies.py) does ALL the work:
    - Extract token from header
    - Verify JWT signature
    - Look up user in database
    - Check is_active
    - Return User object
    """
    return current_user
