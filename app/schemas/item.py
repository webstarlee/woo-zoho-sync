from pydantic import BaseModel

class Item(BaseModel):
    name: str
    item_name: str
    category_id: str
    unit: str
    status: str
    description: str
    brand: str
    manufacturer: str
    rate: float
    tax_id: str
    initial_stock: float
    stock_on_hand: float
    available_stock: float
    actual_available_stock: float
    purchase_rate: float
    item_type: str
    product_type: str
    sku: str
    length: str
    width: str
    height: str
    weight: str
    weight_unit: str
    dimension_unit: str
    tags: list
    
