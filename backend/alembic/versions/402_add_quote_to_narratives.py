"""Add quote and quote_source columns to period_narratives.

Stores a representative historical quote for each regional narrative,
extracted by the LLM during narrative generation.

Revision ID: 402_add_quote
Revises: 401_add_region
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa

revision = '402_add_quote'
down_revision = '401_add_region'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('period_narratives',
        sa.Column('quote', sa.String(500), nullable=True))
    op.add_column('period_narratives',
        sa.Column('quote_source', sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column('period_narratives', 'quote_source')
    op.drop_column('period_narratives', 'quote')
