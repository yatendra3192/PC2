import logging
from fastapi import APIRouter, HTTPException, status, Depends

from app.db.client import fetch_one
from app.auth.middleware import verify_password, create_access_token
from app.auth.dependencies import get_current_user
from app.models.user import LoginRequest, LoginResponse, UserResponse, TokenPayload

logger = logging.getLogger("pc2.auth")
router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    row = await fetch_one("SELECT * FROM users WHERE email = $1 AND is_active = true", req.email)
    logger.info(f"Login attempt: email={req.email}, user_found={row is not None}")
    if row:
        logger.info(f"Hash in DB: {row['password_hash'][:20]}...")
        try:
            pwd_ok = verify_password(req.password, row["password_hash"])
            logger.info(f"Password verify result: {pwd_ok}")
        except Exception as e:
            logger.error(f"Password verify error: {e}")
            pwd_ok = False
    else:
        pwd_ok = False
    if not row or not pwd_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({
        "sub": str(row["id"]),
        "email": row["email"],
        "role": row["role"],
        "client_id": str(row["client_id"]) if row["client_id"] else None,
    })

    return LoginResponse(
        access_token=token,
        user=UserResponse(
            id=str(row["id"]),
            email=row["email"],
            full_name=row["full_name"],
            role=row["role"],
            client_id=str(row["client_id"]) if row["client_id"] else None,
            is_active=row["is_active"],
            created_at=row["created_at"],
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: TokenPayload = Depends(get_current_user)):
    row = await fetch_one("SELECT * FROM users WHERE id = $1", user.sub)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=str(row["id"]),
        email=row["email"],
        full_name=row["full_name"],
        role=row["role"],
        client_id=str(row["client_id"]) if row["client_id"] else None,
        is_active=row["is_active"],
        created_at=row["created_at"],
    )


@router.post("/forgot-password")
async def forgot_password(email: str):
    # In production, send a reset email. For demo, just acknowledge.
    return {"message": "If that email exists, a reset link has been sent."}
