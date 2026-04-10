import os
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/spend/today")
async def get_spend_today():
    if not os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"):
        return {"spend":0,"roas":0,"note":"Add Google Ads keys to .env"}
    return {"spend":0,"roas":0,"date":datetime.utcnow().strftime("%Y-%m-%d")}

@router.get("/campaigns")
async def get_campaigns(days: int = 7):
    return {"campaigns":[],"summary":{"total_spend":0,"avg_roas":0}}

@router.get("/roas/check")
async def check_roas(floor: float = 2.5):
    return {"floor":floor,"breached":[],"breach_count":0,"alert_needed":False}
