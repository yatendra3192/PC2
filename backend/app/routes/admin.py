"""Admin routes — confidence config, pipeline config, model health, audit logs, DQ config.
All operations are client-scoped.
"""

from __future__ import annotations


import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db.client import fetch_all, fetch_one, execute, execute_returning
from app.auth.dependencies import require_admin
from app.models.user import TokenPayload
from app.config import settings
from app.ai.router import check_model_health

router = APIRouter()


# ── Model Health ──

class ModelKeyStatus(BaseModel):
    provider: str
    configured: bool
    model: str | None = None
    healthy: bool = False
    key_preview: str | None = None


@router.get("/models/health")
async def get_model_health_status(_: TokenPayload = Depends(require_admin)):
    health = await check_model_health()
    providers = [
        ModelKeyStatus(provider="OpenAI", configured=health["openai"]["configured"], model=health["openai"]["model"], healthy=health["openai"]["healthy"], key_preview=_mask_key(settings.openai_api_key) if settings.has_openai else None),
        ModelKeyStatus(provider="Anthropic", configured=health["anthropic"]["configured"], model=health["anthropic"]["model"], healthy=health["anthropic"]["healthy"], key_preview=_mask_key(settings.anthropic_api_key) if settings.has_anthropic else None),
        ModelKeyStatus(provider="SerpAPI", configured=health["serpapi"]["configured"], key_preview=_mask_key(settings.serpapi_key) if settings.has_serpapi else None),
        ModelKeyStatus(provider="Athena DQ", configured=bool(settings.athena_dq_url), key_preview=_mask_key(settings.athena_dq_api_key) if settings.athena_dq_api_key else None),
    ]
    return {"demo_mode": settings.demo_mode, "providers": [p.model_dump() for p in providers]}


# ── Model Registry (DB-backed) ──

@router.get("/models")
async def list_models(_: TokenPayload = Depends(require_admin)):
    rows = await fetch_all("SELECT * FROM model_registry ORDER BY model_name")
    return [_model_from_row(r) for r in rows]


@router.post("/models")
async def register_model(
    model_name: str, model_type: str, provider: str,
    endpoint_url: str | None = None, capabilities: list[str] | None = None,
    default_for_stages: list[int] | None = None, client_id: str | None = None,
    _: TokenPayload = Depends(require_admin),
):
    row = await execute_returning(
        """INSERT INTO model_registry (model_name, model_type, provider, endpoint_url, capabilities, default_for_stages, client_id, added_by)
           VALUES ($1, $2, $3, $4, $5, $6, $7::uuid, 'client')
           RETURNING *""",
        model_name, model_type, provider, endpoint_url, capabilities or [], default_for_stages or [], client_id,
    )
    return _model_from_row(row)


@router.delete("/models/{model_id}")
async def deactivate_model(model_id: str, _: TokenPayload = Depends(require_admin)):
    await execute("UPDATE model_registry SET is_active = false WHERE id = $1::uuid", model_id)
    return {"message": "Model deactivated"}


# ── Confidence Config (per stage, per client) ──

class ConfidenceConfigUpdate(BaseModel):
    auto_approve_threshold: float | None = None
    needs_review_threshold: float | None = None
    source_reliability_scores: dict[str, float] | None = None
    component_weights: dict[str, float] | None = None
    multi_source_agreement_bonus: int | None = None
    conflict_resolution: str | None = None


@router.get("/confidence/{client_id}/{stage}")
async def get_confidence_config(client_id: str, stage: int, _: TokenPayload = Depends(require_admin)):
    config = await fetch_one(
        "SELECT stage_configs FROM pipeline_configs WHERE client_id = $1::uuid AND is_active = true",
        client_id,
    )
    if not config:
        raise HTTPException(status_code=404, detail="No pipeline config for this client")

    stage_configs = json.loads(config["stage_configs"]) if config["stage_configs"] else {}
    stage_conf = stage_configs.get(str(stage), {}).get("confidence", {})

    # Return with defaults
    defaults = {
        "auto_approve_threshold": 85,
        "needs_review_threshold": 60,
        "source_reliability_scores": {"human": 100, "kb": 95, "pdf_ocr": 85, "api_feed": 85, "csv_supplier": 80, "vision": 75, "llm": 65, "web_google": 70, "web_marketplace": 65},
        "component_weights": {"source_reliability": 0.40, "consistency": 0.35, "completeness": 0.25},
        "multi_source_agreement_bonus": 10,
        "conflict_resolution": "highest_reliability",
    }
    for k, v in defaults.items():
        if k not in stage_conf:
            stage_conf[k] = v

    return {"client_id": client_id, "stage": stage, "confidence": stage_conf}


