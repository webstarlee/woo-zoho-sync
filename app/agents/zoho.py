import httpx, json, requests, io
from datetime import datetime, timedelta
import http.client

from app.config import settings
from app.agents.postgres import PostgresAgent
from app.models.category import CategoryBase
from app.schemas.customer import Customer
from app.schemas.item import Item
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
        
    async def get_brands(self):
        access_token = await self.get_access_token()
            
        conn = http.client.HTTPSConnection("www.zohoapis.eu")

        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }

        conn.request("GET", f"/inventory/v1/brands?organization_id={settings.ZOHO_ORGANIZATION_ID}", headers=headers)

        res = conn.getresponse()
        data = res.read()
        json_data = data.decode('utf-8')  # Convert bytes to string
        return json.loads(json_data)
    
    async def get_customers(self):
        access_token = await self.get_access_token()
        
        conn = http.client.HTTPSConnection("www.zohoapis.eu")
        
        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
        
        conn.request("GET", f"/inventory/v1/contacts?organization_id={settings.ZOHO_ORGANIZATION_ID}", headers=headers)
        
        res = conn.getresponse()
        data = res.read()
        json_data = data.decode('utf-8')  # Convert bytes to string
        return json.loads(json_data)
    
    async def create_customer(self, customer: Customer):
        print(customer)
        try:
            access_token = await self.get_access_token()
            
            conn = http.client.HTTPSConnection("www.zohoapis.eu")
            print(customer.billing_address)
            payload = json.dumps({
                "contact_name": customer.contact_name,
                "company_name": customer.company_name,
                "contact_type": customer.contact_type,
                "billing_address": {
                    "address": customer.billing_address.address,
                    "city": customer.billing_address.city,
                    "state": customer.billing_address.state,
                    "zip": customer.billing_address.zip,
                    "country": customer.billing_address.country
                },
                "shipping_address": {
                    "address": customer.shipping_address.address,
                    "city": customer.shipping_address.city,
                    "state": customer.shipping_address.state,
                    "zip": customer.shipping_address.zip,
                    "country": customer.shipping_address.country
                },
                "contact_persons": [{
                    "first_name": person.first_name,
                    "last_name": person.last_name,
                    "email": person.email,
                    "is_primary_contact": person.is_primary_contact
                } for person in customer.contact_persons]
            })
            
            print(payload)
            
            headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
            
            conn.request("POST", f"/inventory/v1/contacts?organization_id={settings.ZOHO_ORGANIZATION_ID}", payload, headers)
            
            res = conn.getresponse()
            data = res.read()
            json_data = data.decode('utf-8')  # Convert bytes to string
            
            print(json_data)
            return json.loads(json_data)
        
        except KeyError as e:
            print(f"Error: Missing required field in customer data: {e}")
            return {"error": str(e)}
    
    async def get_contact_persons(self):
        access_token = await self.get_access_token()
        
        conn = http.client.HTTPSConnection("www.zohoapis.eu")
        
        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
        
        conn.request("GET", f"/inventory/v1/contacts/686329000000279600/contactpersons?organization_id={settings.ZOHO_ORGANIZATION_ID}", headers=headers)
        
        res = conn.getresponse()
        data = res.read()
        json_data = data.decode('utf-8')  # Convert bytes to string
        return json.loads(json_data)
    
    async def get_items(self):
        print(settings.ZOHO_ORGANIZATION_ID)
        access_token = await self.get_access_token()
        
        conn = http.client.HTTPSConnection("www.zohoapis.eu")
        
        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
        
        conn.request("GET", f"/inventory/v1/items?organization_id={settings.ZOHO_ORGANIZATION_ID}", headers=headers)
        
        res = conn.getresponse()
        data = res.read()
        json_data = data.decode('utf-8')  # Convert bytes to string
        return json.loads(json_data)
    
    async def create_item(self, item: Item):
        access_token = await self.get_access_token()
        
        conn = http.client.HTTPSConnection("www.zohoapis.eu")
        
        payload = json.dumps(item.model_dump())
        
        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
        
        conn.request("POST", f"/inventory/v1/items?organization_id={settings.ZOHO_ORGANIZATION_ID}", payload, headers)
        
        res = conn.getresponse()
        status_code = res.status
        print(status_code)
        if status_code == 429:
            return {"limit_exceeded": True}
        else:
            data = res.read()
            json_data = data.decode('utf-8')  # Convert bytes to string
            return json.loads(json_data)
    
    async def upload_image(self, images: list, item_id: str):
        try:
            access_token = await self.get_access_token()
            conn = http.client.HTTPSConnection("www.zohoapis.eu")
            
            results = []
            # Handle each image separately
            for index, image in enumerate(images):
                try:
                    image_response = requests.get(image['src'])
                    image_response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    print(f"Error downloading image from {image['src']}: {str(e)}")
                    results.append({"error": f"Failed to download image {index + 1}: {str(e)}"})
                    continue
                
                image_data = image_response.content
                
                # Determine image format from URL or content type
                content_type = image_response.headers.get('content-type', '')
                if 'webp' in content_type.lower():
                    ext = 'webp'
                elif 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                    ext = 'jpg'
                elif 'png' in content_type.lower():
                    ext = 'png'
                else:
                    # Try to get extension from URL
                    url_ext = image['src'].split('.')[-1].lower()
                    if url_ext in ['jpg', 'jpeg', 'png', 'webp']:
                        ext = 'jpg' if url_ext == 'jpeg' else url_ext
                    else:
                        ext = 'jpg'  # default to jpg if format cannot be determined
                
                # Create multipart form data for each image
                boundary = b'boundary123'
                body = []
                
                body.extend([
                    b'--' + boundary,
                    f'Content-Disposition: form-data; name="image"; filename="item_{item_id}_{index + 1}.{ext}"'.encode(),
                    f'Content-Type: image/{ext}'.encode(),
                    b'',
                    image_data,
                ])
                
                body.extend([
                    b'--' + boundary + b'--',
                    b'',
                ])
                
                body = b'\r\n'.join(body)
                
                headers = {
                    'Authorization': f"Zoho-oauthtoken {access_token}",
                    'Content-Type': f'multipart/form-data; boundary={boundary.decode()}'
                }
                
                try:
                    conn.request("POST", 
                               f"/inventory/v1/items/{item_id}/images?organization_id={settings.ZOHO_ORGANIZATION_ID}", 
                               body=body,
                               headers=headers)
                    res = conn.getresponse()
                    data = res.read()
                    json_data = data.decode('utf-8')
                    
                    if res.status >= 400:
                        results.append({"error": f"Zoho API error for image {index + 1}: {json_data}"})
                    else:
                        results.append(json.loads(json_data))
                    
                except (http.client.HTTPException, json.JSONDecodeError) as e:
                    print(f"Error uploading image {index + 1} to Zoho: {str(e)}")
                    results.append({"error": f"Failed to upload image {index + 1}: {str(e)}"})
            
            return results
            
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}
    
    async def get_taxes(self):
        access_token = await self.get_access_token()
        
        conn = http.client.HTTPSConnection("www.zohoapis.eu")
        
        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
        
        conn.request("GET", f"/inventory/v1/settings/taxes?organization_id={settings.ZOHO_ORGANIZATION_ID}", headers=headers)
        
        res = conn.getresponse()
        data = res.read()
        json_data = data.decode('utf-8')  # Convert bytes to string
        return json.loads(json_data)
        