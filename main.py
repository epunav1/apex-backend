"""
APEX — Personal E-Commerce OS
FastAPI Backend
Run: uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

from api.shopify import router as shopify_router
from api.meta import router as meta_router
from api.google_ads import router as google_router
from api.tiktok import router as tiktok_router
from api.klaviyo import router as klaviyo_router
from api.trends import router as trends_router
from api.briefing import router as briefing_router
from api.automations import router as automations_router
from api.dashboard import router as dashboard_router
from api.orders import router as orders_router
from api.token_refresh import router as token_refresh_router

app = FastAPI(title="APEX — Personal E-Commerce OS", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router,   prefix="/api/dashboard",   tags=["Dashboard"])
app.include_router(shopify_router,     prefix="/api/shopify",     tags=["Shopify"])
app.include_router(meta_router,        prefix="/api/meta",        tags=["Meta Ads"])
app.include_router(google_router,      prefix="/api/google",      tags=["Google Ads"])
app.include_router(tiktok_router,      prefix="/api/tiktok",      tags=["TikTok"])
app.include_router(klaviyo_router,     prefix="/api/klaviyo",     tags=["Klaviyo"])
app.include_router(trends_router,      prefix="/api/trends",      tags=["Trends"])
app.include_router(briefing_router,    prefix="/api/briefing",    tags=["Briefings"])
app.include_router(automations_router, prefix="/api/automations", tags=["Automations"])
app.include_router(token_refresh_router, prefix="/api")
app.include_router(orders_router,     prefix="/api/orders",     tags=["Order Brain"])

@app.get("/")
async def root():
    return {"name": "APEX", "status": "online", "operator": "Victor Epunae"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}
