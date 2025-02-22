"""create customer table

Revision ID: 5bf49f57fcab
Revises: a6f4bf0694b1
Create Date: 2025-02-20 07:10:16.476518

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5bf49f57fcab'
down_revision: Union[str, None] = 'a6f4bf0694b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column("contact_name", sa.String(), nullable=False),
        sa.Column("woo_id", sa.Integer(), nullable=False),
        sa.Column("zoho_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("customers")
