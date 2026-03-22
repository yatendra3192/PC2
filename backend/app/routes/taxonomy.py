import json
from fastapi import APIRouter, Depends

from app.db.client import fetch_all, fetch_one
from app.auth.dependencies import get_current_user
from app.models.user import TokenPayload
from app.models.taxonomy import TaxonomyNode, IksulaClassAttribute, IksulaAllowedValue

router = APIRouter()


@router.get("/tree", response_model=list[TaxonomyNode])
async def get_taxonomy_tree(_: TokenPayload = Depends(get_current_user)):
    rows = await fetch_all("SELECT * FROM taxonomy_nodes WHERE is_active = true ORDER BY full_path")
    nodes = {str(r["id"]): TaxonomyNode(
        id=str(r["id"]),
        parent_id=str(r["parent_id"]) if r["parent_id"] else None,
        level=r["level"],
        code=r["code"],
        name=r["name"],
        full_path=r["full_path"],
    ) for r in rows}

    # Build tree
    roots = []
    for node in nodes.values():
        if node.parent_id and node.parent_id in nodes:
            nodes[node.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


@router.get("/{node_id}/attributes", response_model=list[IksulaClassAttribute])
async def get_class_attributes(node_id: str, _: TokenPayload = Depends(get_current_user)):
    rows = await fetch_all(
        "SELECT * FROM iksula_class_attributes WHERE taxonomy_node_id = $1::uuid ORDER BY display_order",
        node_id,
    )
    return [IksulaClassAttribute(
        id=str(r["id"]),
        taxonomy_node_id=str(r["taxonomy_node_id"]),
        attribute_code=r["attribute_code"],
        attribute_name=r["attribute_name"],
        attribute_group=r["attribute_group"],
        data_type=r["data_type"],
        unit=r["unit"],
        is_mandatory=r["is_mandatory"],
        display_order=r["display_order"],
        description=r["description"],
        validation_rule=json.loads(r["validation_rule"]) if r["validation_rule"] else None,
    ) for r in rows]


@router.get("/{node_id}/allowed-values/{attribute_id}", response_model=list[IksulaAllowedValue])
async def get_allowed_values(node_id: str, attribute_id: str, _: TokenPayload = Depends(get_current_user)):
    rows = await fetch_all(
        "SELECT * FROM iksula_allowed_values WHERE attribute_id = $1::uuid AND is_active = true ORDER BY sort_order",
        attribute_id,
    )
    return [IksulaAllowedValue(
        id=str(r["id"]),
        attribute_id=str(r["attribute_id"]),
        value_code=r["value_code"],
        value_label=r["value_label"],
        synonyms=r["synonyms"],
    ) for r in rows]
