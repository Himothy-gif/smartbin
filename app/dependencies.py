"""
==============================================================================
SMART BIN LTD - AUTHENTICATION & AUTHORIZATION DEPENDENCIES
==============================================================================
Replaces: src/middleware/auth.js from the Node.js version.

WHAT THIS DOES:
1. get_current_user: Reads the JWT token from the Authorization header,
   verifies it's valid, looks up the user in the database, and returns
   the user object. If invalid, returns 401 Unauthorized.

2. require_role: Checks if the logged-in user has the required role.
   If not, returns 403 Forbidden.

3. get_current_user_optional: Same as #1 but returns None instead of
   crashing. Used for endpoints that work with or without login.

HOW JWT WORKS IN THIS SYSTEM:
1. User logs in with email + password
2. Server verifies password with bcrypt
3. Server creates a JWT token containing: userId, email, role, companyId
4. Token is signed with JWT_SECRET (only server knows this)
5. Client stores token and sends it in every request header:
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
6. Server verifies signature, extracts userId, looks up user in DB
7. If everything checks out, the endpoint runs. If not, 401 error.

WHY DEPENDENCIES?
FastAPI's dependency injection system is powerful. Instead of writing
auth logic in every endpoint, we write it ONCE here and inject it
with:  current_user: User = Depends(get_current_user)
==============================================================================
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import get_settings
from app.models import User


# ==============================================================================
# STEP 1: SECURITY SCHEME
# ==============================================================================
# HTTPBearer tells FastAPI to expect: Authorization: Bearer <token>
# If the header is missing, FastAPI auto-returns 401 before our code runs.
security = HTTPBearer()


# ==============================================================================
# STEP 2: LOAD SETTINGS (for JWT secret)
# ==============================================================================
settings = get_settings()


# ==============================================================================
# STEP 3: GET CURRENT USER (core auth dependency)
# ==============================================================================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    This is called automatically by FastAPI for any endpoint that needs auth.
    
    FLOW:
    1. Extract token from Authorization: Bearer <token> header
    2. Decode JWT using our secret key
    3. Extract userId from the payload
    4. Look up user in MySQL database
    5. Verify user is_active (not soft-deleted)
    6. Return the User object to the endpoint
    
    If ANY step fails, raise 401 Unauthorized immediately.
    """
    
    # The actual token string (without "Bearer " prefix)
    token = credentials.credentials
    
    # Standard 401 error — same format for all failure cases (security best practice)
    # We don't tell the attacker WHY it failed (wrong signature? expired? missing?)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT token
        # algorithms=["HS256"] = HMAC with SHA-256 (industry standard)
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        
        # Extract userId from the "sub" (subject) claim
        user_id: str = payload.get("userId")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        # JWTError covers: expired token, invalid signature, malformed token
        raise credentials_exception
    
    # Look up the user in the database
    # We check is_active=True to prevent disabled accounts from accessing
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    
    if user is None:
        # User was deleted or deactivated after token was issued
        raise credentials_exception
    
    # SUCCESS: Return the full User object
    # The endpoint can now access: user.id, user.email, user.role, user.company_id
    return user


# ==============================================================================
# STEP 4: ROLE-BASED ACCESS CONTROL (RBAC)
# ==============================================================================
def require_role(*roles: str):
    """
    Factory function that creates a role-checking dependency.
    
    USAGE:
        @router.post("/estates")
        def create_estate(..., user: User = Depends(require_role("super_admin", "admin"))):
            # Only super_admin or admin can reach this code
            pass
    
    HOW IT WORKS:
    1. First calls get_current_user (validates JWT + looks up user)
    2. Then checks if user.role is in the allowed roles list
    3. If not, returns 403 Forbidden
    4. If yes, returns the User object
    
    The *roles syntax means: accept any number of role strings.
    Example: require_role("super_admin") or require_role("super_admin", "admin")
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(roles)}"
            )
        return current_user
    return role_checker


# ==============================================================================
# STEP 5: OPTIONAL AUTH (for public endpoints that also work logged-in)
# ==============================================================================
def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Same as get_current_user but NEVER crashes.
    Returns the User object if token is valid, None if not.
    
    USAGE:
        @router.get("/public-data")
        def public_data(user: User = Depends(get_current_user_optional)):
            if user:
                return {"message": f"Hello {user.full_name}"}
            else:
                return {"message": "Hello guest"}
    """
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None
