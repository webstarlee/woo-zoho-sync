import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.agents.zoho import ZohoAgent
from app.config import settings
from app.sync.item import create_items

@asynccontextmanager
async def lifespan(app: FastAPI):
    item_task = asyncio.create_task(create_items())
    app.state.item_task = item_task
    yield
    item_task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/oauth/callback")
async def oauth_callback(request: Request):
    code = request.query_params.get('code')
    if not code:
        return {"error": "No code provided"}
    
    result = await ZohoAgent().get_access_and_refresh_token(code)
    
    if result.get("error"):
        return {"error": result.get("error")}
    
    return {"access_token": result.get("access_token"), "refresh_token": result.get("refresh_token"), "expires_at": result.get("expires_at")}

@app.get("/refresh")
def refresh():
    result = settings.refresh()
    
    return result

@app.get("/items")
async def get_items():
    result = await ZohoAgent().get_items()
    
    return result

@app.get("/taxes")
async def get_taxes():
    result = await ZohoAgent().get_taxes()
    
    taxes = []
    
    for tax in result['taxes']:
        taxes.append({
            'id': tax['tax_id'],
            'name': tax['tax_name'],
            'rate': tax['tax_percentage']
        })
    
    with open('taxes.json', 'w') as f:
        json.dump(taxes, f, indent=4, ensure_ascii=False)
    return taxes
