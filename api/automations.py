import httpx
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()
BASE = "https://apex-production-a997.up.railway.app/api"

RULES = [
    {"id":"roas_guard","name":"ROAS Drop Guard","trigger":"roas_drop","threshold":2.5,"actions":["alert","pause"],"active":True},
    {"id":"revenue_alert","name":"Revenue Gap Alert","trigger":"revenue_low","threshold":1000,"actions":["alert"],"active":True},
    {"id":"inventory_watch","name":"Inventory Watch","trigger":"stock_low","threshold_units":15,"actions":["alert","flag_reorder"],"active":True},
    {"id":"zero_orders","name":"Zero Orders Alert","trigger":"zero_orders","threshold":0,"actions":["alert"],"active":True},
    {"id":"daily_briefing","name":"Morning Briefing","trigger":"daily","time":"07:00","actions":["generate_briefing"],"active":True},
    {"id":"trend_spotter","name":"Trend Spotter","trigger":"trend_spike","threshold_score":75,"actions":["alert"],"active":True},
]

async def get_store_data():
    data = {}
    async with httpx.AsyncClient(timeout=15) as http:
        for key, path in [("orders","/shopify/orders/today"),("inventory","/shopify/inventory"),("trends","/trends/top?limit=5")]:
            try:
                r = await http.get(f"{BASE}{path}")
                data[key] = r.json() if r.status_code == 200 else {}
            except:
                data[key] = {}
    return data

async def evaluate_rules(data: dict) -> list:
    alerts = []
    orders = data.get("orders", {})
    inventory = data.get("inventory", {})
    revenue = orders.get("revenue", 0)
    order_count = orders.get("order_count", 0)
    roas = orders.get("roas", 0)

    for rule in RULES:
        if not rule["active"]:
            continue
        fired = False
        alert = None

        if rule["trigger"] == "zero_orders" and order_count == 0:
            fired = True
            alert = {"rule_id":rule["id"],"rule_name":rule["name"],"severity":"critical","message":f"ZERO ORDERS today — revenue ${revenue:,.2f}. Immediate action required.","trigger_value":order_count,"actions":rule["actions"]}

        elif rule["trigger"] == "revenue_low":
            hour = datetime.utcnow().hour
            expected = rule["threshold"] * max(hour, 1)
            if revenue < expected * 0.5 and hour >= 6:
                fired = True
                alert = {"rule_id":rule["id"],"rule_name":rule["name"],"severity":"warning","message":f"Revenue gap: ${revenue:,.2f} vs expected ~${expected:,.2f} by hour {hour}.","trigger_value":revenue,"actions":rule["actions"]}

        elif rule["trigger"] == "roas_drop" and roas > 0 and roas < rule["threshold"]:
            fired = True
            alert = {"rule_id":rule["id"],"rule_name":rule["name"],"severity":"critical","message":f"ROAS {roas:.2f}x below {rule['threshold']}x floor. Pause underperforming campaigns.","trigger_value":roas,"actions":rule["actions"]}

        elif rule["trigger"] == "stock_low":
            critical = inventory.get("critical_items", [])
            if critical:
                fired = True
                alert = {"rule_id":rule["id"],"rule_name":rule["name"],"severity":"warning","message":f"{len(critical)} product(s) critically low: {[i.get('title','?') for i in critical[:3]]}","trigger_value":len(critical),"actions":rule["actions"]}

        if fired and alert:
            alerts.append(alert)
            try:
                from db import log_automation
                await log_automation(rule_name=rule["name"], trigger_value=float(alert.get("trigger_value",0)), action_taken=alert["message"])
            except Exception as e:
                print(f"Log failed: {e}")

    return alerts

@router.post("/run")
async def run_automations():
    data = await get_store_data()
    alerts = await evaluate_rules(data)
    return {"ran_at":datetime.utcnow().isoformat(),"rules_checked":len([r for r in RULES if r["active"]]),"alerts_fired":len(alerts),"alerts":alerts,"store_snapshot":{"revenue":data.get("orders",{}).get("revenue",0),"orders":data.get("orders",{}).get("order_count",0),"roas":data.get("orders",{}).get("roas",0)}}

@router.get("/rules")
async def get_rules():
    return {"rules":RULES,"active_count":sum(1 for r in RULES if r["active"])}

@router.get("/log")
async def get_log():
    try:
        key = os.getenv("SUPABASE_SERVICE_KEY","")
        url = os.getenv("SUPABASE_URL","")
        if not key or not url:
            return {"log":[],"message":"Supabase not configured"}
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{url}/rest/v1/automation_log",headers={"apikey":key,"Authorization":f"Bearer {key}"},params={"order":"created_at.desc","limit":50})
            if r.status_code == 200:
                return {"log":r.json(),"count":len(r.json())}
    except Exception as e:
        return {"log":[],"error":str(e)}
    return {"log":[]}
