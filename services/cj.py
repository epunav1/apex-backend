"""
CJ Dropshipping API client
Docs: https://developers.cjdropshipping.com/api2.0/v1
Auth: apiKey (format: "CJUserNum@api@accesstoken") → accessToken (expires 12h) + refreshToken (expires 7d)
Env vars required: CJ_API_KEY
"""
import os
import time
import httpx
from typing import Optional

CJ_BASE = "https://developers.cjdropshipping.com/api2.0/v1"

# In-memory token cache (survives the process lifetime on Railway)
_token_cache: dict = {
    "access_token": None,
    "refresh_token": None,
    "expires_at": 0.0,
}


async def _get_access_token() -> str:
    """Return a valid access token, refreshing or re-authenticating as needed."""
    now = time.time()

    # Token still valid (with 5-min buffer)
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 300:
        return _token_cache["access_token"]

    # Try refresh first
    if _token_cache["refresh_token"]:
        token = await _refresh_token()
        if token:
            return token

    # Full re-auth
    return await _authenticate()


async def _authenticate() -> str:
    api_key = os.getenv("CJ_API_KEY", "")
    if not api_key:
        raise RuntimeError("CJ_API_KEY env var is required (format: CJUserNum@api@accesstoken)")

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{CJ_BASE}/authentication/getAccessToken",
            json={"apiKey": api_key},
        )
        resp.raise_for_status()
        data = resp.json()

    if not data.get("result"):
        raise RuntimeError(f"CJ auth failed: {data.get('message', 'unknown error')}")

    payload = data["data"]
    _token_cache["access_token"] = payload["accessToken"]
    _token_cache["refresh_token"] = payload["refreshToken"]
    # CJ tokens expire in 12 hours; store as epoch
    _token_cache["expires_at"] = time.time() + 12 * 3600
    return _token_cache["access_token"]


async def _refresh_token() -> Optional[str]:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{CJ_BASE}/authentication/refreshAccessToken",
            json={"refreshToken": _token_cache["refresh_token"]},
        )
        if resp.status_code != 200:
            return None
        data = resp.json()

    if not data.get("result"):
        return None

    payload = data["data"]
    _token_cache["access_token"] = payload["accessToken"]
    _token_cache["refresh_token"] = payload.get("refreshToken", _token_cache["refresh_token"])
    _token_cache["expires_at"] = time.time() + 12 * 3600
    return _token_cache["access_token"]


async def _cj_get(path: str, params: dict = None) -> dict:
    token = await _get_access_token()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{CJ_BASE}{path}",
            headers={"CJ-Access-Token": token},
            params=params or {},
        )
        resp.raise_for_status()
        return resp.json()


async def _cj_post(path: str, body: dict) -> dict:
    token = await _get_access_token()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{CJ_BASE}{path}",
            headers={"CJ-Access-Token": token, "Content-Type": "application/json"},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def search_product(keyword: str, page: int = 1, page_size: int = 20) -> dict:
    """Search CJ product catalog by keyword."""
    data = await _cj_get(
        "/product/list",
        params={"productNameEn": keyword, "pageNum": page, "pageSize": page_size},
    )
    return data


async def get_product_variants(cj_product_id: str) -> dict:
    """Get variant details (SKU/price/stock) for a CJ product."""
    data = await _cj_get("/product/variant/query", params={"pid": cj_product_id})
    return data


async def create_order(
    shopify_order_id: str,
    shopify_order_name: str,
    shipping_address: dict,
    line_items: list[dict],
) -> dict:
    """
    Submit a dropshipping order to CJ.

    line_items: list of {
        "cj_product_id": str,
        "cj_variant_id": str,
        "quantity": int,
        "shopify_title": str   # for logging only
    }

    Returns CJ API response dict.
    """
    products = [
        {
            "vid": item["cj_variant_id"],
            "quantity": item["quantity"],
        }
        for item in line_items
    ]

    payload = {
        "orderNumber": f"APEX-{shopify_order_id}",
        "shippingCountry": shipping_address.get("country_code", ""),
        "shippingAddress": shipping_address.get("address1", ""),
        "shippingAddress2": shipping_address.get("address2", ""),
        "shippingCity": shipping_address.get("city", ""),
        "shippingProvince": shipping_address.get("province", ""),
        "shippingZip": shipping_address.get("zip", ""),
        "shippingPhone": shipping_address.get("phone", ""),
        "shippingCustomerName": shipping_address.get("name", ""),
        "products": products,
        "remark": f"Shopify {shopify_order_name}",
    }

    data = await _cj_post("/shopping/order/createOrder", payload)
    return data


async def get_order_status(cj_order_id: str) -> dict:
    """Check the status of a previously submitted CJ order."""
    data = await _cj_get("/shopping/order/getOrderDetail", params={"orderId": cj_order_id})
    return data
