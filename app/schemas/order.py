from pydantic import BaseModel

class LineItem(BaseModel):
    item_id: str
    name: str
    description: str
    rate: float
    quantity: float
    unit: str
    tax_id: str | None
    tax_name: str | None
    tax_percentage: float | None
    item_total: float

class Order(BaseModel):
    customer_id: str
    date: str
    shipment_date: str
    reference_number: str
    line_items: list[LineItem]
    notes: str
    discount: float
    is_discount_before_tax: bool
    discount_type: str
    shipping_charge: float
    delivery_method: str
    status: str
    tax_total: float
    