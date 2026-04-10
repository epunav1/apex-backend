from fastapi import APIRouter
router = APIRouter()

@router.get("/orders/today")
async def get_orders():
    return {"orders":0,"revenue":0,"note":"Add TikTok keys to .env to connect"}
