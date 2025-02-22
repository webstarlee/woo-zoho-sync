from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from datetime import datetime

from app.config import settings
from app.models.oauth import OAuth
from app.models.category import Category, CategoryBase
from app.models.customer import Customer, CustomerBase

class PostgresAgent:
    def __init__(self):
        self.engine = create_async_engine(settings.DATABASE_URL)

    async def get_session(self):
        async with AsyncSession(self.engine) as session:
            yield session
    
    async def insert_oauth(self, access_token: str, refresh_token: str, expires_at: datetime):
        async for db in self.get_session():
            db_oauth = OAuth(access_token=access_token, refresh_token=refresh_token, expires_at=expires_at)
            db.add(db_oauth)
            await db.commit()
            await db.refresh(db_oauth)
            return db_oauth
        return None
    
    async def update_oauth(self, access_token: str, refresh_token: str, expires_at: datetime):
        async for db in self.get_session():
            statement = select(OAuth).where(OAuth.refresh_token == refresh_token)
            result = (await db.exec(statement)).first()
            result.access_token = access_token
            result.expires_at = expires_at
            await db.commit()
            await db.refresh(result)
            return result
        return None
    
    async def get_oauth(self):
        async for db in self.get_session():
            statement = select(OAuth)
            result = (await db.exec(statement)).first()
            return result
        return None
    
    async def get_access_token(self):
        async for db in self.get_session():
            statement = select(OAuth)
            result = (await db.exec(statement)).first()
            return result.access_token
        return None
    
    async def get_refresh_token(self):
        async for db in self.get_session():
            statement = select(OAuth)
            result = (await db.exec(statement)).first()
            return result.refresh_token
        return None
    
    async def insert_category(self, category: CategoryBase):
        async for db in self.get_session():
            db_category = Category(
                name=category.name,
                description=category.description,
                url=category.url,
                woo_id=category.woo_id,
                woo_parent_id=category.woo_parent_id,
                zoho_id=category.zoho_id,
                zoho_parent_id=category.zoho_parent_id
            )
            db.add(db_category)
            await db.commit()
            await db.refresh(db_category)
            return db_category
        return None
    
    async def get_category_by_woo_id(self, woo_id: int):
        async for db in self.get_session():
            statement = select(Category).where(Category.woo_id == woo_id)
            result = (await db.exec(statement)).first()
            return result
        return None
    
    async def insert_customer(self, customer: CustomerBase):
        async for db in self.get_session():
            db_customer = Customer(
                contact_name=customer.contact_name,
                woo_id=customer.woo_id,
                zoho_id=customer.zoho_id
            )
            db.add(db_customer)
            await db.commit()
            await db.refresh(db_customer)
    
    async def get_customer_by_woo_id(self, woo_id: int):
        async for db in self.get_session():
            statement = select(Customer).where(Customer.woo_id == woo_id)
            result = (await db.exec(statement)).first()
            return result
        return None
