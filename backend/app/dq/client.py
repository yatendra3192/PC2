"""Athena DQ client — calls external Data Quality API after each stage.

Sends stage output, receives pass/warning/fail per field.
Handles timeout (proceed with warning), manual override.
"""

import json
import logging
import httpx

from app.config import settings
from app.db.client import fetch_one, execute

logger = logging.getLogger(__name__)


class DQClient:

    async def check(self, product_id: str, stage: int, fields: list[dict]) -> dict:
        """Send stage output to Athena DQ for quality check.

        Args:
            product_id: Product being checked
            stage: Stage number that just completed
            fields: List of {attribute_code, value, unit, source}

        Returns:
            {"results": [{attribute_code, status, message, suggestion}], "overall_status": "pass|warn|fail"}
        """
        if not settings.athena_dq_url:
            return {"results": [], "overall_status": "skipped", "message": "DQ not configured"}

        # Get client DQ config
        product = await fetch_one("SELECT client_id, pipeline_config_id FROM products WHERE id = $1::uuid", product_id)
        if not product:
            return {"results": [], "overall_status": "skipped"}

        config = await fetch_one("SELECT dq_config FROM pipeline_configs WHERE id = $1::uuid", str(product["pipeline_config_id"])) if product["pipeline_config_id"] else None
        dq_config = json.loads(config["dq_config"]) if config and config["dq_config"] else {}

        if not dq_config.get("enabled", True):
            return {"results": [], "overall_status": "disabled"}

        # Check if DQ is enabled for this stage
        stages_enabled = dq_config.get("stages_enabled", {})
        if not stages_enabled.get(str(stage), True):
            return {"results": [], "overall_status": "stage_disabled"}

        timeout = dq_config.get("timeout_ms", 5000) / 1000

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{settings.athena_dq_url}/check",
                    headers={
                        "Authorization": f"Bearer {settings.athena_dq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "product_id": product_id,
                        "stage": stage,
                        "client_id": str(product["client_id"]),
                        "fields": fields,
                    },
                    timeout=timeout,
                )
                resp.raise_for_status()
                result = resp.json()

            # Log results in audit trail
            for field_result in result.get("results", []):
                action = f"dq_{field_result.get('status', 'unknown')}"
                if action in ("dq_pass", "dq_passed"):
                    action = "dq_passed"
                elif action in ("dq_fail", "dq_failed"):
                    action = "dq_failed"

                await execute(
                    """INSERT INTO audit_trail (product_id, layer, field_name, stage, action, new_value, actor_type, actor_id)
                       VALUES ($1::uuid, 'iksula', $2, $3, $4, $5, 'system', 'athena_dq')""",
                    product_id, field_result.get("attribute_code"), stage, action,
                    field_result.get("message"),
                )

            return result

        except httpx.TimeoutException:
            logger.warning(f"DQ check timed out for product {product_id} stage {stage}")
            fallback = dq_config.get("fallback_on_timeout", "proceed_with_warning")
            return {"results": [], "overall_status": "timeout", "message": f"DQ check timed out — {fallback}"}

        except Exception as e:
            logger.error(f"DQ check failed: {e}")
            return {"results": [], "overall_status": "error", "message": str(e)}

    async def override(self, product_id: str, attribute_code: str, reason: str, note: str, user_id: str) -> dict:
        """Override a DQ failure with a reason."""
        await execute(
            """INSERT INTO audit_trail
               (product_id, layer, field_name, action, actor_type, actor_id, reason, metadata)
               VALUES ($1::uuid, 'iksula', $2, 'dq_overridden', 'human', $3, $4, $5::jsonb)""",
            product_id, attribute_code, user_id, reason,
            json.dumps({"note": note}),
        )

        # Update field review status
        await execute(
            """UPDATE product_iksula_values SET review_status = 'dq_override', updated_at = now()
               WHERE product_id = $1::uuid AND attribute_id = (
                 SELECT id FROM iksula_class_attributes WHERE attribute_code = $2
               )""",
            product_id, attribute_code,
        )

        return {"status": "overridden", "attribute_code": attribute_code}


dq_client = DQClient()
