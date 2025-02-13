import uuid
from pydantic import BaseModel

class BillingAddress(BaseModel):
    address: str
    city: str
    state: str
    zip: str
    country: str

class ShippingAddress(BaseModel):
    address: str
    city: str
    state: str
    zip: str
    country: str

class ContactPerson(BaseModel):
    first_name: str
    last_name: str
    email: str
    is_primary_contact: bool

class Customer(BaseModel):
    contact_name: str
    company_name: str
    contact_type: str
    billing_address: BillingAddress
    shipping_address: ShippingAddress
    contact_persons: list[ContactPerson]
