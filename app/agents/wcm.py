import asyncio, json, os
from woocommerce import API

from app.agents.postgres import PostgresAgent
from app.config import settings

class WcmAgent:
    def __init__(self):
        self.postgres_agent = PostgresAgent()
        self.wcapi = API(
            url=settings.WCM_URL,
            consumer_key=settings.WCM_CONSUMER_KEY,
            consumer_secret=settings.WCM_CONSUMER_SECRET,
            wp_api=True,
            version="wc/v3"
        )
        
    async def json_categories(self):
        categories = []
        page = 1
        per_page = 20
        
        while True:
            response = self.wcapi.get(
                "products/categories",
                params={
                    "per_page": per_page,
                    "page": page
                }
            )
            
            if response.status_code == 200:
                current_categories = response.json()
                if not current_categories:  # If no more categories are returned
                    break
                    
                categories.extend(current_categories)
                page += 1
            else:
                await asyncio.sleep(1)
                continue
        
        filename = "categories/categories.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(categories, f, indent=4, ensure_ascii=False)
            
        return f"Categories saved to {filename}"
    
    async def separate_categories(self):
        # Read the file using async with
        categories = None
        with open("categories/categories.json", "r") as f:
            categories = json.load(f)
            
        if not categories:
            return "No categories found"
            
        # Create a dictionary to store categories by their levels
        categories_by_level = {}
        
        # Helper function to determine category level
        def get_category_level(category, all_categories):
            level = 0
            current_cat = category
            while current_cat["parent"] != 0:
                level += 1
                # Find parent category
                parent = next((cat for cat in all_categories if cat["id"] == current_cat["parent"]), None)
                if parent is None:
                    break
                current_cat = parent
            return level
        
        # Group categories by their levels
        for category in categories:
            try:
                level = get_category_level(category, categories)
                if level not in categories_by_level:
                    categories_by_level[level] = []
                    
                categories_by_level[level].append({
                    "name": category["name"],
                    "woo_id": category["id"],
                    "woo_parent_id": category["parent"],
                    "description": category["description"],
                    "url": category["slug"]
                })
            except Exception as e:
                print(f"Error processing category {category['name']}: {str(e)}")
                continue
        
        # Save categories for each level
        for level, cats in categories_by_level.items():
            filename = f"categories/categories_level_{level}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(cats, f, indent=4, ensure_ascii=False)
            await asyncio.sleep(0)  # Yield control back to event loop
            
        return f"Categories separated by levels and saved to categories_level_[0-{max(categories_by_level.keys())}].json"
    
    async def json_brands(self):
        brands = []
        page = 1
        per_page = 20
        
        while True:
            response = self.wcapi.get(
                "products/brands",
                params={
                    "per_page": per_page,
                    "page": page
                }
            )
            
            if response.status_code == 200:
                current_brands = response.json()
                if not current_brands:  # If no more brands are returned
                    break
                    
                brands.extend(current_brands)
                page += 1
            else:
                await asyncio.sleep(1)
                continue
        
        filename = "brands/brands.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(brands, f, indent=4, ensure_ascii=False)
            
        return f"Brands saved to {filename}"
    
    async def json_customers(self):
        page = 1
        per_page = 20
        customers = []
        current_file_number = 1
        customers_per_file = 100
        
        while True:
            response = self.wcapi.get(
                "customers",
                params={
                    "per_page": per_page,
                    "page": page
                }
            )
            
            if response.status_code == 200:
                current_customers = response.json()
                if not current_customers:  # If no more customers are returned
                    break
                
                customers.extend(current_customers)
                
                # Write to file every 100 customers
                while len(customers) >= customers_per_file:
                    filename = f"customers/customers_{current_file_number}.json"
                    batch = customers[:customers_per_file]
                    customers = customers[customers_per_file:]
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(batch, f, indent=4, ensure_ascii=False)
                    
                    print(f"Saved {filename}")
                    current_file_number += 1
                
                page += 1
            else:
                await asyncio.sleep(1)
                continue
        
        # Write any remaining customers
        if customers:
            filename = f"customers/customers_{current_file_number}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(customers, f, indent=4, ensure_ascii=False)
            print(f"Saved {filename}")
            
        return f"Customers saved to customers_1.json through customers_{current_file_number}.json"
    
    def filter_customers(self):
        real_customers = []
        count = 1
        while True:
            
            if not os.path.exists(f"customers/customers_{count}.json"):
                break
            
            with open(f"customers/customers_{count}.json", "r") as f:
                customers = json.load(f)
            
            for customer in customers:
                if customer["first_name"] != "" or customer["last_name"] != "":
                    real_customers.append(customer)
                
            count += 1
                
        with open("customers/real_customers.json", "w", encoding="utf-8") as f:
            json.dump(real_customers, f, indent=4, ensure_ascii=False)
                
        return f"Real customers saved to customers/real_customers.json"
    
    async def json_products(self):
        products = []
        page = 1
        per_page = 20
        current_file_number = 1
        products_per_file = 100
        
        while True:
            response = self.wcapi.get(
                "products",
                params={
                    "per_page": per_page,
                    "page": page,
                    "status": "publish",
                    "type": "simple"
                }
            )
            
            if response.status_code == 200:
                current_products = response.json()
                if not current_products:
                    break
                
                products.extend(current_products)
                
                while len(products) >= products_per_file:
                    filename = f"products/products_{current_file_number}.json"
                    batch = products[:products_per_file]
                    products = products[products_per_file:]
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(batch, f, indent=4, ensure_ascii=False)
                    
                    print(f"Saved {filename}")
                    current_file_number += 1
                
                page += 1
            else:
                await asyncio.sleep(1)
                continue
        
        # Write any remaining products
        if products:
            filename = f"products/products_{current_file_number}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=4, ensure_ascii=False)
            print(f"Saved {filename}")
            
        return f"Products saved to products_1.json through products_{current_file_number}.json"
