import os, json, requests
from bs4 import BeautifulSoup
from app.agents.zoho import ZohoAgent
from app.agents.postgres import PostgresAgent
from app.schemas.item import Item
from typing import List, Dict
from pathlib import Path
import unicodedata
from app.agents.open import OpenAgent

async def create_items():
    count = 87
    total_count = 8600
    errors = []
    limit_exceeded = False
    
    while True:
        if limit_exceeded:
            break
        try:
            filename = f"products/products_{count}.json"
            if not os.path.exists(filename):
                break
            
            with open(filename, 'r') as f:
                products = json.load(f)
                
            for product in products:
                if limit_exceeded:
                    break
                try:
                    if len(product["categories"]) > 0:
                        category_woo_id = product["categories"][0]["id"]
                        category = await PostgresAgent().get_category_by_woo_id(category_woo_id)
                    
                    if category:
                        category_id = category.zoho_id
                    else:
                        category_id = "-1"
                    
                    if len(product["brands"]) > 0:
                        brand = product["brands"][0]["name"]
                    else:
                        brand = "Eagle Fishing"
                    
                    if product["description"]:
                        soup = BeautifulSoup(product["description"], 'html.parser')
                        plain_description = soup.get_text(separator=' ').strip()
                        # Clean text of emojis and invalid characters
                        cleaned_description = unicodedata.normalize('NFKD', plain_description).encode('ascii', 'ignore').decode('ascii')
                        truncated_description = cleaned_description[:2000]
                    elif product["short_description"]:
                        soup = BeautifulSoup(product["short_description"], 'html.parser')
                        plain_description = soup.get_text(separator=' ').strip()
                        # Clean text of emojis and invalid characters
                        cleaned_description = unicodedata.normalize('NFKD', plain_description).encode('ascii', 'ignore').decode('ascii')
                        truncated_description = cleaned_description[:2000]
                    else:
                        truncated_description = ""
                    
                    try:
                        stock_qty = float(product["stock_quantity"])
                        stock_qty = max(0.0, stock_qty)
                    except (ValueError, TypeError):
                        stock_qty = 0.0
                    
                    available_stock = stock_qty
                    if product["stock_status"] == "instock":
                        available_stock = stock_qty
                    else:
                        available_stock = 0.0
                    
                    # Process price
                    try:
                        price = float(product["price"]) if product["price"] else 0.0
                    except (ValueError, TypeError):
                        price = 0.0
                    
                    item_base = Item(
                        name=product["name"],
                        item_name=product["name"],
                        category_id=category_id,
                        unit="pcs",
                        status="active",
                        description=truncated_description,
                        brand=brand,
                        manufacturer=brand,
                        rate=price,
                        tax_id="686329000000054249",
                        initial_stock=float(stock_qty),
                        stock_on_hand=float(stock_qty),
                        available_stock=float(available_stock),
                        actual_available_stock=float(available_stock),
                        purchase_rate=price,
                        item_type="inventory",
                        product_type="goods",
                        sku=product["sku"],
                        length=product["dimensions"]["length"],
                        width=product["dimensions"]["width"],
                        height=product["dimensions"]["height"],
                        weight=product["weight"],
                        weight_unit="kg",
                        dimension_unit="cm",
                        tags=product["tags"]
                    )
                    result = await ZohoAgent().create_item(item_base)
                    if result.get("limit_exceeded"):
                        limit_exceeded = True
                        break
                    if result.get("item") and len(product["images"]) > 0:
                        try:
                            print("uploading image")
                            await ZohoAgent().upload_image(product["images"], result['item']['item_id'])
                        except Exception as e:
                            print(f"Error uploading image: {str(e)}")
                            errors.append(f"Image upload error for product {product['name']}: {str(e)}")
                    else:
                        print("no image to upload")
                    
                    print("total count: ", total_count)
                    total_count += 1
                
                except Exception as e:
                    print(f"Error processing product {product.get('name', 'unknown')}: {str(e)}")
                    errors.append(f"Product error - {product.get('name', 'unknown')}: {str(e)}")
                    continue
            print(f"{count} - Total count: {total_count}")
            count += 1
        
        except Exception as e:
            print(f"Error processing file {filename}: {str(e)}")
            errors.append(f"File error - {filename}: {str(e)}")
            count += 1
            continue
    
    print(f"Total count: {total_count}")
    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(f"- {error}")

