import asyncio, json, os
from woocommerce import API
from concurrent.futures import ThreadPoolExecutor

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
            version="wc/v3",
            timeout=30,
            verify=False
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
                    "type": "simple",
                    "search": "Produkt"
                }
            )
            
            if response.status_code == 200:
                current_products = response.json()
                if not current_products:
                    break
                
                products.extend(current_products)
                
                while len(products) >= products_per_file:
                    filename = f"wcm_products/wcm_products_{current_file_number}.json"
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
            filename = f"wcm_products/wcm_products_{current_file_number}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=4, ensure_ascii=False)
            print(f"Saved {filename}")
            
        return f"Products saved to wcm_products_1.json through wcm_products_{current_file_number}.json"
    
    async def clean_products(self):
        cleaned_products = []
        count = 1
        current_file_number = 1
        products_per_file = 100
        
        while True:
            if not os.path.exists(f"wcm_products/wcm_products_{count}.json"):
                break
            
            with open(f"wcm_products/wcm_products_{count}.json", "r") as f:
                products = json.load(f)
            
            for product in products:
                if product['sku'] == "":
                    continue
                # Remove unwanted fields
                product.pop('meta_data', None)
                product.pop('yoast_head', None)
                product.pop('price_html', None)
                product.pop('yoast_head_json', None)
                cleaned_products.append(product)
                
                # Write to file every 100 products
                while len(cleaned_products) >= products_per_file:
                    filename = f"wcm_products/cleaned_products_{current_file_number}.json"
                    batch = cleaned_products[:products_per_file]
                    cleaned_products = cleaned_products[products_per_file:]
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(batch, f, indent=4, ensure_ascii=False)
                    
                    print(f"Saved {filename}")
                    current_file_number += 1
            
            count += 1
        
        # Write any remaining products
        if cleaned_products:
            filename = f"wcm_products/cleaned_products_{current_file_number}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(cleaned_products, f, indent=4, ensure_ascii=False)
            print(f"Saved {filename}")
        
        return f"Products cleaned and saved to cleaned_products_1.json through cleaned_products_{current_file_number}.json"
    
    async def delete_products_files(self):
        count = 1
        while True:
            if not os.path.exists(f"wcm_products/cleaned_products_{count}.json"):
                break
            
            os.remove(f"wcm_products/cleaned_products_{count}.json")
            count += 1
    
    async def check_duplicates(self):
        all_products = []
        new_products = []
        seen_skus = set()
        
        # Read all products from JSON files
        count = 1
        while True:
            file_path = f"products/cleaned_products_{count}.json"
            if not os.path.exists(file_path):
                break
            
            with open(file_path, "r") as f:
                products = json.load(f)
                all_products.extend(products)
            count += 1
        
        # Check for duplicates and unique products
        print(f"Found {len(all_products)} products")
        for product in all_products:
            if not product["sku"] in seen_skus:
                seen_skus.add(product["sku"])
                new_products.append(product)
        
        def make_chunks(products, chunk_size):
            for i in range(0, len(products), chunk_size):
                yield products[i:i + chunk_size]
        
        chunks = list(make_chunks(new_products, 100))
        
        for index, chunk in enumerate(chunks):
            with open(f"products/new_products_{index}.json", "w", encoding="utf-8") as f:
                json.dump(chunk, f, indent=4, ensure_ascii=False)
            print(f"Saved chunk {index}")
        
        return f"New products saved to new_products_0.json through new_products_{len(chunks) - 1}.json"

    async def check_duplicates_names(self):
        all_products = []
        new_products = []
        seen_names = set()
        
        count = 0
        
        while True:
            file_path = f"products/new_products_{count}.json"
            if not os.path.exists(file_path):
                break
            
            with open(file_path, "r") as f:
                products = json.load(f)
                all_products.extend(products)
            count += 1
        
        print(f"Found {len(all_products)} products")
        for product in all_products:
            base_name = product["name"]
            counter = 2
            while product["name"] in seen_names:
                product["name"] = f"{base_name} ({counter})"
                counter += 1
            seen_names.add(product["name"])
            new_products.append(product)
        
        # Save updated products in chunks of 100
        def make_chunks(products, chunk_size):
            for i in range(0, len(products), chunk_size):
                yield products[i:i + chunk_size]
        
        chunks = list(make_chunks(new_products, 100))
        
        for index, chunk in enumerate(chunks):
            filename = f"products/renamed_products_{index}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(chunk, f, indent=4, ensure_ascii=False)
            print(f"Saved {filename}")
        
        return f"Renamed products saved to renamed_products_0.json through renamed_products_{len(chunks) - 1}.json"
    
    async def check_duplicates_total(self):
        count = 0
        seen_names = []
        duplicates = 0
        while True:
            file_path = f"products/products_{count}.json"
            if not os.path.exists(file_path):
                break
            
            with open(file_path, "r") as f:
                products = json.load(f)
            
            for product in products:
                if product["name"] in seen_names:
                    print(f"Duplicate name found: {product['name']}")
                    duplicates += 1
                else:
                    seen_names.append(product["name"])
            count += 1
            
        print(f"Checked {count} files, found {duplicates} duplicates")
    
    async def get_variable_products(self):
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
                    "type": "variable"
                }
            )
            
            if response.status_code == 200:
                current_products = response.json()
                if not current_products:
                    break
                
                products.extend(current_products)
                
                while len(products) >= products_per_file:
                    filename = f"variable_products/variable_products_{current_file_number}.json"
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
            filename = f"variable_products/variable_products_{current_file_number}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=4, ensure_ascii=False)
            print(f"Saved {filename}")
            
        print(f"Products saved to products_1.json through products_{current_file_number}.json")
    
    async def get_attributes(self):
        attributes = []
        page = 1
        per_page = 20
        current_file_number = 1
        attributes_per_file = 100
        
        while True:
            response = self.wcapi.get(
                "products/attributes",
                params={
                    "per_page": per_page,
                    "page": page
                }
            )
            
            if response.status_code == 200:
                current_attributes = response.json()
                if not current_attributes:
                    break
                    
                attributes.extend(current_attributes)
                
                while len(attributes) >= attributes_per_file:
                    filename = f"attributes/attributes_{current_file_number}.json"
                    batch = attributes[:attributes_per_file]
                    attributes = attributes[attributes_per_file:]
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(batch, f, indent=4, ensure_ascii=False)
                    
                    print(f"Saved {filename}")
                    current_file_number += 1
                
                page += 1
            else:
                await asyncio.sleep(1)
                continue
                    
        if attributes:
            filename = f"attributes/attributes_{current_file_number}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(attributes, f, indent=4, ensure_ascii=False)
            print(f"Saved {filename}")
            
        return f"Attributes saved to attributes_1.json through attributes_{current_file_number}.json"
    
    async def get_product_variations(self):
        print("Getting product variations")
        count = 1

        # Ensure variations directory exists
        os.makedirs("variations", exist_ok=True)
        
        while True:
            print(f"Getting variations for product {count}")
            file_path = f"variable_products/products_{count}.json"
            if not os.path.exists(file_path):
                print(f"File {file_path} does not exist")
                break
            
            print(f"File {file_path} exists")
            with open(file_path, "r") as f:
                products = json.load(f)
            
            for product in products:
                try:
                    response = self.wcapi.get(
                        f"products/{product['id']}/variations"
                    )
                    # Add delay to avoid rate limiting
                    await asyncio.sleep(0.5)  # 500ms delay between requests
                    
                    response.raise_for_status()  # Raise exception for bad status codes
                    variations = response.json()
                    
                    filename = f"variations/variations_{product['id']}.json"
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(variations, f, indent=4, ensure_ascii=False)
                    print(f"Saved variations for product {product['id']}")
                
                except Exception as e:
                    print(f"Error processing product {product['id']}: {str(e)}")
                    
            count += 1

    async def separate_wrong_products(self):
        count = 1
        wrong_products = []
        current_file_number = 1
        products_per_file = 100
        
        while True:
            file_path = f"wcm_products/wcm_products_{count}.json"
            if not os.path.exists(file_path):
                break
            
            with open(file_path, "r") as f:
                products = json.load(f)
            
            for product in products:
                if product["name"] == "Produkt":
                    print(f"Product {product['id']} is a wrong product")
                    wrong_products.append(product)
                    
                    # Write to file every 100 products
                    while len(wrong_products) >= products_per_file:
                        filename = f"wrong_products/wrong_products_{current_file_number}.json"
                        batch = wrong_products[:products_per_file]
                        wrong_products = wrong_products[products_per_file:]
                        
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(batch, f, indent=4, ensure_ascii=False)
                        
                        print(f"Saved {filename}")
                        current_file_number += 1
            
            count += 1
        
        # Write any remaining products
        if wrong_products:
            filename = f"wrong_products/wrong_products_{current_file_number}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(wrong_products, f, indent=4, ensure_ascii=False)
            print(f"Saved {filename}")
            
        return f"Wrong products saved to wrong_products_1.json through wrong_products_{current_file_number}.json"
    
    async def delete_wrong_products(self):
        try:
            print(self.wcapi.delete("products/118506", params={"force": True}).json())
        except Exception as e:
            print(e)
        return
    
        count = 1
        deleted_count = 0
        error_count = 0
        executor = ThreadPoolExecutor()

        while True:
            file_path = f"wrong_products/wrong_products_{count}.json"
            if not os.path.exists(file_path):
                break

            try:
                with open(file_path, "r") as f:
                    products = json.load(f)

                for product in products:
                    if product["name"] == "Produkt":
                        max_retries = 3
                        retry_count = 0

                        while retry_count < max_retries:
                            try:
                                print(f"Deleting product {product['id']} (attempt {retry_count + 1})")

                                # Run blocking `wcapi.delete(...)` in a separate thread
                                loop = asyncio.get_running_loop()
                                result = await loop.run_in_executor(
                                    executor, lambda: self.wcapi.delete(f"products/{product['id']}", params={"force": True})
                                )
                                
                                print(f"Response Status: {result.status_code}")
                                print(f"Response Headers: {result.headers}")
                                print(f"Response Text: {result.text}")

                                if result.status_code == 200:
                                    deleted_count += 1
                                    print(f"Successfully deleted product {product['id']}")
                                    await asyncio.sleep(2)  # Short delay after successful deletion
                                    break
                                else:
                                    print(f"Failed to delete product {product['id']}: Status {result.status_code}")
                                    await asyncio.sleep(5)  # Longer delay on failure
                                    retry_count += 1

                            except Exception as e:
                                print(f"Error deleting product {product['id']}: {str(e)}")
                                await asyncio.sleep(10)  # Longer delay on connection error
                                retry_count += 1
                                continue

                        if retry_count == max_retries:
                            error_count += 1
                            print(f"Failed to delete product {product['id']} after {max_retries} attempts")

            except Exception as e:
                print(f"Error reading file {file_path}: {str(e)}")

            count += 1

        return f"Process completed. Successfully deleted {deleted_count} products. Encountered {error_count} errors."

    async def post_test(self):
        data = {
            "name": "Clothing daniellee",
            "image": {
                "src": "http://demo.woothemes.com/woocommerce/wp-content/uploads/sites/56/2013/06/T_2_front.jpg"
            }
        }

        print(self.wcapi.post("products/categories", data).json())
        
    async def delete_cat_test(self):
        max_retries = 5  # Increased retries
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Add delay with exponential backoff
                await asyncio.sleep(2 ** retry_count)  # 1, 2, 4, 8, 16 seconds
                
                print(f"Attempt {retry_count + 1}: Trying to delete category 5248")
                response = self.wcapi.delete(
                    "products/categories/5248",
                    params={
                        "force": True,
                    }
                )
                
                if response.status_code == 200:
                    print("Successfully deleted category")
                    print(response.json())
                    return
                else:
                    print(f"Failed with status code: {response.status_code}")
                    print(f"Response: {response.text}")
                
            except ConnectionError as e:
                print(f"Connection error on attempt {retry_count + 1}: {str(e)}")
            except Exception as e:
                print(f"Unexpected error on attempt {retry_count + 1}: {str(e)}")
            
            retry_count += 1
                
        print("Failed to delete category after maximum retries")
        return
    
    async def get_orders(self):
        orders = []
        page = 1
        per_page = 20
        current_file_number = 1
        orders_per_file = 100
        
        while True:
            response = self.wcapi.get(
                "orders",
                params={
                    "per_page": per_page,
                    "page": page,
                    "status": "completed"
                }
            )
            
            if response.status_code == 200:
                current_orders = response.json()
                if not current_orders:  # If no more orders are returned
                    break
                
                orders.extend(current_orders)
                
                # Write to file every 100 orders
                while len(orders) >= orders_per_file:
                    filename = f"orders/orders_{current_file_number}.json"
                    batch = orders[:orders_per_file]
                    orders = orders[orders_per_file:]
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(batch, f, indent=4, ensure_ascii=False)
                    
                    print(f"Saved {filename}")
                    current_file_number += 1
                
                page += 1
            else:
                await asyncio.sleep(1)
                continue
        
        # Write any remaining orders
        if orders:
            filename = f"orders/orders_{current_file_number}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(orders, f, indent=4, ensure_ascii=False)
            print(f"Saved {filename}")
            
        return f"Orders saved to orders_1.json through orders_{current_file_number}.json"
