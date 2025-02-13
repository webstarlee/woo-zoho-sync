import json
import os, asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Request
from app.agents.zoho import ZohoAgent
from app.agents.wcm import WcmAgent
from app.agents.postgres import PostgresAgent
from app.config import settings
from app.models.category import CategoryBase

async def create_category():
    count = 0
    total_count = 0
    while True:
        filename = f"categories/categories_level_{count}.json"
        if not os.path.exists(filename):
            break
        
        with open(filename, 'r') as f:
            categories = json.load(f)
            
        for category in categories:
            if category["woo_parent_id"] == 0:
                category_base = CategoryBase(
                    name=category["name"],
                    woo_id=category["woo_id"],
                    woo_parent_id=category["woo_parent_id"],
                    description=category["description"],
                    url=category["url"],
                    zoho_id=None,
                    zoho_parent_id="-1"
                )
                result = await ZohoAgent().create_category(category_base)
                if result.get("category"):
                    category_base.zoho_id = result['category']['category_id']
                    category_base.zoho_parent_id = result['category']['parent_category_id']
                    await PostgresAgent().insert_category(category_base)
                    print(f"Created category {category['name']} with id {category_base.zoho_id}")
                
                total_count += 1
            else:
                parent_category = await PostgresAgent().get_category_by_woo_id(category["woo_parent_id"])
                if parent_category:
                    category_base = CategoryBase(
                        name=category["name"],
                        woo_id=category["woo_id"],
                        woo_parent_id=category["woo_parent_id"],
                        description=category["description"],
                        url=category["url"],
                        zoho_id=None,
                        zoho_parent_id=parent_category.zoho_id
                    )
                    result = await ZohoAgent().create_category(category_base)
                    if result.get("category"):
                        category_base.zoho_id = result['category']['category_id']
                        category_base.zoho_parent_id = result['category']['parent_category_id']
                        await PostgresAgent().insert_category(category_base)
                        print(f"Created category {category['name']} with id {category_base.zoho_id} deep {count}")
                    total_count += 1
                else:
                    category_base = CategoryBase(
                        name=category["name"],
                        woo_id=category["woo_id"],
                        woo_parent_id=category["woo_parent_id"],
                        description=category["description"],
                        url=category["url"],
                        zoho_id=None,
                        zoho_parent_id="-1"
                    )
                    result = await ZohoAgent().create_category(category_base)
                    if result.get("category"):
                        category_base.zoho_id = result['category']['category_id']
                        category_base.zoho_parent_id = result['category']['parent_category_id']
                        await PostgresAgent().insert_category(category_base)
                        print(f"Created category {category['name']} with id {category_base.zoho_id}")
                    total_count += 1
            
            
        count += 1
        print(f"{count} - Total count: {total_count}")
    
    print(f"Total count: {total_count}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    catetory_task = asyncio.create_task(create_category())
    app.state.category_task = catetory_task
    yield
    catetory_task.cancel()

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

@app.get("/categories")
async def get_categories():
    result = await ZohoAgent().get_categories()
    
    return result

@app.get("/refresh")
def refresh():
    result = settings.refresh()
    
    return result

@app.post("/categories")
async def create_new_category(request: Request):
    data = await request.json()
    name = data.get('name')
    
    result = await ZohoAgent().create_category(name)
    
    return result

@app.get("/categories/json")
async def get_json_categories():
    result = await WcmAgent().json_categories()
    
    return result

@app.get("/categories/separate")
async def get_top_categories():
    result = await WcmAgent().separate_categories()
    
    return result
            