from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException

from app.db.client import fetch_all, fetch_one, execute_returning
from app.auth.middleware import hash_password
from app.auth.dependencies import require_admin
from app.models.user import UserResponse, UserCreate, TokenPayload

router = APIRouter()


@router.get("", response_model=list[UserResponse])
async def list_users(_: TokenPayload = Depends(require_admin)):
    rows = await fetch_all("SELECT * FROM users ORDER BY created_at DESC")
    return [
        UserResponse(
            id=str(r["id"]),
            email=r["email"],
            full_name=r["full_name"],
            role=r["role"],
            client_id=str(r["client_id"]) if r["client_id"] else None,
            is_active=r["is_active"],
            last_active_at=r["last_active_at"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("", response_model=UserResponse)
async def create_user(user: UserCreate, _: TokenPayload = Depends(require_admin)):
    existing = await fetch_one("SELECT id FROM users WHERE email = $1", user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    row = await execute_returning(
        """INSERT INTO users (email, password_hash, full_name, role, client_id)
           VALUES ($1, $2, $3, $4, $5::uuid) RETURNING *""",
        user.email,
        hash_password(user.password),
        user.full_name,
        user.role,
        user.client_id,
    )

    return UserResponse(
        id=str(row["id"]),
        email=row["email"],
        full_name=row["full_name"],
        role=row["role"],
        client_id=str(row["client_id"]) if row["client_id"] else None,
        is_active=row["is_active"],
        created_at=row["created_at"],
    )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, role: str | None = None, is_active: bool | None = None, _: TokenPayload = Depends(require_admin)):
    updates = []
    params = []
    idx = 1

    if role is not None:
        updates.append(f"role = ${idx}")
        params.append(role)
        idx += 1
    if is_active is not None:
        updates.append(f"is_active = ${idx}")
        params.append(is_active)
        idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    params.append(user_id)
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ${idx}::uuid RETURNING *"
    row = await execute_returning(query, *params)

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