@router.put("/confidence/{client_id}/{stage}")
async def update_confidence_config(
    client_id: str, stage: int, req: ConfidenceConfigUpdate,
    user: TokenPayload = Depends(require_admin),
):
    config = await fetch_one(
        "SELECT id, stage_configs FROM pipeline_configs WHERE client_id = $1::uuid AND is_active = true",
        client_id,
    )
    if not config:
        raise HTTPException(status_code=404, detail="No pipeline config for this client")

    stage_configs = json.loads(config["stage_configs"]) if config["stage_configs"] else {}
    if str(stage) not in stage_configs:
        stage_configs[str(stage)] = {}
    if "confidence" not in stage_configs[str(stage)]:
        stage_configs[str(stage)]["confidence"] = {}

    conf = stage_configs[str(stage)]["confidence"]
    update_data = req.model_dump(exclude_none=True)
    conf.update(update_data)

    await execute(
        "UPDATE pipeline_configs SET stage_configs = $1::jsonb, updated_at = now() WHERE id = $2::uuid",
        json.dumps(stage_configs), str(config["id"]),
    )

    # Audit
    await execute(
        """INSERT INTO audit_trail (layer, field_name, action, new_value, actor_type, actor_id, metadata)
           VALUES ('config', $1, 'mapping_corrected', $2, 'human', $3, $4::jsonb)""",
        f"confidence_stage_{stage}", json.dumps(update_data), user.sub,
        json.dumps({"client_id": client_id, "stage": stage}),
    )

    return {"message": "Confidence config updated", "client_id": client_id, "stage": stage}


# ── Pipeline Config (stage toggles per client) ──

class PipelineStageUpdate(BaseModel):
    stages_enabled: dict[str, bool]


@router.get("/pipeline/{client_id}")
async def get_pipeline_config(client_id: str, _: TokenPayload = Depends(require_admin)):
    config = await fetch_one(
        "SELECT * FROM pipeline_configs WHERE client_id = $1::uuid AND is_active = true", client_id,
    )
    if not config:
        raise HTTPException(status_code=404, detail="No pipeline config for this client")

    return {
        "id": str(config["id"]),
        "client_id": client_id,
        "name": config["name"],
        "stages_enabled": json.loads(config["stages_enabled"]) if config["stages_enabled"] else {},
        "stage_configs": json.loads(config["stage_configs"]) if config["stage_configs"] else {},
        "dq_config": json.loads(config["dq_config"]) if config["dq_config"] else {},
        "scraper_config": json.loads(config["scraper_config"]) if config["scraper_config"] else {},
    }


@router.put("/pipeline/{client_id}")
async def update_pipeline_config(client_id: str, req: PipelineStageUpdate, user: TokenPayload = Depends(require_admin)):
    # Enforce: stages 1 and 7 always enabled
    req.stages_enabled["1"] = True
    req.stages_enabled["7"] = True

    config = await fetch_one(
        "SELECT id FROM pipeline_configs WHERE client_id = $1::uuid AND is_active = true", client_id,
    )
    if not config:
        raise HTTPException(status_code=404, detail="No pipeline config for this client")

    await execute(
        "UPDATE pipeline_configs SET stages_enabled = $1::jsonb, updated_at = now() WHERE id = $2::uuid",
        json.dumps(req.stages_enabled), str(config["id"]),
    )

    await execute(
        """INSERT INTO audit_trail (layer, action, new_value, actor_type, actor_id, metadata)
           VALUES ('config', 'mapping_corrected', $1, 'human', $2, $3::jsonb)""",
        json.dumps(req.stages_enabled), user.sub, json.dumps({"client_id": client_id}),
    )

    return {"message": "Pipeline config updated", "stages_enabled": req.stages_enabled}


# ── DQ Config (per client) ──

class DQConfigUpdate(BaseModel):
    enabled: bool = True
    api_endpoint: str | None = None
    stages_enabled: dict[str, bool] | None = None
    block_on_fail: bool = True
    allow_override: bool = True
    timeout_ms: int = 5000


@router.get("/dq/{client_id}")
async def get_dq_config(client_id: str, _: TokenPayload = Depends(require_admin)):
    config = await fetch_one(
        "SELECT dq_config FROM pipeline_configs WHERE client_id = $1::uuid AND is_active = true", client_id,
    )
    dq = json.loads(config["dq_config"]) if config and config["dq_config"] else {}
    defaults = {"enabled": True, "api_endpoint": settings.athena_dq_url, "stages_enabled": {str(i): True for i in range(1, 8)}, "block_on_fail": True, "allow_override": True, "timeout_ms": 5000}
    for k, v in defaults.items():
        if k not in dq:
            dq[k] = v
    return {"client_id": client_id, "dq_config": dq}


