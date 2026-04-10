from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

TRENDS = [
    {"rank":1,"name":"Wireless Charging Pad","category":"Electronics","score":92,"velocity":"+34%","source":"tiktok","tag":"electronics"},
    {"rank":2,"name":"Home Office Setup","category":"Home","score":87,"velocity":"+21%","source":"google","tag":"home"},
    {"rank":3,"name":"Resistance Bands","category":"Fitness","score":81,"velocity":"+18%","source":"amazon","tag":"fitness"},
    {"rank":4,"name":"Gaming Accessories","category":"Gaming","score":74,"velocity":"+12%","source":"tiktok","tag":"gaming"},
    {"rank":5,"name":"Eco Skincare","category":"Beauty","score":69,"velocity":"+9%","source":"instagram","tag":"beauty"},
    {"rank":6,"name":"Open-Ear Headphones","category":"Electronics","score":66,"velocity":"+89%","source":"tiktok","tag":"electronics"},
]

@router.get("/top")
async def get_top(limit: int = 10, category: str = None):
    t = TRENDS if not category else [x for x in TRENDS if x["tag"]==category.lower()]
    return {"trends":t[:limit],"total":len(t),"last_updated":datetime.utcnow().isoformat()}

@router.get("/rising")
async def get_rising():
    rising = [t for t in TRENDS if int(t["velocity"].replace("+","").replace("%","")) >= 50]
    return {"rising":rising}
