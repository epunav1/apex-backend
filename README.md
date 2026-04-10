# APEX — Personal E-Commerce OS

## Your Keys (already configured in .env)
- Shopify: shop-wit-sazy.myshopify.com ✓
- Anthropic API: Configured ✓

## Run Locally
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Test it works
Open: http://localhost:8000/api/shopify/orders/today
Open: http://localhost:8000/api/briefing/generate
Open: http://localhost:8000/docs

## Deploy to Railway
1. Push this folder to a private GitHub repo
2. Connect repo to railway.app
3. Add env vars from .env in Railway dashboard
4. Done — APEX runs 24/7