async def check_unsynced_items():
    unsynced_items = []
    count = 0
    wcm_products = []

    # Collect all WCM products
    while True:
        file_path = f"wcm_products/products_{count}.json"
        if not os.path.exists(file_path):
            break
        
        with open(file_path, "r") as f:
            products = json.load(f)
            wcm_products.extend(products)
        count += 1

    # Get all Zoho items
    zoho_item_names = []
    zoho_item_skus = []
    zoho_count = 0
    while True:
        file_path = f"zoho_items/items_{zoho_count}.json"
        if not os.path.exists(file_path):
            break
        
        with open(file_path, "r") as f:
            items = json.load(f)
            for item in items:
                zoho_item_names.append(item["name"])
                zoho_item_skus.append(item["sku"])
        zoho_count += 1

    print(f"Found {len(zoho_item_names)} items in Zoho")
    # Compare and find unsynced items
    for product in wcm_products:
        if product["name"] not in zoho_item_names or product["sku"] not in zoho_item_skus:
            unsynced_items.append(product)

    # Save unsynced items to JSON file
    if unsynced_items:
        with open("repairs/unsynced_items.json", "w") as f:
            json.dump(unsynced_items, f, indent=4, ensure_ascii=False)
        print(f"Found {len(unsynced_items)} unsynced items. Saved to unsynced_items.json")
    else:
        print("All items are synced")

async def load_json_files(base_path: str, file_prefix: str) -> List[dict]:
    """Helper function to load and combine JSON files from a directory."""
    count = 0
    combined_data = []
    while True:
        file_path = f"{base_path}/{file_prefix}_{count}.json"
        if not os.path.exists(file_path):
            break
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                combined_data.extend(data)
            count += 1
        except json.JSONDecodeError as e:
            print(f"Error reading {file_path}: {e}")
            break
    return combined_data

async def check_unsynced_item_images():
    # Create repairs directory if it doesn't exist
    Path("repairs").mkdir(exist_ok=True)
    
    try:
        # Load all products and items
        wcm_products = await load_json_files("wcm_products", "products")
        zoho_items = await load_json_files("zoho_items", "items")
        
        # Create lookup dictionary for zoho items
        zoho_items_dict = {item["name"]: item for item in zoho_items}
        
        # Find unsynced products with images
        unsynced_products = [
            {**product, "zoho_id": zoho_items_dict[product["name"]]["item_id"]}
            for product in wcm_products
            if product["name"] in zoho_items_dict
            and zoho_items_dict[product["name"]]["image_name"] == ""
            and product["images"]
        ]
        
        print(f"Found {len(unsynced_products)} unsynced item images")
        
        if unsynced_products:
            # Save in batches of 100
            BATCH_SIZE = 100
            total_files = (len(unsynced_products) + BATCH_SIZE - 1) // BATCH_SIZE
            
            for i in range(total_files):
                start_idx = i * BATCH_SIZE
                end_idx = min((i + 1) * BATCH_SIZE, len(unsynced_products))
                batch = unsynced_products[start_idx:end_idx]
                
                filename = f"repairs/unsynced_images_{i}.json"
                with open(filename, 'w') as f:
                    json.dump(batch, f, indent=4, ensure_ascii=False)
            
            print(f"Saved {len(unsynced_products)} products across {total_files} files in repairs/unsynced_images_*.json")
        else:
            print("No unsynced images found")
            
    except Exception as e:
        print(f"Error processing unsynced images: {str(e)}")

async def sync_unsynced_item_images():
    products_updated = 0
    count = 0
    while True:
        file_path = f"repairs/unsynced_images_{count}.json"
        if not os.path.exists(file_path):
            break
        
        with open(file_path, "r") as f:
            products = json.load(f)
        
        for product in products:
            print("uploading image")
            result = await ZohoAgent().upload_image(product["images"], product["zoho_id"])
            print(result)
            print(f"Uploaded {len(product['images'])} images for {product['name']} total products updated: {products_updated}")
            products_updated += 1
        count += 1
    print(f"Total products updated: {products_updated}")

