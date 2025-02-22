import os, json, asyncio
from app.agents.zoho import ZohoAgent
from app.schemas.customer import Customer, BillingAddress, ShippingAddress, ContactPerson
from app.schemas.order import LineItem, Order
from app.agents.postgres import PostgresAgent

async def fetch_customer_id(order: dict):
    # Check existing customer first
    if order["customer_id"] != 0:
        customer = await PostgresAgent().get_customer_by_woo_id(order["customer_id"])
        if customer is not None:
            return customer.zoho_id
    
    # Extract billing info with defaults
    billing = order.get("billing", {})
    first_name = billing.get("first_name", "")
    last_name = billing.get("last_name", "")
    
    if not first_name or not last_name:
        print("Missing required billing name fields")
        return ""

    try:
        # Try to find existing customer by name
        print(f"Searching for customer: {first_name} {last_name}")
        result = await ZohoAgent().list_customers(first_name, last_name)
        if result.get("contacts"):
            return result["contacts"][0]["contact_id"]

        # Determine company name using fallbacks
        company_name = (
            billing.get("company")
            or order.get("company_name")
            or f"{first_name} {last_name}".strip()
        )
        
        if not company_name:
            print("Unable to determine company name - missing required fields")
            return ""

        # Create new customer
        customer_base = Customer(
            contact_name=f"{first_name} {last_name}",
            company_name=company_name,
            contact_type="customer",
            billing_address=BillingAddress(
                address=billing["address_1"],
                city=billing["city"],
                state=billing["state"],
                zip=billing["postcode"],
                country=billing["country"],
            ),
            shipping_address=ShippingAddress(
                address=order["shipping"]["address_1"],
                city=order["shipping"]["city"],
                state=order["shipping"]["state"],
                zip=order["shipping"]["postcode"],
                country=order["shipping"]["country"],
            ),
            contact_persons=[ContactPerson(
                first_name=first_name,
                last_name=last_name,
                email=billing["email"],
                is_primary_contact=True,
            )],
        )
        
        c_result = await ZohoAgent().create_customer(customer_base)
        print(f"Created new customer: {company_name}")
        return c_result['contact']['contact_id']

    except Exception as e:
        print(f"Error processing customer: {str(e)}")
        return ""

async def search_sku_item(sku: str):
    count = 0
    while True:
        file_path = f"zoho_items/items_{count}.json"
        if not os.path.exists(file_path):
            break
        
        with open(file_path, "r") as f:
            items = json.load(f)
            
        for item in items:
            if item["sku"] == sku:
                return item
            
        count += 1
        
    return None

async def fetch_line_items(order: dict):
    items = []
    for item in order["line_items"]:
        zoho_item = await search_sku_item(item["sku"])
        if zoho_item is None:
            continue
        
        rate = float(item["subtotal"])/float(item["quantity"]) if float(item["subtotal"]) != 0 and float(item['quantity']) != 0 else float(zoho_item["rate"])
        
        
        tax_id = None
        tax_name = None
        tax_percentage = None
        
        if len(order["tax_lines"]) > 0:
            tax_id = zoho_item["tax_id"]
            tax_name = zoho_item["tax_name"]
            tax_percentage = zoho_item["tax_percentage"]
            
        line_item = LineItem(
            item_id=zoho_item["item_id"],
            name=zoho_item["name"],
            description=zoho_item["description"],
            rate=rate,
            quantity=item["quantity"],
            unit=zoho_item["unit"],
            tax_id=tax_id,
            tax_name=tax_name,
            tax_percentage=tax_percentage,
            item_total=item["subtotal"]
        )
        
        items.append(line_item)
    return items

async def calculate_discount(order: dict, line_items: list[LineItem]):
    try:
        fixed_discount = float(order.get("discount_total", "0"))
        return fixed_discount
    except (ValueError, TypeError):
        print(f"Invalid discount_total value, defaulting to 0")
        return 0.0

