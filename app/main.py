import asyncio
import json, os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.agents.zoho import ZohoAgent
from app.config import settings
from app.sync.item import sync_unsynced_items
from app.sync.item_group import create_item_groups
from app.agents.wcm import WcmAgent

@asynccontextmanager
async def lifespan(app: FastAPI):
    variable_products_task = asyncio.create_task(create_item_groups())
    app.state.variable_products_task = variable_products_task
    yield
    variable_products_task.cancel()

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


@app.get("/products/delete")
async def delete_products():
    count = 0
    while True:
        file_path = f"zoho_items/items_{count}.json"
        if not os.path.exists(file_path):
            break
        
        os.remove(file_path)
        count += 1
        
    return {"message": f"{count} files deleted"}

@app.get("/item_groups")
async def get_item_groups():
    result = await ZohoAgent().get_item_groups()
    
    return result

@app.get("/item/{item_id}")
async def get_item(item_id: str):
    result = await ZohoAgent().get_item_by_id(item_id)
    
    return result

# @app.get("/products/rename")
# async def rename_products():
#     count = 0
#     while True:
#         file_path = f"products/renamed_products_{count}.json"
#         if not os.path.exists(file_path):
#             break
#         os.rename(file_path, f"products/products_{count}.json")
#         count += 1
#     return {"message": f"{count} files renamed"}
        
        