import uuid
from sqlmodel import SQLModel, Field

class CustomerBase(SQLModel):
    contact_name: str
    woo_id: int
    zoho_id: str

class Customer(CustomerBase, table=True):
    __tablename__ = "customers"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
