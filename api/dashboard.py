import httpx, asyncio
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()
BASE = "http://localhost:8000/api"

async def fetch(http, url):
    try:
        r = await http.get(url, timeout=15)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

@router.get("/snapshot")
async def get_snapshot():
    async with httpx.AsyncClient() as http:
        results = await asyncio.gather(
            fetch(http, f"{BASE}/shopify/orders/today"),
            fetch(http, f"{BASE}/shopify/inventory"),
            fetch(http, f"{BASE}/trends/top?limit=5"),
            return_exceptions=True
        )
    shopify = results[0] if not isinstance(results[0], Exception) else {}
    inventory = results[1] if not isinstance(results[1], Exception) else {}
    trends = results[2] if not isinstance(results[2], Exception) else {}
    revenue = shopify.get("revenue", 0)
    orders = shopify.get("order_count", 0)
    aov = shopify.get("aov", 0)
    est_profit = revenue * 0.47
    alerts = []
    if inventory.get("critical_count", 0) > 0:
        alerts.append({"level":"yellow","type":"inventory","message":f"{inventory.get('critical_count')} products critically low","action":"Place reorder today"})
    return {"timestamp":datetime.utcnow().isoformat(),"metrics":{"revenue_today":round(revenue,2),"orders_today":orders,"aov":round(aov,2),"total_ad_spend":0,"avg_roas":0,"est_profit":round(est_profit,2),"profit_margin":47.0},"top_products":shopify.get("top_products",[])[:5],"ad_channels":[],"inventory":{"low_stock_count":inventory.get("low_stock_count",0),"critical_count":inventory.get("critical_count",0),"critical_items":inventory.get("critical_items",[])[:3]},"trends":trends.get("trends",[])[:5],"alerts":alerts}

@router.get("/metrics/range")
async def get_metrics_range(days: int = 14):
    async with httpx.AsyncClient() as http:
        r = await fetch(http, f"{BASE}/shopify/revenue/range?days={days}")
    return {"chart_data":r.get("data",[]),"period_days":days}
