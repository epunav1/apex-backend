import os, httpx
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()
TOKEN = os.getenv("META_ACCESS_TOKEN","")
AD_ACCOUNT = os.getenv("META_AD_ACCOUNT_ID","")

@router.get("/spend/today")
async def get_spend_today():
    if not TOKEN:
        return {"spend":0,"roas":0,"note":"Add META_ACCESS_TOKEN to .env"}
    return {"spend":0,"roas":0,"date":datetime.utcnow().strftime("%Y-%m-%d")}

@router.get("/campaigns/insights")
async def get_campaigns(days: int = 7):
    if not TOKEN:
        return {"campaigns":[],"summary":{"total_spend":0,"avg_roas":0},"note":"Add META_ACCESS_TOKEN to .env"}
    return {"campaigns":[],"summary":{"total_spend":0,"avg_roas":0}}

@router.get("/roas/check")
async def check_roas(floor: float = 2.5):
    return {"floor":floor,"breached":[],"breach_count":0,"alert_needed":False}
