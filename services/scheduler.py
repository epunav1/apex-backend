import asyncio, httpx, os
from datetime import datetime

BASE = "http://localhost:8000/api"

async def run_morning_briefing():
    print(f"[APEX] Generating morning briefing — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    async with httpx.AsyncClient(timeout=60) as http:
        try:
            r = await http.get(f"{BASE}/briefing/generate?save=true")
            if r.status_code == 200:
                print(f"[APEX] Briefing generated OK")
        except Exception as e:
            print(f"[APEX] Briefing error: {e}")

async def run_hourly_automations():
    print(f"[APEX] Running automations — {datetime.now().strftime('%H:%M')}")
    async with httpx.AsyncClient(timeout=30) as http:
        try:
            await http.post(f"{BASE}/automations/run")
        except Exception as e:
            print(f"[APEX] Automation error: {e}")

async def start_scheduler():
    print(f"[APEX] Scheduler started")

async def stop_scheduler():
    print(f"[APEX] Scheduler stopped")