async def sync_orders():
    count = 7
    while True:
        try:
            print("Syncing orders")
            file_path = f"orders/orders_{count}.json"
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                break
            
            with open(file_path, "r") as f:
                orders = json.load(f)
            
            for order in orders:
                try:
                    customer_id = await fetch_customer_id(order)
                    if customer_id == "":
                        continue
                    
                    line_items = await fetch_line_items(order)
                    if len(line_items) == 0:
                        continue
                    
                    discount = await calculate_discount(order, line_items)
                    
                    shipping_charge = 0.0
                    try:
                        shipping_total = float(order["shipping_total"]) if order["shipping_total"] else 0.0
                        shipping_tax = float(order["shipping_tax"]) if order["shipping_tax"] else 0.0
                        shipping_charge = shipping_total + shipping_tax
                    except (ValueError, TypeError):
                        shipping_charge = 0.0
                    
                    delivery_method = ""
                    try:
                        if len(order["shipping_lines"]) > 0:
                            delivery_method = order["shipping_lines"][0]["method_title"]
                        else:
                            delivery_method = "Pickup"
                    except (ValueError, TypeError):
                        delivery_method = "Pickup"
                    
                    tax_total = 0.0
                    try:
                        tax_total = float(order["total_tax"]) if order["total_tax"] else 0.0
                    except (ValueError, TypeError):
                        print(f"Invalid total_tax value, defaulting to 0")
                        tax_total = 0.0
                    
                    order_base = Order(
                        customer_id=customer_id,
                        date=order["date_created"].split('T')[0],
                        shipment_date=order["date_completed"].split('T')[0],
                        reference_number=str(order["id"]),
                        line_items=line_items,
                        notes=order["customer_note"],
                        discount=discount,
                        is_discount_before_tax=True,
                        discount_type="entity_level",
                        shipping_charge=shipping_charge,
                        delivery_method=delivery_method,
                        status="Confirmed",
                        tax_total=tax_total
                    )
                    
                    result = await ZohoAgent().create_order(order_base)
                    if result.get("salesorder", {}).get("status") == "draft":
                        print("Draft order created")
                        confirmed_result = await ZohoAgent().mark_order_as_confirmed(result.get("salesorder", {}).get("salesorder_id"))
                        print(confirmed_result)
                except KeyError as e:
                    print(f"Missing required field in order: {str(e)}")
                    continue
                except Exception as e:
                    print(f"Unexpected error processing order: {str(e)}")
                    continue
            
            print(f"Orders synced of {count}")
            count += 1
            await asyncio.sleep(1)
        except json.JSONDecodeError as e:
            print(f"Error reading JSON file: {str(e)}")
            count += 1
        except Exception as e:
            print(f"Unexpected error in sync_orders: {str(e)}")
            count += 1
        
    print("All orders synced")

