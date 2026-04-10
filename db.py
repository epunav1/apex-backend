import os
import json
from datetime import date, datetime
from typing import Optional
import httpx

# Supabase REST API approach - no asyncpg needed
SUPABASE_URL = "https://rsucihkeabqxeczbdcbn.supabase.co"

def get_supabase_key():
    return os.getenv("SUPABASE_SERVICE_KEY", "")

async def save_briefing(briefing_text: str, context: dict) -> bool:
    """Save a briefing to Supabase via REST API"""
    key = get_supabase_key()
    if not key:
        return False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/briefings",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "date": str(date.today()),
                    "briefing": briefing_text,
                    "shopify_revenue": context.get("shopify_revenue", 0),
                    "shopify_orders": context.get("shopify_orders", 0),
                }
            )
            return r.status_code in (200, 201)
    except:
        return False

async def get_briefing_history(limit: int = 7) -> list:
    """Get recent briefings from Supabase"""
    key = get_supabase_key()
    if not key:
        return []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/briefings",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                },
                params={
                    "order": "created_at.desc",
                    "limit": limit,
                    "select": "id,date,briefing,shopify_revenue,shopify_orders,created_at"
                }
            )
            if r.status_code == 200:
                return r.json()
    except:
        pass
    return []

async def save_metric_snapshot(metrics: dict) -> bool:
    """Save hourly metric snapshot"""
    key = get_supabase_key()
    if not key:
        return False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/metric_snapshots",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "snapshot_date": str(date.today()),
                    "shopify_revenue": metrics.get("shopify_revenue", 0),
                    "shopify_orders": metrics.get("shopify_orders", 0),
                    "shopify_aov": metrics.get("shopify_aov", 0),
                }
            )
            return r.status_code in (200, 201)
    except:
        return False

# ---------------------------------------------------------------------------
# Fulfillment jobs
# ---------------------------------------------------------------------------

async def save_fulfillment_job(job: dict) -> bool:
    """Insert a new fulfillment job record."""
    key = get_supabase_key()
    if not key:
        return False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/fulfillment_jobs",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json=job,
            )
            return r.status_code in (200, 201)
    except:
        return False


async def update_fulfillment_job(shopify_order_id: str, updates: dict) -> bool:
    """Patch a fulfillment job by shopify_order_id."""
    key = get_supabase_key()
    if not key:
        return False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.patch(
                f"{SUPABASE_URL}/rest/v1/fulfillment_jobs",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                params={"shopify_order_id": f"eq.{shopify_order_id}"},
                json={**updates, "updated_at": datetime.utcnow().isoformat()},
            )
            return r.status_code in (200, 204)
    except:
        return False


async def get_fulfillment_jobs(limit: int = 50) -> list:
    """Return recent fulfillment jobs."""
    key = get_supabase_key()
    if not key:
        return []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/fulfillment_jobs",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
                params={"order": "created_at.desc", "limit": limit},
            )
            if r.status_code == 200:
                return r.json()
    except:
        pass
    return []


# ---------------------------------------------------------------------------
# Product mappings (Shopify variant → CJ product/variant)
# ---------------------------------------------------------------------------

async def get_product_mapping(shopify_variant_id: str) -> Optional[dict]:
    """Look up a single product mapping by Shopify variant ID."""
    key = get_supabase_key()
    if not key:
        return None
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/product_mappings",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
                params={
                    "shopify_variant_id": f"eq.{shopify_variant_id}",
                    "limit": 1,
                },
            )
            if r.status_code == 200:
                rows = r.json()
                return rows[0] if rows else None
    except:
        pass
    return None


async def list_product_mappings() -> list:
    """Return all product mappings."""
    key = get_supabase_key()
    if not key:
        return []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/product_mappings",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
                params={"order": "created_at.desc"},
            )
            if r.status_code == 200:
                return r.json()
    except:
        pass
    return []


async def upsert_product_mapping(mapping: dict) -> bool:
    """Insert or update a product mapping (upsert on shopify_variant_id)."""
    key = get_supabase_key()
    if not key:
        return False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/product_mappings",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                },
                json=mapping,
            )
            return r.status_code in (200, 201)
    except:
        return False


async def log_automation(rule_name: str, trigger_value: float, action_taken: str) -> bool:
    """Log an automation execution"""
    key = get_supabase_key()
    if not key:
        return False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/automation_log",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "rule_name": rule_name,
                    "trigger_value": trigger_value,
                    "action_taken": action_taken,
                    "status": "executed"
                }
            )
            return r.status_code in (200, 201)
    except:
        return False
