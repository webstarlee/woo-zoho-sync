import uuid
from sqlmodel import SQLModel, Field

class CategoryBase(SQLModel):
    name: str
    woo_id: int | None = Field(default=None)
    woo_parent_id: int | None = Field(default=None)
    zoho_id: str | None = Field(default=None)
    zoho_parent_id: str | None = Field(default=None)
    description: str | None = Field(default=None)
    url: str | None = Field(default=None)

class Category(CategoryBase, table=True):
    __tablename__ = "categories"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
