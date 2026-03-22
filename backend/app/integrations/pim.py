"""PIM connectors — push published records to retailer PIM systems.

SiteOne: REST API push
THD: Batch XML submission
"""

import json
import logging
import httpx

from app.config import settings
from app.db.client import fetch_all, fetch_one, execute

logger = logging.getLogger(__name__)


class PIMConnector:
    """Base class for PIM integrations."""

    async def push_to_staging(self, product_id: str) -> dict:
        raise NotImplementedError

    async def push_to_production(self, product_id: str) -> dict:
        raise NotImplementedError

    async def check_status(self, submission_id: str) -> dict:
        raise NotImplementedError


class SiteOnePIM(PIMConnector):

    async def push_to_staging(self, product_id: str) -> dict:
        if not settings.siteone_pim_url:
            return {"status": "skipped", "message": "SiteOne PIM not configured"}

        # Get client-transformed values (Layer 2)
        product = await fetch_one("SELECT * FROM products WHERE id = $1::uuid", product_id)
        client_values = await fetch_all(
            """SELECT client_field_name, COALESCE(edited_value, client_value) as value
               FROM product_client_values WHERE product_id = $1::uuid
               ORDER BY (SELECT client_field_order FROM client_field_mappings WHERE id = field_mapping_id)""",
            product_id,
        )

        payload = {
            "template_version": "2.4",
            "product": {field["client_field_name"]: field["value"] for field in client_values},
            "metadata": {
                "pc2_product_id": product_id,
                "overall_confidence": product["overall_confidence"],
                "product_name": product["product_name"],
                "model_number": product["model_number"],
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{settings.siteone_pim_url}/products/stage",
                    headers={"Authorization": f"Bearer {settings.siteone_pim_key}", "Content-Type": "application/json"},
                    json=payload, timeout=30.0,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"SiteOne PIM push failed: {e}")
            return {"status": "error", "message": str(e)}


class THDPIM(PIMConnector):

    async def push_to_staging(self, product_id: str) -> dict:
        if not settings.thd_pim_url:
            return {"status": "skipped", "message": "THD PIM not configured"}

        client_values = await fetch_all(
            """SELECT client_field_name, COALESCE(edited_value, client_value) as value
               FROM product_client_values WHERE product_id = $1::uuid""",
            product_id,
        )

        # THD uses XML format
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<item>']
        for cv in client_values:
            tag = cv["client_field_name"].lower().replace(" ", "_").replace("(", "").replace(")", "")
            xml_lines.append(f'  <{tag}>{cv["value"]}</{tag}>')
        xml_lines.append('</item>')
        xml_body = "\n".join(xml_lines)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{settings.thd_pim_url}/items/submit",
                    headers={"Authorization": f"Bearer {settings.thd_pim_key}", "Content-Type": "application/xml"},
                    content=xml_body, timeout=30.0,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"THD PIM push failed: {e}")
            return {"status": "error", "message": str(e)}


# Factory
def get_pim_connector(client_code: str) -> PIMConnector:
    if client_code == "siteone":
        return SiteOnePIM()
    elif client_code == "thd":
        return THDPIM()
    else:
        return SiteOnePIM()  # Default
