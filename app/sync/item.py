import os, json, requests
from bs4 import BeautifulSoup
from app.agents.zoho import ZohoAgent
from app.agents.postgres import PostgresAgent
from app.schemas.item import Item

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
                        truncated_description = plain_description[:2000]
                    elif product["short_description"]:
                        soup = BeautifulSoup(product["short_description"], 'html.parser')
                        plain_description = soup.get_text(separator=' ').strip()
                        truncated_description = plain_description[:2000]
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
                    
                    item_base = Item(
                        name=product["name"],
                        item_name=product["name"],
                        category_id=category_id,
                        unit="pcs",
                        status="active",
                        description=truncated_description,
                        brand=brand,
                        manufacturer=brand,
                        rate=product["price"],
                        tax_id="686329000000054249",
                        initial_stock=float(stock_qty),
                        stock_on_hand=float(stock_qty),
                        available_stock=float(available_stock),
                        actual_available_stock=float(available_stock),
                        purchase_rate=product["price"],
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