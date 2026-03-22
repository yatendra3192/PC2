"""Client management routes — add/edit/list clients, manage their configs."""

from __future__ import annotations


import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db.client import fetch_all, fetch_one, execute_returning, execute
from app.auth.dependencies import require_admin, get_current_user
from app.models.user import TokenPayload

router = APIRouter()


class ClientCreate(BaseModel):
    name: str
    code: str


class ClientUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class ClientResponse(BaseModel):
    id: str
    name: str
    code: str
    is_active: bool
    pipeline_config_id: str | None = None
    # Computed counts
    product_count: int = 0
    published_count: int = 0
    template_count: int = 0


@router.get("", response_model=list[ClientResponse])
async def list_clients(user: TokenPayload = Depends(get_current_user)):
    """List all clients. Admins see all, others see only their assigned client."""
    if user.role == "admin" and user.client_id is None:
        # Super admin — sees all
        rows = await fetch_all("""
            SELECT c.*,
                   (SELECT COUNT(*) FROM products p WHERE p.client_id = c.id) as product_count,
                   (SELECT COUNT(*) FROM products p WHERE p.client_id = c.id AND p.status = 'published') as published_count,
                   (SELECT COUNT(*) FROM retailer_templates rt WHERE rt.client_id = c.id) as template_count
            FROM clients c ORDER BY c.name
        """)
    else:
        # Scoped to their client
        rows = await fetch_all("""
            SELECT c.*,
                   (SELECT COUNT(*) FROM products p WHERE p.client_id = c.id) as product_count,
                   (SELECT COUNT(*) FROM products p WHERE p.client_id = c.id AND p.status = 'published') as published_count,
                   (SELECT COUNT(*) FROM retailer_templates rt WHERE rt.client_id = c.id) as template_count
            FROM clients c WHERE c.id = $1::uuid ORDER BY c.name
        """, user.client_id)

    return [ClientResponse(
        id=str(r["id"]), name=r["name"], code=r["code"], is_active=r["is_active"],
        pipeline_config_id=str(r["pipeline_config_id"]) if r["pipeline_config_id"] else None,
        product_count=r["product_count"], published_count=r["published_count"], template_count=r["template_count"],
    ) for r in rows]


@router.post("", response_model=ClientResponse)
async def create_client(req: ClientCreate, user: TokenPayload = Depends(require_admin)):
    """Create a new client with default pipeline config."""
    existing = await fetch_one("SELECT id FROM clients WHERE code = $1", req.code)
    if existing:
        raise HTTPException(status_code=400, detail=f"Client code '{req.code}' already exists")

    # Create client
    client = await execute_returning(
        "INSERT INTO clients (name, code) VALUES ($1, $2) RETURNING *",
        req.name, req.code,
    )

    # Create default pipeline config (all 7 stages enabled)
    config = await execute_returning(
        """INSERT INTO pipeline_configs (client_id, name, stages_enabled)
           VALUES ($1::uuid, $2, '{"1":true,"2":true,"3":true,"4":true,"5":true,"6":true,"7":true}')
           RETURNING id""",
        str(client["id"]), f"{req.name} Default Pipeline",
    )

    # Link pipeline config to client
    await execute(
        "UPDATE clients SET pipeline_config_id = $1::uuid WHERE id = $2::uuid",
        str(config["id"]), str(client["id"]),
    )

    return ClientResponse(
        id=str(client["id"]), name=client["name"], code=client["code"],
        is_active=True, pipeline_config_id=str(config["id"]),
    )


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(client_id: str, req: ClientUpdate, user: TokenPayload = Depends(require_admin)):
    updates = []
    params = []
    idx = 1

    if req.name is not None:
        updates.append(f"name = ${idx}")
        params.append(req.name)
        idx += 1
    if req.is_active is not None:
        updates.append(f"is_active = ${idx}")
        params.append(req.is_active)
        idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    params.append(client_id)
    row = await execute_returning(
        f"UPDATE clients SET {', '.join(updates)} WHERE id = ${idx}::uuid RETURNING *", *params,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")

    return ClientResponse(
        id=str(row["id"]), name=row["name"], code=row["code"], is_active=row["is_active"],
        pipeline_config_id=str(row["pipeline_config_id"]) if row["pipeline_config_id"] else None,
    )


@router.get("/{client_id}")
async def get_client_detail(client_id: str, user: TokenPayload = Depends(get_current_user)):
    """Get client with full config details."""
    client = await fetch_one("SELECT * FROM clients WHERE id = $1::uuid", client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Get pipeline config
    config = None
    if client["pipeline_config_id"]:
        config_row = await fetch_one("SELECT * FROM pipeline_configs WHERE id = $1::uuid", str(client["pipeline_config_id"]))
        if config_row:
            config = {
                "id": str(config_row["id"]),
                "stages_enabled": json.loads(config_row["stages_enabled"]) if config_row["stages_enabled"] else {},
                "stage_configs": json.loads(config_row["stage_configs"]) if config_row["stage_configs"] else {},
            }

    # Get templates
    templates = await fetch_all("SELECT * FROM retailer_templates WHERE client_id = $1::uuid", client_id)

    return {
        "id": str(client["id"]),
        "name": client["name"],
        "code": client["code"],
        "is_active": client["is_active"],
        "pipeline_config": config,
        "templates": [{"id": str(t["id"]), "name": t["template_name"], "version": t["version"]} for t in templates],
    }