async def sync_order_one():
    
    order = {
        "id": 109964,
        "parent_id": 0,
        "status": "completed",
        "currency": "SEK",
        "version": "9.6.1",
        "prices_include_tax": True,
        "date_created": "2025-01-23T22:02:27",
        "date_modified": "2025-02-10T23:30:10",
        "discount_total": "0",
        "discount_tax": "0",
        "shipping_total": "63",
        "shipping_tax": "16",
        "cart_tax": "90",
        "total": "529",
        "total_tax": "106",
        "customer_id": 158880,
        "order_key": "wc_order_t6TvfkNaW05y5",
        "billing": {
            "first_name": "Joakim",
            "last_name": "Gudmunds",
            "company": "",
            "address_1": "Tullhusgatan 11",
            "address_2": "",
            "city": "Karlstad",
            "state": "",
            "postcode": "652 27",
            "country": "SE",
            "email": "joakimgudmunds@gmail.com",
            "phone": "0738178051"
        },
        "shipping": {
            "first_name": "Joakim",
            "last_name": "Gudmunds",
            "company": "",
            "address_1": "Tullhusgatan 11",
            "address_2": "",
            "city": "Karlstad",
            "state": "",
            "postcode": "652 27",
            "country": "SE",
            "phone": ""
        },
        "payment_method": "redlight_swish-ecommerce",
        "payment_method_title": "Swish",
        "transaction_id": "011C2E7B8E8E1958ED91796B9AC9DA63",
        "customer_ip_address": "81.226.225.68",
        "customer_user_agent": "Mozilla/5.0 (Linux; Android 14; SM-S918B Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6834.90 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/496.0.0.45.65;IABMV/1;]",
        "created_via": "checkout",
        "customer_note": "",
        "date_completed": "2025-01-24T15:43:28",
        "date_paid": "2025-01-23T22:02:55",
        "cart_hash": "fcfacca4274c27a3d90f52a954912daf",
        "number": "109964",
        "line_items": [
            {
                "id": 11879,
                "name": "Gunki Hårt Spöfodral Power Game 140",
                "product_id": 75660,
                "variation_id": 0,
                "quantity": 1,
                "tax_class": "",
                "subtotal": "360",
                "subtotal_tax": "90",
                "total": "360",
                "total_tax": "90",
                "taxes": [
                    {
                        "id": 1,
                        "total": "89.9",
                        "subtotal": "89.9"
                    }
                ],
                "meta_data": [
                    {
                        "id": 99789,
                        "key": "_reduced_stock",
                        "value": "1",
                        "display_key": "_reduced_stock",
                        "display_value": "1"
                    }
                ],
                "sku": "33080",
                "price": 359.6,
                "image": {
                    "id": "79165",
                    "src": "https://eagle.fishing/wp-content/uploads/2023/05/spovaska-gunki.webp"
                },
                "parent_name": None
            }
        ],
        "tax_lines": [
            {
                "id": 11881,
                "rate_code": "SE-MOMS (PRODUKTER, TJäNSTER)-1",
                "rate_id": 1,
                "label": "Moms (Produkter, tjänster)",
                "compound": False,
                "tax_total": "90",
                "shipping_tax_total": "16",
                "rate_percent": 25
            }
        ],
        "shipping_lines": [
            {
                "id": 11880,
                "method_title": "DHL Service Point - 0-5kg",
                "method_id": "table_rate",
                "instance_id": "23",
                "total": "63",
                "total_tax": "16",
                "taxes": [
                    {
                        "id": 1,
                        "total": "15.8",
                        "subtotal": ""
                    }
                ],
                "tax_status": "taxable",
                "meta_data": [
                    {
                        "id": 99778,
                        "key": "Artiklar",
                        "value": "Gunki Hårt Spöfodral Power Game 140 &times; 1",
                        "display_key": "Artiklar",
                        "display_value": "Gunki Hårt Spöfodral Power Game 140 &times; 1"
                    }
                ]
            }
        ],
        "fee_lines": [],
        "coupon_lines": [],
        "refunds": [],
        "payment_url": "https://eagle.fishing/checkout/order-pay/109964/?pay_for_order=true&key=wc_order_t6TvfkNaW05y5",
        "is_editable": False,
        "needs_payment": False,
        "needs_processing": True,
        "date_created_gmt": "2025-01-23T21:02:27",
        "date_modified_gmt": "2025-02-10T22:30:10",
        "date_completed_gmt": "2025-01-24T14:43:28",
        "date_paid_gmt": "2025-01-23T21:02:55",
        "currency_symbol": "kr"
    }
    
    
    try:
        customer_id = await fetch_customer_id(order)
        if customer_id == "":
            return
        
        line_items = await fetch_line_items(order)
        discount = await calculate_discount(order, line_items)
        
        shipping_charge = 0.0
        try:
            shipping_total = float(order["shipping_total"]) if order["shipping_total"] else 0.0
            shipping_tax = float(order["shipping_tax"]) if order["shipping_tax"] else 0.0
            shipping_charge = shipping_total + shipping_tax
        except (ValueError, TypeError):
            shipping_charge = 0.0
        
        delivery_method = ""
        try:
            if len(order["shipping_lines"]) > 0:
                delivery_method = order["shipping_lines"][0]["method_title"]
            else:
                delivery_method = "Pickup"
        except (ValueError, TypeError):
            delivery_method = "Pickup"
        
        tax_total = 0.0
        try:
            tax_total = float(order["total_tax"]) if order["total_tax"] else 0.0
        except (ValueError, TypeError):
            print(f"Invalid total_tax value, defaulting to 0")
            tax_total = 0.0
        
        order_base = Order(
            customer_id=customer_id,
            date=order["date_created"].split('T')[0],
            shipment_date=order["date_completed"].split('T')[0],
            reference_number=str(order["id"]),
            line_items=line_items,
            notes=order["customer_note"],
            discount=discount,
            is_discount_before_tax=True,
            discount_type="entity_level",
            shipping_charge=shipping_charge,
            delivery_method=delivery_method,
            status="Confirmed",
            tax_total=tax_total
        )
        
        result = await ZohoAgent().create_order(order_base)
        if result.get("salesorder", {}).get("status") == "draft":
            print("Draft order created")
            confirmed_result = await ZohoAgent().mark_order_as_confirmed(result.get("salesorder", {}).get("salesorder_id"))
            print(confirmed_result)
        
        return
    except KeyError as e:
        print(f"Missing required field in order: {str(e)}")
        return
    except Exception as e:
        print(f"Unexpected error processing order: {str(e)}")
        return