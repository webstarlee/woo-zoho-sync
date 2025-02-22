import os, json
from app.schemas.item_group import ItemGroup, Item, Attribute
from app.agents.postgres import PostgresAgent
from app.agents.zoho import ZohoAgent
from bs4 import BeautifulSoup
import unicodedata
async def create_item_groups():
    try:
        print("Starting item group creation")
        
        filename = f"variable_products/products_9.json"
        
        try:
            with open(filename, 'r') as f:
                products = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading products file: {str(e)}")
            return
        
        failed_count = 0
        success_count = 0
        for product in products:
            if product['attributes'] == []:
                continue
            
            try:
                category = None  # Initialize category
                if len(product["categories"]) > 0:
                    category_woo_id = product["categories"][0]["id"]
                    category = await PostgresAgent().get_category_by_woo_id(category_woo_id)
                
                if category:
                    category_id = category.zoho_id
                else:
                    category_id = ""
                    
                group_items = []
                item_filename = f"variations/variations_{product['id']}.json"
                if not os.path.exists(item_filename):
                    print(f"Variations file not found for product ID: {product.get('id')}")
                    continue
                
                try:
                    with open(item_filename, 'r') as f:
                        items = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error loading variations file for product {product.get('id')}: {str(e)}")
                    failed_count += 1
                    continue
                
                item_images_list = []
                for item in items:
                    if len(item['attributes']) == 0:
                        continue
                    
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
                    
                    existing_skus = [item.sku for item in group_items]
                    
                    current_sku = item.get('sku', '')
                    if current_sku == "" or current_sku in existing_skus:
                        sku = f'{current_sku}-ER-{item["id"]}'
                    else:
                        sku = current_sku
                    
                    single_item = Item(
                        name=item_name,
                        rate=price,
                        purchase_rate=price,
                        initial_stock=float(stock_qty),
                        initial_stock_rate=500,
                        stock_on_hand=float(stock_qty),
                        available_stock=float(available_stock),
                        actual_available_stock=float(available_stock),
                        sku=sku,
                        attribute_option_name1=item.get('attributes', [{}])[0].get('option', ''),
                    )
                    
                    item_images = {
                        "sku": sku,
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
                
                brand = product["brands"][0]["name"] if product["brands"] else "Eagle Fishing"
                
                def clean_description(text):
                    if not text:
                        return "No Description"
                    # Remove HTML and clean text
                    plain_text = BeautifulSoup(text, 'html.parser').get_text(separator=' ', strip=True)
                    plain_text = ' '.join(plain_text.split())
                    cleaned_text = unicodedata.normalize('NFKD', plain_text).encode('ascii', 'ignore').decode('ascii')
                    cleaned_text = cleaned_text.replace('<', '').replace('>', '')
                    return cleaned_text[:2000]

                truncated_description = clean_description(product.get("description") or product.get("short_description"))
                    
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
                
                try:
                    result = await ZohoAgent().create_item_group(item_group)
                except Exception as e:
                    print(f"Error creating item group for product {product.get('id')}: {str(e)}")
                    failed_count += 1
                    continue
                
                if result.get("code") == 2:
                    print(f"invalid description: {truncated_description}")
                    continue
                
                if result.get("limit_exceeded"):
                    print(f"API limit exceeded. Stopping process.")
                    return
                
                if "item_group" not in result:
                    print(f"API Response: {result}")
                    failed_count += 1
                    continue
                
                print(f"Created item group: {product['name']} with total items: {len(result['item_group']['items'])}")
                success_count += 1
                if len(result["item_group"]["items"]) > 0:
                    print(f"Processing images for {len(result['item_group']['items'])} items in group {product['name']}")
                    sku_to_images = {item_image["sku"]: item_image["images"] for item_image in item_images_list}
                    
                    for item in result["item_group"]["items"]:
                        try:
                            item_sku = item.get("sku")
                            if item_sku and item_sku in sku_to_images:
                                print(f"Uploading images for SKU: {item_sku}")
                                image_upload_result = await ZohoAgent().upload_image(sku_to_images[item_sku], item["item_id"])
                                print(f"Image upload result for SKU {item_sku}")
                            else:
                                print(f"No images found for SKU: {item_sku}")
                        except Exception as e:
                            print(f"Error uploading images for SKU {item_sku}: {str(e)}")
                            continue
                            
            except Exception as e:
                print(f"Error processing product {product.get('id')}: {str(e)}")
                failed_count += 1
                continue
        
        print(f"Total products processed: {len(products)}")
        print(f"Successfully created item groups: {success_count}")
        print(f"Failed to create item groups: {failed_count}")
        
    except Exception as e:
        print(f"Fatal error in create_item_groups: {str(e)}")
        raise
