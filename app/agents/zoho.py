import httpx, json
from datetime import datetime, timedelta
import http.client

from app.config import settings
from app.agents.postgres import PostgresAgent
from app.models.category import CategoryBase

class ZohoAgent:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.client_id = settings.ZOHO_CLIENT_ID
        self.client_secret = settings.ZOHO_CLIENT_SECRET
        self.redirect_uri = settings.ZOHO_REDIRECT_URI
        self.postgres_agent = PostgresAgent()
        
    async def get_access_token(self):
        if not self.access_token or not self.refresh_token:
            return {"error": "No access token or refresh token available"}
    
    async def get_access_and_refresh_token(self, code: str):
        async with httpx.AsyncClient() as client:
            print(settings.ZOHO_CLIENT_ID)
            response = await client.post(
                "https://accounts.zoho.eu/oauth/v2/token",
                data={
                    "code": code,
                    "client_id": settings.ZOHO_CLIENT_ID,
                    "client_secret": settings.ZOHO_CLIENT_SECRET,
                    "redirect_uri": settings.ZOHO_REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
            )
        
        response_data = response.json()
        
        print(response_data)
        
        if response.status_code != 200:
            return {"error": response_data}
        
        try:
            self.access_token = response_data["access_token"]
            self.refresh_token = response_data["refresh_token"]
            self.expires_at = datetime.now() + timedelta(seconds=response_data["expires_in"])
        except Exception as e:
            return {"error": str(e)}
        
        await self.postgres_agent.insert_oauth(self.access_token, self.refresh_token, self.expires_at)

        return {"access_token": self.access_token, "refresh_token": self.refresh_token, "expires_at": self.expires_at}
    
    async def get_access_token_from_refresh_token(self, refresh_token: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://accounts.zoho.eu/oauth/v2/token",
                data={
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "refresh_token"
                }
            )
        
        response_data = response.json()
        
        print(response_data)
        
        if response.status_code != 200:
            return {"error": response_data}
        
        self.access_token = response_data["access_token"]
        self.expires_at = datetime.now() + timedelta(seconds=response_data["expires_in"])
        
        result = await self.postgres_agent.update_oauth(self.access_token, refresh_token, self.expires_at)
        
        if not result:
            return {"error": "Failed to update OAuth token"}
        
        return result
    
    async def get_access_token(self):
        oauth_token = await self.postgres_agent.get_oauth()
        
        if not oauth_token:
            return {"error": "No OAuth token available"}
        
        if oauth_token.expires_at < datetime.now():
            new_oauth_token = await self.get_access_token_from_refresh_token(oauth_token.refresh_token)
            if "error" in new_oauth_token:
                return {"error": new_oauth_token["error"]}
            oauth_token = new_oauth_token
            
        return oauth_token.access_token
    
    async def get_categories(self):
        print(settings.ZOHO_ORGANIZATION_ID)
        access_token = await self.get_access_token()
            
        conn = http.client.HTTPSConnection("www.zohoapis.eu")

        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }

        conn.request("GET", f"/inventory/v1/categories?organization_id={settings.ZOHO_ORGANIZATION_ID}", headers=headers)

        res = conn.getresponse()
        data = res.read()
        json_data = data.decode('utf-8')  # Convert bytes to string
        return json.loads(json_data)
    
    async def create_category(self, category: CategoryBase):
        access_token = await self.get_access_token()
            
        conn = http.client.HTTPSConnection("www.zohoapis.eu")
        
        payload = json.dumps({
            "name": category.name,
            "url": category.url,
            "parent_category_id": category.zoho_parent_id
        })

        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }

        conn.request("POST", f"/inventory/v1/categories?organization_id={settings.ZOHO_ORGANIZATION_ID}", payload, headers)

        res = conn.getresponse()
        data = res.read()
        json_data = data.decode('utf-8')  # Convert bytes to string
        return json.loads(json_data)
        
        