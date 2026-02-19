"""Add region column to period_narratives for regional sub-narratives.

Each period can have multiple rows: one global overview (region=NULL)
and one per active region (e.g., 'europe', 'east_asia', etc.)

Revision ID: 401_add_region
Revises: 400_timeline_narratives
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa

revision = '401_add_region'
down_revision = '400_timeline_narratives'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add region column
    op.add_column('period_narratives',
        sa.Column('region', sa.String(30), nullable=True))

    # Drop the old unique constraint (period_start, period_end)
    op.drop_constraint('uq_period_narratives_range', 'period_narratives', type_='unique')

    # New unique: (period_start, period_end, region) - allows NULL region for global overview
    op.create_index('idx_period_narratives_region', 'period_narratives', ['period_start', 'region'])

    # Add event_count and person_count for display
    op.add_column('period_narratives',
        sa.Column('event_count', sa.Integer, server_default='0'))
    op.add_column('period_narratives',
        sa.Column('person_count', sa.Integer, server_default='0'))

    # Add top_entity_names for quick display without JOINs
    op.add_column('period_narratives',
        sa.Column('top_events', sa.Text))   # JSON array string
    op.add_column('period_narratives',
        sa.Column('top_persons', sa.Text))   # JSON array string


def downgrade() -> None:
    op.drop_column('period_narratives', 'top_persons')
    op.drop_column('period_narratives', 'top_events')
    op.drop_column('period_narratives', 'person_count')
    op.drop_column('period_narratives', 'event_count')
    op.drop_index('idx_period_narratives_region', 'period_narratives')
    op.create_unique_constraint('uq_period_narratives_range', 'period_narratives',
        ['period_start', 'period_end'])
    op.drop_column('period_narratives', 'region')
