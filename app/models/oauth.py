import uuid
from sqlmodel import SQLModel, Field
from datetime import datetime

class OAuthBase(SQLModel):
    access_token: str
    refresh_token: str
    expires_at: datetime

class OAuth(OAuthBase, table=True):
    __tablename__ = "oauth_tokens"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)