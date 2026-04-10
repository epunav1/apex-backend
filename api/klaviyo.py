from fastapi import APIRouter
router = APIRouter()

@router.get("/metrics")
async def get_metrics():
    return {"note":"Add KLAVIYO_PRIVATE_KEY to .env to connect"}
