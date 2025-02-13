import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.agents.zoho import ZohoAgent
from app.agents.wcm import WcmAgent
from app.config import settings
from app.sync.customer import sync_customers

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     customer_task = asyncio.create_task(sync_customers())
#     app.state.customer_task = customer_task
#     yield
#     customer_task.cancel()

app = FastAPI()

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

@app.get("/brands")
async def get_brands():
    result = await ZohoAgent().get_brands()
    
    return result

@app.get("/brands/json")
async def get_brands_json():
    result = await WcmAgent().json_brands()
    
    return result

@app.get("/customers")
async def get_customers():
    result = await ZohoAgent().get_customers()
    
    return result

@app.get("/customers/json")
async def get_customers_json():
    result = await WcmAgent().json_customers()
    
    return result

@app.get("/customers/count")
async def get_customers_count():
    with open("customers/real_customers.json", "r") as f:
        customers = json.load(f)
    
    return len(customers)

@app.get("/customers/real")
def get_customers_real():
    result = WcmAgent().filter_customers()
    
    return result

@app.get("/contact_persons")
async def get_contact_persons():
    result = await ZohoAgent().get_contact_persons()
    
    return result