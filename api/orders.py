"""
Order Brain — Shopify webhook receiver + CJ fulfillment orchestration
Routes:
  POST /api/orders/webhook          — Shopify calls this on every new order
  GET  /api/orders/jobs             — list fulfillment jobs
  POST /api/orders/fulfill/{id}     — manually trigger fulfillment for an order
  GET  /api/orders/mappings         — list product mappings
  POST /api/orders/mappings         — create/update a product mapping
  GET  /api/orders/cj/search        — search CJ catalog
  GET  /api/orders/cj/variants/{id} — get CJ product variants
"""
import hashlib
import hmac
import os
import json

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional

from db import (
    save_fulfillment_job,
    update_fulfillment_job,
    get_fulfillment_jobs,
    get_product_mapping,
    list_product_mappings,
    upsert_product_mapping,
)
from services.cj import create_order, get_order_status, search_product, get_product_variants

router = APIRouter()

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")


# ---------------------------------------------------------------------------
# HMAC verification
# ---------------------------------------------------------------------------

def _verify_shopify_hmac(body: bytes, signature: str) -> bool:
    """Return True if the request body matches the Shopify HMAC signature."""
    if not SHOPIFY_WEBHOOK_SECRET:
        return False
    expected = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    import base64
    expected_b64 = base64.b64encode(expected).decode()
    return hmac.compare_digest(expected_b64, signature)


# ---------------------------------------------------------------------------
# Fulfillment orchestration
# ---------------------------------------------------------------------------

async def _fulfill_order(order: dict) -> dict:
    """
    Core fulfillment logic:
    1. Extract line items from the Shopify order
    2. Look up CJ mapping for each Shopify variant
    3. Submit to CJ
    4. Persist result in Supabase
    """
    shopify_order_id = str(order["id"])
    shopify_order_name = order.get("name", f"#{shopify_order_id}")
    shipping_address = order.get("shipping_address", {})

    # Save initial pending job
    await save_fulfillment_job({
        "shopify_order_id": shopify_order_id,
        "shopify_order_name": shopify_order_name,
        "status": "pending",
        "cj_order_id": None,
        "items": json.dumps(order.get("line_items", [])),
        "error": None,
    })

    # Build CJ line items from mapped variants
    cj_items = []
    unmapped = []
    for item in order.get("line_items", []):
        variant_id = str(item.get("variant_id", ""))
        mapping = await get_product_mapping(variant_id)
        if mapping:
            cj_items.append({
                "cj_product_id": mapping["cj_product_id"],
                "cj_variant_id": mapping["cj_variant_id"],
                "quantity": item["quantity"],
                "shopify_title": item.get("title", ""),
            })
        else:
            unmapped.append(item.get("title", variant_id))

    if not cj_items:
        error_msg = f"No CJ mappings found for variants: {unmapped}"
        await update_fulfillment_job(shopify_order_id, {
            "status": "failed",
            "error": error_msg,
        })
        return {"status": "failed", "error": error_msg, "shopify_order_id": shopify_order_id}

    # Submit to CJ
    try:
        result = await create_order(
            shopify_order_id=shopify_order_id,
            shopify_order_name=shopify_order_name,
            shipping_address=shipping_address,
            line_items=cj_items,
        )

        if result.get("result"):
            cj_order_id = result.get("data", {}).get("orderId", "")
            await update_fulfillment_job(shopify_order_id, {
                "status": "submitted",
                "cj_order_id": cj_order_id,
            })
            return {
                "status": "submitted",
                "shopify_order_id": shopify_order_id,
                "shopify_order_name": shopify_order_name,
                "cj_order_id": cj_order_id,
                "unmapped_items": unmapped,
            }
        else:
            error_msg = result.get("message", "CJ returned result=false")
            await update_fulfillment_job(shopify_order_id, {
                "status": "failed",
                "error": error_msg,
            })
            return {"status": "failed", "error": error_msg, "shopify_order_id": shopify_order_id}

    except Exception as e:
        error_msg = str(e)
        await update_fulfillment_job(shopify_order_id, {
            "status": "failed",
            "error": error_msg,
        })
        return {"status": "failed", "error": error_msg, "shopify_order_id": shopify_order_id}


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def shopify_order_webhook(
    request: Request,
    x_shopify_hmac_sha256: Optional[str] = Header(None),
):
    """
    Shopify sends a POST here for every new paid order.
    Verifies HMAC, then triggers CJ fulfillment automatically.
    """
    body = await request.body()

    if x_shopify_hmac_sha256:
        if not _verify_shopify_hmac(body, x_shopify_hmac_sha256):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    elif SHOPIFY_WEBHOOK_SECRET:
        # Secret is configured but no signature header — reject
        raise HTTPException(status_code=401, detail="Missing HMAC signature")

    try:
        order = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Only fulfill paid orders
    financial_status = order.get("financial_status", "")
    if financial_status not in ("paid", "partially_paid"):
        return {"received": True, "action": "skipped", "reason": f"financial_status={financial_status}"}

    result = await _fulfill_order(order)
    return {"received": True, "action": "fulfill_attempted", **result}


# ---------------------------------------------------------------------------
# Manual fulfillment trigger
# ---------------------------------------------------------------------------

@router.post("/fulfill/{shopify_order_id}")
async def manual_fulfill(shopify_order_id: str):
    """Manually trigger fulfillment for a specific Shopify order ID."""
    import httpx as _httpx
    SHOPIFY_URL = f"https://{os.getenv('SHOPIFY_STORE_URL')}/admin/api/{os.getenv('SHOPIFY_API_VERSION', '2024-01')}"
    HEADERS = {
        "X-Shopify-Access-Token": os.getenv("SHOPIFY_ACCESS_TOKEN", ""),
        "Content-Type": "application/json",
    }
    async with _httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{SHOPIFY_URL}/orders/{shopify_order_id}.json",
            headers=HEADERS,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Shopify: {resp.text}")
        order = resp.json().get("order", {})

    result = await _fulfill_order(order)
    return result


# ---------------------------------------------------------------------------
# Fulfillment job log
# ---------------------------------------------------------------------------

@router.get("/jobs")
async def list_jobs(limit: int = 50):
    jobs = await get_fulfillment_jobs(limit=limit)
    return {"jobs": jobs, "count": len(jobs)}


# ---------------------------------------------------------------------------
# Product mapping CRUD
# ---------------------------------------------------------------------------

class ProductMapping(BaseModel):
    shopify_variant_id: str
    shopify_product_id: str
    shopify_title: str
    cj_product_id: str
    cj_variant_id: str


@router.get("/mappings")
async def get_mappings():
    mappings = await list_product_mappings()
    return {"mappings": mappings, "count": len(mappings)}


@router.post("/mappings")
async def create_mapping(mapping: ProductMapping):
    ok = await upsert_product_mapping(mapping.model_dump())
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save mapping to Supabase")
    return {"saved": True, "mapping": mapping}


# ---------------------------------------------------------------------------
# CJ catalog helpers (for building mappings)
# ---------------------------------------------------------------------------

@router.get("/cj/search")
async def cj_search(q: str, page: int = 1, page_size: int = 20):
    """Search the CJ product catalog."""
    try:
        data = await search_product(keyword=q, page=page, page_size=page_size)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/cj/variants/{cj_product_id}")
async def cj_variants(cj_product_id: str):
    """Get variant list for a CJ product (gives you the vid needed for ordering)."""
    try:
        data = await get_product_variants(cj_product_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
