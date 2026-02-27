"""Add widgets JSONB column to chain_segments.

Allows attaching modular widget data to shift pages.

Revision ID: 601_add_widgets_jsonb
Revises: 600_history_shifts
Create Date: 2026-02-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

revision = '601_add_widgets_jsonb'
down_revision = '600_history_shifts'
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    insp = inspect(conn)
    columns = [c['name'] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not _column_exists('chain_segments', 'widgets'):
        op.add_column('chain_segments', sa.Column('widgets', JSONB, nullable=True))


def downgrade() -> None:
    if _column_exists('chain_segments', 'widgets'):
        op.drop_column('chain_segments', 'widgets')
