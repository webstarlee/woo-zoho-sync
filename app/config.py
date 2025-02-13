import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://username:password@localhost:1027/database")
    ZOHO_ACCOUNTS_URL: str = os.getenv("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com")
    ZOHO_CLIENT_ID: str = os.getenv("ZOHO_CLIENT_ID", "1000.0000000000000000")
    ZOHO_CLIENT_SECRET: str = os.getenv("ZOHO_CLIENT_SECRET", "00000000000000000000000000000000")
    ZOHO_REDIRECT_URI: str = os.getenv("ZOHO_REDIRECT_URI", "http://example.com/oauth/callback")
    ZOHO_ORGANIZATION_ID: str = os.getenv("ZOHO_ORGANIZATION_ID", "00000000000000000000000000000000")
    WCM_CONSUMER_KEY: str = os.getenv("WCM_CONSUMER_KEY", "00000000000000000000000000000000")
    WCM_CONSUMER_SECRET: str = os.getenv("WCM_CONSUMER_SECRET", "00000000000000000000000000000000")
    WCM_URL: str = os.getenv("WCM_URL", "https://www.wcm.com")
    
    class Config:
        env_file = ".env"
    
    def refresh(self):
        """Reload environment variables"""
        load_dotenv(override=True)
        return Settings()

settings = Settings()
