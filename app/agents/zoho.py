import httpx, json, requests, io
from datetime import datetime, timedelta
import http.client
from PIL import Image  # Add this import at the top of the file
from urllib.parse import urlencode  # Add this import at the top of the file

from app.config import settings
from app.agents.postgres import PostgresAgent
from app.models.category import CategoryBase
from app.schemas.customer import Customer
from app.schemas.item import Item
from app.schemas.item_group import ItemGroup
from app.schemas.order import Order
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
        try:
            access_token = await self.get_access_token()
            
            conn = http.client.HTTPSConnection("www.zohoapis.eu")
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
            
            headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
            
            conn.request("POST", f"/inventory/v1/contacts?organization_id={settings.ZOHO_ORGANIZATION_ID}", payload, headers)
            
            res = conn.getresponse()
            data = res.read()
            json_data = data.decode('utf-8')  # Convert bytes to string
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
        page = 1
        per_page = 100  # Items per page
        file_number = 0
        
        while True:
            access_token = await self.get_access_token()
            conn = http.client.HTTPSConnection("www.zohoapis.eu")
            
            headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
            
            conn.request("GET", f"/inventory/v1/items?organization_id={settings.ZOHO_ORGANIZATION_ID}&page={page}&per_page={per_page}", headers=headers)
            
            res = conn.getresponse()
            data = res.read()
            json_data = json.loads(data.decode('utf-8'))
            
            # Check if we have items in the response
            if 'items' not in json_data or not json_data['items']:
                break
                
            # Save current batch to a JSON file
            filename = f"zoho_items/items_{file_number}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data['items'], f, indent=4, ensure_ascii=False)
                
            print(f"Saved batch {file_number} with {len(json_data['items'])} items to {filename}")
            
            # Check if we've reached the last page
            if len(json_data['items']) < per_page:
                break
                
            page += 1
            file_number += 1
            
        print(f"Successfully saved {file_number} batches of items")
    
    async def create_item(self, item: Item):
        access_token = await self.get_access_token()
        
        conn = http.client.HTTPSConnection("www.zohoapis.eu")
        
        payload = json.dumps(item.model_dump())
        
        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
        
        conn.request("POST", f"/inventory/v1/items?organization_id={settings.ZOHO_ORGANIZATION_ID}", payload, headers)
        
        res = conn.getresponse()
        status_code = res.status
        if status_code == 429:
            return {"limit_exceeded": True}
        else:
            data = res.read()
            json_data = data.decode('utf-8')  # Convert bytes to string
            return json.loads(json_data)
    
    async def upload_image(self, images: list, item_id: str):
        try:
            access_token = await self.get_access_token()
            results = []
            
            async with httpx.AsyncClient() as client:
                for index, image in enumerate(images):
                    try:
                        # Download image
                        response = await client.get(image['src'])
                        response.raise_for_status()
                        image_data = response.content
                        content_type = response.headers.get('content-type', '').lower()
                        url_lower = image['src'].lower()

                        # Determine image format
                        if 'jpeg' in content_type or 'jpg' in content_type or url_lower.endswith(('.jpg', '.jpeg')):
                            ext = 'jpg'
                        elif 'png' in content_type or url_lower.endswith('.png'):
                            ext = 'png'
                        else:
                            # Convert other formats (including WebP) to JPG
                            try:
                                image_buffer = io.BytesIO(image_data)
                                if url_lower.endswith('.avif'):
                                    try:
                                        import pillow_avif  # Required for AVIF support
                                        img = Image.open(image_buffer)
                                    except ImportError:
                                        results.append({"error": f"AVIF support not available for image {index + 1}"})
                                        continue
                                else:
                                    img = Image.open(image_buffer)

                                # Convert to RGB and handle alpha channel
                                if img.mode in ('RGBA', 'LA'):
                                    background = Image.new('RGB', img.size, (255, 255, 255))
                                    background.paste(img, mask=img.split()[-1])
                                    img = background
                                elif img.mode != 'RGB':
                                    img = img.convert('RGB')

                                output_buffer = io.BytesIO()
                                img.save(output_buffer, format='JPEG', quality=85, optimize=True)
                                image_data = output_buffer.getvalue()
                                ext = 'jpg'
                                
                            except Exception as e:
                                results.append({"error": f"Failed to convert image {index + 1}: {str(e)}"})
                                continue

                        # Prepare multipart form data
                        files = {
                            'image': (
                                f'item_{item_id}_{index + 1}.{ext}',
                                image_data,
                                f'image/{ext}'
                            )
                        }
                        
                        # Upload to Zoho
                        upload_response = await client.post(
                            f"https://www.zohoapis.eu/inventory/v1/items/{item_id}/images",
                            params={'organization_id': settings.ZOHO_ORGANIZATION_ID},
                            headers={'Authorization': f"Zoho-oauthtoken {access_token}"},
                            files=files
                        )

                        if upload_response.status_code >= 400:
                            results.append({
                                "error": f"Zoho API error for image {index + 1}: {upload_response.text}"
                            })
                        else:
                            results.append(upload_response.json())

                    except httpx.RequestError as e:
                        results.append({"error": f"Failed to process image {index + 1}: {str(e)}"})

            return results

        except Exception as e:
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
    
    async def get_item_groups(self):
        access_token = await self.get_access_token()
        
        conn = http.client.HTTPSConnection("www.zohoapis.eu")
        
        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
        
        conn.request("GET", f"/inventory/v1/itemgroups?organization_id={settings.ZOHO_ORGANIZATION_ID}", headers=headers)
        
        res = conn.getresponse()
        data = res.read()
        json_data = data.decode('utf-8')  # Convert bytes to string
        return json.loads(json_data)
    
    async def get_item_by_id(self, item_id: str):
        access_token = await self.get_access_token()
        
        conn = http.client.HTTPSConnection("www.zohoapis.eu")
        
        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
        
        conn.request("GET", f"/inventory/v1/items/{item_id}?organization_id={settings.ZOHO_ORGANIZATION_ID}", headers=headers)
        
        res = conn.getresponse()
        data = res.read()
        json_data = data.decode('utf-8')  # Convert bytes to string
        return json.loads(json_data)
    
    async def create_item_group(self, item_group: ItemGroup):
        access_token = await self.get_access_token()
        
        conn = http.client.HTTPSConnection("www.zohoapis.eu")
        
        payload = json.dumps({
            "group_name": item_group.group_name,
            "brand": item_group.brand,
            "manufacturer": item_group.manufacturer,
            "unit": item_group.unit,
            "description": item_group.description,
            "tax_id": item_group.tax_id,
            "attribute_name1": item_group.attribute_name1,
            "category_id": item_group.category_id,
            "items": [{
                "name": item.name,
                "rate": item.rate,
                "purchase_rate": item.purchase_rate,
                "initial_stock": item.initial_stock,
                "initial_stock_rate": item.initial_stock_rate,
                "stock_on_hand": item.stock_on_hand,
                "available_stock": item.available_stock,
                "actual_available_stock": item.actual_available_stock,
                "sku": item.sku,
                "attribute_option_name1": item.attribute_option_name1
            } for item in item_group.items],
        })
        
        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
        
        conn.request("POST", f"/inventory/v1/itemgroups?organization_id={settings.ZOHO_ORGANIZATION_ID}", payload, headers)
        
        res = conn.getresponse()
        status_code = res.status
        if status_code == 429:
            return {"limit_exceeded": True}
        else:
            data = res.read()
            json_data = data.decode('utf-8')
            return json.loads(json_data)
    
    async def list_customers(self, first_name: str, last_name: str):
        access_token = await self.get_access_token()
        
        conn = http.client.HTTPSConnection("www.zohoapis.eu")
        
        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
        
        # Properly encode query parameters
        params = {
            'organization_id': settings.ZOHO_ORGANIZATION_ID,
            'first_name': first_name,
            'last_name': last_name
        }
        query_params = urlencode(params)
        
        conn.request("GET", f"/inventory/v1/contacts?{query_params}", headers=headers)
        
        res = conn.getresponse()
        data = res.read()
        json_data = data.decode('utf-8')
        return json.loads(json_data)
    
    async def get_orders(self):
        access_token = await self.get_access_token()
        
        conn = http.client.HTTPSConnection("www.zohoapis.eu")
        
        headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
        
        conn.request("GET", f"/inventory/v1/salesorders?organization_id={settings.ZOHO_ORGANIZATION_ID}", headers=headers)
        
        res = conn.getresponse()
        data = res.read()
        json_data = data.decode('utf-8')
        return json.loads(json_data)
    
    async def create_order(self, order: Order):
        try:
            access_token = await self.get_access_token()
            
            conn = http.client.HTTPSConnection("www.zohoapis.eu")
            
            # Convert the order to a dictionary and remove None values
            order_dict = {k: v for k, v in order.model_dump().items() if v is not None}
            payload = json.dumps(order_dict)
            
            headers = {
                'Authorization': f"Zoho-oauthtoken {access_token}",
                'Content-Type': 'application/json'  # Add content type header
            }
            
            conn.request("POST", f"/inventory/v1/salesorders?organization_id={settings.ZOHO_ORGANIZATION_ID}", payload, headers)
            
            res = conn.getresponse()
            data = res.read()
            json_data = data.decode('utf-8')
            
            # Add error handling for non-200 responses
            if res.status >= 400:
                print(f"Zoho API error: Status {res.status}, Response: {json_data}")
                return None
            
            return json.loads(json_data)
        except Exception as e:
            print(f"Error creating order in Zoho: {str(e)}")
            return None
    
    async def mark_order_as_confirmed(self, order_id: str):
        print(order_id)
        try:
            access_token = await self.get_access_token()
            
            conn = http.client.HTTPSConnection("www.zohoapis.eu")
            
            headers = { 'Authorization': f"Zoho-oauthtoken {access_token}" }
            
            conn.request("POST", f"/inventory/v1/salesorders/{order_id}/status/confirmed?organization_id={settings.ZOHO_ORGANIZATION_ID}", headers=headers)
            
            res = conn.getresponse()
            data = res.read()
            json_data = data.decode('utf-8')
            
            if res.status >= 400:
                print(f"Zoho API error: Status {res.status}, Response: {json_data}")
                return {"error": f"Failed to confirm order: {json_data}"}
            
            return json.loads(json_data)
            
        except http.client.HTTPException as e:
            print(f"HTTP error occurred: {str(e)}")
            return {"error": f"HTTP error: {str(e)}"}
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            return {"error": f"Invalid JSON response: {str(e)}"}
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}