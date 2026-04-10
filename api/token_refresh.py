import os, httpx
from fastapi import APIRouter

router = APIRouter()

@router.post("/token/refresh")
async def refresh_shopify_token():
    client_id = os.getenv("SHOPIFY_CLIENT_ID")
    client_secret = os.getenv("SHOPIFY_CLIENT_SECRET")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://shop-wit-sazy.myshopify.com/admin/oauth/access_token",
            json={"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"}
        )
        data = resp.json()
        new_token = data.get("access_token")
        if not new_token:
            return {"error": "Failed to refresh token", "detail": data}
        return {"status": "ok", "token_preview": new_token[:12] + "..."}