@router.put("/dq/{client_id}")
async def update_dq_config(client_id: str, req: DQConfigUpdate, _: TokenPayload = Depends(require_admin)):
    config = await fetch_one(
        "SELECT id FROM pipeline_configs WHERE client_id = $1::uuid AND is_active = true", client_id,
    )
    if not config:
        raise HTTPException(status_code=404, detail="No pipeline config")

    await execute(
        "UPDATE pipeline_configs SET dq_config = $1::jsonb, updated_at = now() WHERE id = $2::uuid",
        json.dumps(req.model_dump()), str(config["id"]),
    )
    return {"message": "DQ config updated"}


# ── Audit Logs ──

@router.get("/audit")
async def get_audit_logs(
    action: str | None = None,
    actor_id: str | None = None,
    layer: str | None = None,
    product_id: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    _: TokenPayload = Depends(require_admin),
):
    conditions = []
    params: list = []
    idx = 1

    if action:
        conditions.append(f"action = ${idx}")
        params.append(action)
        idx += 1
    if actor_id:
        conditions.append(f"actor_id = ${idx}")
        params.append(actor_id)
        idx += 1
    if layer:
        conditions.append(f"layer = ${idx}")
        params.append(layer)
        idx += 1
    if product_id:
        conditions.append(f"product_id = ${idx}::uuid")
        params.append(product_id)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.extend([limit, offset])

    rows = await fetch_all(
        f"""SELECT at.*, p.product_name, p.model_number
            FROM audit_trail at
            LEFT JOIN products p ON at.product_id = p.id
            {where}
            ORDER BY at.created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}""",
        *params,
    )

    count_row = await fetch_one(f"SELECT COUNT(*) as cnt FROM audit_trail {where}", *params[:-2])
    total = count_row["cnt"] if count_row else 0

    return {
        "total": total,
        "items": [
            {
                "id": str(r["id"]),
                "product_id": str(r["product_id"]) if r["product_id"] else None,
                "product_name": r["product_name"],
                "model_number": r["model_number"],
                "layer": r["layer"],
                "field_name": r["field_name"],
                "stage": r["stage"],
                "action": r["action"],
                "old_value": r["old_value"],
                "new_value": r["new_value"],
                "actor_type": r["actor_type"],
                "actor_id": r["actor_id"],
                "model_name": r["model_name"],
                "reason": r["reason"],
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ],
    }


# ── Dashboard Stats ──

@router.get("/dashboard/stats")
async def get_dashboard_stats(client_id: str | None = None, _: TokenPayload = Depends(require_admin)):
    client_filter = "AND p.client_id = $1::uuid" if client_id else ""
    params = [client_id] if client_id else []

    row = await fetch_one(f"""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE p.status = 'processing') as in_pipeline,
            COUNT(*) FILTER (WHERE p.status = 'review') as awaiting_review,
            COUNT(*) FILTER (WHERE p.status = 'published') as published,
            COUNT(*) FILTER (WHERE p.status IN ('draft','rejected')) as other
        FROM products p
        WHERE 1=1 {client_filter}
    """, *params)

    review_row = await fetch_one(f"""
        SELECT COUNT(*) as cnt
        FROM product_iksula_values piv
        JOIN products p ON piv.product_id = p.id
        WHERE piv.review_status IN ('needs_review','low_confidence')
          AND p.status != 'published'
          {client_filter.replace('p.', 'p.')}
    """, *params)

    return {
        "total_products": row["total"] or 0,
        "in_pipeline": row["in_pipeline"] or 0,
        "awaiting_review": review_row["cnt"] if review_row else 0,
        "published": row["published"] or 0,
        "other": row["other"] or 0,
    }


def _model_from_row(r) -> dict:
    return {
        "id": str(r["id"]), "model_name": r["model_name"], "model_type": r["model_type"],
        "provider": r["provider"], "endpoint_url": r["endpoint_url"],
        "capabilities": r["capabilities"] or [], "default_for_stages": r["default_for_stages"] or [],
        "is_active": r["is_active"], "added_by": r["added_by"],
        "client_id": str(r["client_id"]) if r["client_id"] else None,
    }


def _mask_key(key: str) -> str:
    if not key or len(key) < 16:
        return "****"
    return f"{key[:8]}...{key[-4:]}"
