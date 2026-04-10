import os, httpx
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta

router = APIRouter()
SHOPIFY_URL = f"https://{os.getenv('SHOPIFY_STORE_URL')}/admin/api/{os.getenv('SHOPIFY_API_VERSION','2024-01')}"
HEADERS = {"X-Shopify-Access-Token": os.getenv("SHOPIFY_ACCESS_TOKEN",""), "Content-Type": "application/json"}

async def shopify_get(endpoint, params=None):
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{SHOPIFY_URL}/{endpoint}", headers=HEADERS, params=params or {})
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Shopify error: {resp.text}")
        return resp.json()

@router.get("/orders/today")
async def get_orders_today():
    today = datetime.utcnow().replace(hour=0,minute=0,second=0).isoformat()+"Z"
    data = await shopify_get("orders.json", {"status":"any","created_at_min":today,"limit":250,"fields":"id,created_at,total_price,financial_status,line_items"})
    orders = data.get("orders",[])
    revenue = sum(float(o["total_price"]) for o in orders)
    product_sales = {}
    for order in orders:
        for item in order.get("line_items",[]):
            pid = item["product_id"]
            if pid not in product_sales:
                product_sales[pid] = {"title":item["title"],"revenue":0,"units":0}
            product_sales[pid]["revenue"] += float(item["price"]) * item["quantity"]
            product_sales[pid]["units"] += item["quantity"]
    top = sorted([{"id":k,**v} for k,v in product_sales.items()], key=lambda x:x["revenue"], reverse=True)[:10]
    return {"date":datetime.utcnow().strftime("%Y-%m-%d"),"revenue":round(revenue,2),"order_count":len(orders),"aov":round(revenue/len(orders),2) if orders else 0,"top_products":top}

@router.get("/orders")
async def get_orders(days: int = 30):
    since = (datetime.utcnow()-timedelta(days=days)).isoformat()+"Z"
    data = await shopify_get("orders.json", {"status":"any","created_at_min":since,"limit":250,"fields":"id,created_at,total_price,financial_status"})
    orders = data.get("orders",[])
    revenue = sum(float(o["total_price"]) for o in orders)
    return {"orders":orders,"summary":{"total_revenue":round(revenue,2),"order_count":len(orders),"period_days":days}}

@router.get("/inventory")
async def get_inventory():
    try:
        locations = await shopify_get("locations.json")
        lid = locations["locations"][0]["id"]
        data = await shopify_get("inventory_levels.json", {"location_ids":lid,"limit":250})
        levels = data.get("inventory_levels",[])
        low = [l for l in levels if l.get("available",999) < 50]
        critical = [l for l in levels if l.get("available",999) < 15]
        return {"inventory_levels":levels,"low_stock_count":len(low),"critical_count":len(critical),"critical_items":critical}
    except Exception as e:
        return {"inventory_levels":[],"low_stock_count":0,"critical_count":0,"critical_items":[],"error":str(e)}

@router.get("/products")
async def get_products():
    data = await shopify_get("products.json", {"limit":100,"status":"active"})
    return {"products":data.get("products",[])}

@router.get("/revenue/range")
async def get_revenue_range(days: int = 14):
    results = []
    async with httpx.AsyncClient(timeout=60) as client:
        for i in range(days-1,-1,-1):
            day = datetime.utcnow()-timedelta(days=i)
            resp = await client.get(f"{SHOPIFY_URL}/orders.json", headers=HEADERS,
                params={"status":"any","created_at_min":day.replace(hour=0,minute=0,second=0).isoformat()+"Z","created_at_max":day.replace(hour=23,minute=59,second=59).isoformat()+"Z","fields":"total_price","limit":250})
            if resp.status_code == 200:
                orders = resp.json().get("orders",[])
                results.append({"date":day.strftime("%Y-%m-%d"),"revenue":round(sum(float(o["total_price"]) for o in orders),2),"orders":len(orders)})
    return {"data":results,"period_days":days}
