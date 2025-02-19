import os, json
from app.schemas.item_group import ItemGroup, Item, Attribute
from app.agents.postgres import PostgresAgent
from app.agents.zoho import ZohoAgent
from bs4 import BeautifulSoup

async def create_item_groups():
    count = 1
    limit_exceeded = False
    
    while True:
        if limit_exceeded:
            break
        try:
            filename = f"variable_products/products_{count}.json"
            if not os.path.exists(filename):
                break
            
            with open(filename, 'r') as f:
                products = json.load(f)
            count += 1  # Increment counter after processing each file
                
            for product in products:
                category = None  # Initialize category
                if len(product["categories"]) > 0:
                    category_woo_id = product["categories"][0]["id"]
                    category = await PostgresAgent().get_category_by_woo_id(category_woo_id)
                
                if category:
                    category_id = category.zoho_id
                else:
                    category_id = "-1"
                    
                group_items = []
                item_filename = f"variations/variations_{product['id']}.json"
                if not os.path.exists(item_filename):
                    continue
                with open(item_filename, 'r') as f:
                    items = json.load(f)
                
                item_images_list = []
                for item in items:
                    try:
                        stock_qty = float(item["stock_quantity"])
                        stock_qty = max(0.0, stock_qty)
                    except (ValueError, TypeError):
                        stock_qty = 0.0
                    
                    available_stock = stock_qty
                    if item["stock_status"] == "instock":
                        available_stock = stock_qty
                    else:
                        available_stock = 0.0
                    
                    try:
                        price = float(item["price"]) if item["price"] else 0.0
                    except (ValueError, TypeError):
                        price = 0.0
                    
                    try:
                        item_name = product["name"] + " - " + item["attributes"][0]["option"]
                    except (KeyError, IndexError, TypeError):
                        item_name = product.get("name", "Unknown Product")
                        print(f"Error creating item name for product ID {product.get('id', 'unknown')}: Missing or invalid attributes")
                    
                    single_item = Item(
                        name=item_name,
                        rate=price,
                        purchase_rate=price,
                        initial_stock=float(stock_qty),
                        initial_stock_rate=500,
                        stock_on_hand=float(stock_qty),
                        available_stock=float(available_stock),
                        actual_available_stock=float(available_stock),
                        sku=item.get('sku', ''),
                        attribute_option_name1=item.get('attributes', [{}])[0].get('option', ''),
                    )
                    
                    item_images = {
                        "sku": item['sku'],
                        "images": [item["image"]]
                    }
                    
                    item_images_list.append(item_images)
                    
                    group_items.append(single_item)
                
                group_attributes = []
                for attribute in product["attributes"]:
                    # Truncate attribute name to 99 characters to stay under limit
                    truncated_attr_name = attribute["name"][:99]
                    group_attributes.append(Attribute(
                        name=truncated_attr_name,
                        options=[{"name": option_name[:99]} for option_name in attribute["options"]]  # Also truncate options
                    ))
                
                if len(product["brands"]) > 0:
                    brand = product["brands"][0]["name"][:99]  # Truncate brand name
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
                    
                item_group = ItemGroup(
                    group_name=product.get("name", "Unknown Product"),
                    brand=brand,
                    manufacturer=brand,
                    unit="pcs",
                    description=truncated_description,
                    tax_id="686329000000054249",
                    attribute_name1=product.get("attributes", [{"name": ""}])[0].get("name", ""),
                    items=group_items,
                    attributes=group_attributes,
                    category_id=category_id
                )
                
                result = await ZohoAgent().create_item_group(item_group)
                if result.get("limit_exceeded"):
                    limit_exceeded = True
                    print(f"API limit exceeded. Stopping process.")
                    break
                
                if "item_group" not in result:
                    print(f"Error: Unexpected API response format for {product.get('name', 'Unknown Product')}")
                    print(f"API Response: {result}")
                    continue
                
                print(f"Created item group: {product['name']} with total items: {len(result['item_group']['items'])}")
                
                if len(result["item_group"]["items"]) > 0:
                    print(f"Processing images for {len(result['item_group']['items'])} items in group {product['name']}")
                    # Create a dictionary for quick SKU lookup
                    sku_to_images = {item_image["sku"]: item_image["images"] for item_image in item_images_list}
                    
                    for item in result["item_group"]["items"]:
                        item_sku = item.get("sku")
                        if item_sku and item_sku in sku_to_images:
                            print(f"Uploading images for SKU: {item_sku}")
                            image_upload_result = await ZohoAgent().upload_image(sku_to_images[item_sku], item["item_id"])
                            print(f"Image upload result for SKU {item_sku}")
                        else:
                            print(f"No images found for SKU: {item_sku}")
                
        except Exception as e:
            print(f"Error processing file {filename}: {str(e)}")
            # Maybe add a retry mechanism or logging
            count += 1  # Still increment counter to avoid getting stuck
            continue
    
    print("Done")