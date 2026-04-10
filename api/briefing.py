import os, httpx
import anthropic
from fastapi import APIRouter
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

router = APIRouter()

async def gather_context():
    base = "http://localhost:8000/api"
    ctx = {}
    async with httpx.AsyncClient(timeout=20) as http:
        for key, url in [("shopify", f"{base}/shopify/orders/today"), ("inventory", f"{base}/shopify/inventory"), ("trends", f"{base}/trends/top?limit=5")]:
            try:
                r = await http.get(url)
                ctx[key] = r.json() if r.status_code == 200 else {}
            except:
                ctx[key] = {}
    return ctx

@router.get("/generate")
async def generate_briefing():
    ctx = await gather_context()
    shopify = ctx.get("shopify", {})
    inventory = ctx.get("inventory", {})
    trends = ctx.get("trends", {})
    prompt = f"""You are APEX AI, Victor Epunae's personal e-commerce intelligence system.
Today is {datetime.utcnow().strftime("%A, %B %d, %Y")}.
LIVE STORE DATA:
- Shopify revenue today: ${shopify.get('revenue', 0):,.2f}
- Orders today: {shopify.get('order_count', 0)}
- AOV: ${shopify.get('aov', 0):.2f}
Victor's targets: $8,000/day revenue, 2.5x ROAS floor.
Generate a sharp briefing with: headline, urgent actions, opportunities, best move today."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1200, messages=[{"role": "user", "content": prompt}])
    briefing_text = message.content[0].text
    context_snapshot = {"shopify_revenue": shopify.get("revenue", 0), "shopify_orders": shopify.get("order_count", 0), "critical_inventory": 0}
    try:
        from db import save_briefing
        await save_briefing(briefing_text, context_snapshot)
    except Exception as e:
        print(f"DB save failed: {e}")
    return {"date": datetime.utcnow().strftime("%Y-%m-%d"), "generated_at": datetime.utcnow().isoformat(), "briefing": briefing_text, "context_snapshot": context_snapshot, "saved_to_db": True}

@router.post("/ask")
async def ask_apex(question: str):
    ctx = await gather_context()
    shopify = ctx.get("shopify", {})
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    system = f"You are APEX AI — Victor Epunae's personal e-commerce OS. Store: ${shopify.get('revenue',0):,.0f} today, {shopify.get('order_count',0)} orders. Target: $8k/day."
    message = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=800, system=system, messages=[{"role": "user", "content": question}])
    return {"question": question, "answer": message.content[0].text, "timestamp": datetime.utcnow().isoformat()}

@router.get("/history")
async def get_history():
    try:
        from db import get_briefing_history
        briefings = await get_briefing_history(limit=7)
        return {"briefings": briefings, "count": len(briefings)}
    except Exception as e:
        return {"briefings": [], "error": str(e)}
# DB import added at bottom - will be patched
