import json
from app.schemas.customer import Customer, BillingAddress, ShippingAddress, ContactPerson
from app.agents.zoho import ZohoAgent
from app.agents.postgres import PostgresAgent
from app.models.customer import CustomerBase

async def sync_customers():
    print("Syncing customers")
    customers = []
    
    # File handling error
    try:
        with open("customers/real_customers.json", "r") as f:
            customers = json.load(f)
    except FileNotFoundError:
        print("Error: customers/real_customers.json file not found")
        return
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in customers file")
        return
    
    for customer in customers:
        try:
            # First try to get company name from billing company
            company_name = customer.get('billing', {}).get('company', '')
            if not company_name:
                # Fallback to company_name field if it exists
                company_name = customer.get('company_name', '')
            if not company_name:
                # Final fallback to full name
                first_name = customer.get('first_name', '')
                last_name = customer.get('last_name', '')
                company_name = f"{first_name} {last_name}".strip()
                if not company_name:
                    raise ValueError("Unable to determine company name - missing required fields")
        except Exception as e:
            print(f"Error creating company name: {str(e)}")
            continue
        
        try:
            customer_base = Customer(
                contact_name=customer["first_name"] + " " + customer["last_name"],
                company_name=company_name,
                contact_type="customer",
                billing_address=BillingAddress(
                    address=customer['billing']['address_1'],
                    city=customer["billing"]["city"],
                    state=customer["billing"]["state"],
                    zip=customer["billing"]["postcode"],
                    country=customer["billing"]["country"],
                ),
                shipping_address=ShippingAddress(
                    address=customer["shipping"]["address_1"],
                    city=customer["shipping"]["city"],
                    state=customer["shipping"]["state"],
                    zip=customer["shipping"]["postcode"],
                    country=customer["shipping"]["country"],
                ),
                contact_persons=[ContactPerson(
                    first_name=customer["first_name"],
                    last_name=customer["last_name"],
                    email=customer["email"],
                    is_primary_contact=True,
                )],
            )

            result = await ZohoAgent().create_customer(customer_base)
            if result['contact']:
                print(f"Customer {customer_base.company_name} created successfully")
                contact_zoho_id = result['contact']['contact_id']
                pg_customer = CustomerBase(
                    contact_name=customer_base.contact_name,
                    woo_id=customer["id"],
                    zoho_id=contact_zoho_id
                )
                await PostgresAgent().insert_customer(pg_customer)
                print(contact_zoho_id)
            else:
                print(f"Error: {result['message']}")
        except KeyError as e:
            print(f"Error: Missing required field in customer data: {e}")
            continue
        except ValueError as e:
            print(f"Error: Invalid data format: {e}")
            continue
        except Exception as e:
            print(f"Unexpected error while processing customer: {str(e)}")
            continue
        