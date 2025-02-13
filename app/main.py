from fastapi import FastAPI, Request
from app.agents.zoho import ZohoAgent
from app.config import settings

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

@app.get("/categories")
async def get_categories():
    result = await ZohoAgent().get_categories()
    
    return result

@app.get("/refresh")
def refresh():
    result = settings.refresh()
    
    return result

@app.post("/categories")
async def create_category(request: Request):
    data = await request.json()
    name = data.get('name')
    
    result = await ZohoAgent().create_category(name)
    
    return result