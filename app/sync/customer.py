import json
from app.schemas.customer import Customer, BillingAddress, ShippingAddress, ContactPerson
from app.agents.zoho import ZohoAgent
async def sync_customers():
    print("Syncing customers")
    customers = []
    with open("customers/real_customers.json", "r") as f:
        customers = json.load(f)
        
    for customer in customers:
        try:
            customer_base = Customer(
                contact_name=customer["first_name"] + " " + customer["last_name"],
                company_name=customer["first_name"] + " " + customer["last_name"],
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
            print(result)
        except KeyError as e:
            print(f"Error: Missing required field in customer data: {e}")
            continue
        