from pydantic import BaseModel

class Item(BaseModel):
    name: str
    rate: float
    purchase_rate: float
    initial_stock: float
    initial_stock_rate: float
    stock_on_hand: float
    available_stock: float
    actual_available_stock: float
    sku: str
    attribute_option_name1: str

class AttributeOption(BaseModel):
    name: str

class Attribute(BaseModel):
    name: str
    options: list[AttributeOption]

class ItemGroup(BaseModel):
    group_name: str
    brand: str
    manufacturer: str
    unit: str
    description: str
    tax_id: str
    attribute_name1: str
    items: list[Item]
    attributes: list[Attribute]
    category_id: str