async def sync_unsynced_items():
    # Initialize tracking variables
    total_count = 0
    errors = []
    successful_syncs = 0
    limit_exceeded = False
    
    try:
        filename = "repairs/unsynced_items.json"
        with open(filename, 'r') as f:
            products = json.load(f)
        
        total_products = len(products)
        print(f"Starting sync of {total_products} products")
        
        for product in products:
            if limit_exceeded:
                print("API limit exceeded. Stopping sync.")
                break
                
            try:
                # Get category
                category_id = "-1"
                if product["categories"]:
                    category_woo_id = product["categories"][0]["id"]
                    category = await PostgresAgent().get_category_by_woo_id(category_woo_id)
                    if category:
                        category_id = category.zoho_id
                
                # Get brand
                brand = product["brands"][0]["name"] if product["brands"] else "Eagle Fishing"
                
                # Process description
                final_description = ""
                if product["description"] or product["short_description"]:
                    text = product["description"] or product["short_description"]
                    soup = BeautifulSoup(text, 'html.parser')
                    # Clean text of emojis and invalid characters
                    plain_text = soup.get_text(separator=' ').strip()
                    # Remove non-BMP characters, convert special characters to ASCII, and remove < >
                    cleaned_text = unicodedata.normalize('NFKD', plain_text).encode('ascii', 'ignore').decode('ascii')
                    cleaned_text = cleaned_text.replace('<', '').replace('>', '')
                    truncated_description = cleaned_text[:2000]
                    final_description = truncated_description
                else:
                    truncated_description = "No Description added"
                    final_description = truncated_description
                
                # Process stock
                try:
                    stock_qty = max(0.0, float(product["stock_quantity"]))
                except (ValueError, TypeError):
                    stock_qty = 0.0
                
                available_stock = stock_qty if product["stock_status"] == "instock" else 0.0
                
                # Process price
                try:
                    price = float(product["price"]) if product["price"] else 0.0
                except (ValueError, TypeError):
                    price = 0.0
                    
                # Create item
                item_base = Item(
                    name=product["name"],
                    item_name=product["name"],
                    category_id=category_id,
                    unit="pcs",
                    status="active",
                    description=final_description,
                    brand=brand,
                    manufacturer=brand,
                    rate=price,
                    tax_id="686329000000054249",
                    initial_stock=stock_qty,
                    stock_on_hand=stock_qty,
                    available_stock=available_stock,
                    actual_available_stock=available_stock,
                    purchase_rate=price,
                    item_type="inventory",
                    product_type="goods",
                    sku=product["sku"],
                    length=product["dimensions"]["length"],
                    width=product["dimensions"]["width"],
                    height=product["dimensions"]["height"],
                    weight=product["weight"],
                    weight_unit="kg",
                    dimension_unit="cm",
                    tags=product["tags"]
                )
                
                # Create item in Zoho
                result = await ZohoAgent().create_item(item_base)
                print(result)
                if result.get("limit_exceeded"):
                    limit_exceeded = True
                    break
                
                # Handle image upload
                if result.get("item") and product["images"]:
                    try:
                        await ZohoAgent().upload_image(product["images"], result['item']['item_id'])
                        print(f"Uploaded {len(product['images'])} images for {product['name']}")
                    except Exception as e:
                        errors.append(f"Image upload error for {product['name']}: {str(e)}")
                
                successful_syncs += 1
                total_count += 1
                
                # Progress update every 10 items
                if total_count % 10 == 0:
                    print(f"Progress: {total_count}/{total_products} ({(total_count/total_products)*100:.1f}%)")
            
            except Exception as e:
                errors.append(f"Product error - {product.get('name', 'unknown')}: {str(e)}")
                continue
    
    except Exception as e:
        errors.append(f"File error - {filename}: {str(e)}")
    
    finally:
        # Print summary
        print("\nSync Summary:")
        print(f"Total products processed: {total_count}")
        print(f"Successfully synced: {successful_syncs}")
        print(f"Failed: {len(errors)}")
        
        if errors:
            print("\nErrors encountered:")
            for error in errors:
                print(f"- {error}")
        
        if limit_exceeded:
            print("\nSync stopped due to API limit exceeded")