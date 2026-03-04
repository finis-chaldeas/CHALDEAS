"""Add camera_altitude and highlight_locations to chain_segments.

camera_altitude: Float — per-page globe zoom level (0.1~2.5).
highlight_locations: JSONB — array of {lat, lng, label, label_ko} for overview pages.

Revision ID: 603_shift_camera_highlights
Revises: 602_trismegistus_portal
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

revision = '603_shift_camera_highlights'
down_revision = '602_trismegistus_portal'
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    columns = [c['name'] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not _column_exists('chain_segments', 'camera_altitude'):
        op.add_column('chain_segments',
                       sa.Column('camera_altitude', sa.Float(), nullable=True))

    if not _column_exists('chain_segments', 'highlight_locations'):
        op.add_column('chain_segments',
                       sa.Column('highlight_locations', JSONB, nullable=True))


def downgrade() -> None:
    if _column_exists('chain_segments', 'highlight_locations'):
        op.drop_column('chain_segments', 'highlight_locations')

    if _column_exists('chain_segments', 'camera_altitude'):
        op.drop_column('chain_segments', 'camera_altitude')
