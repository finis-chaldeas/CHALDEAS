"""Add event and location hierarchy support

Revision ID: 005_add_event_location_hierarchy
Revises: 004_multilingual_source_tracking
Create Date: 2026-01-28

Adds:
- Event hierarchy: parent_event_id, is_aggregate, hierarchy_level, aggregate_type
- Event display: default_collapsed, min_zoom_level
- Location hierarchy: parent_id, location_type, display_level, display_zoom_min/max
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_add_event_location_hierarchy'
down_revision: Union[str, None] = '004_multilingual_source_tracking'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== EVENTS ==========
    # Hierarchy columns
    op.add_column('events', sa.Column('parent_event_id', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('is_aggregate', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('events', sa.Column('hierarchy_level', sa.Integer(), server_default='3', nullable=False))
    # 0=Era, 1=Mega, 2=Aggregate, 3=Major, 4=Minor
    op.add_column('events', sa.Column('aggregate_type', sa.String(50), nullable=True))
    # war, movement, dynasty, expedition, revolution, crisis, artistic_period, philosophical_school, scientific_era, religious

    # Display settings
    op.add_column('events', sa.Column('default_collapsed', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('events', sa.Column('min_zoom_level', sa.Float(), server_default='1.0', nullable=False))

    # Indexes for events
    op.create_index('ix_events_parent_event_id', 'events', ['parent_event_id'])
    op.create_index('ix_events_is_aggregate', 'events', ['is_aggregate'])
    op.create_index('ix_events_hierarchy_level', 'events', ['hierarchy_level'])
    op.create_index('ix_events_aggregate_type', 'events', ['aggregate_type'])

    # Foreign key for event hierarchy
    op.create_foreign_key(
        'fk_events_parent_event',
        'events', 'events',
        ['parent_event_id'], ['id'],
        ondelete='SET NULL'
    )

    # ========== LOCATIONS ==========
    # Hierarchy columns (parent_id is simpler than existing dual hierarchy)
    op.add_column('locations', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.add_column('locations', sa.Column('location_type', sa.String(30), nullable=True))
    # city, region, country, empire, cultural_sphere, sea, continent, site
    op.add_column('locations', sa.Column('display_level', sa.Integer(), server_default='3', nullable=False))
    # 0=World, 1=Continent/Empire, 2=Region/Country, 3=City, 4=Site (for zoom filtering)
    # Note: existing hierarchy_level (String) is kept for compatibility

    # Display settings
    op.add_column('locations', sa.Column('display_zoom_min', sa.Float(), server_default='0', nullable=False))
    op.add_column('locations', sa.Column('display_zoom_max', sa.Float(), server_default='10', nullable=False))

    # Indexes for locations
    op.create_index('ix_locations_parent_id', 'locations', ['parent_id'])
    op.create_index('ix_locations_location_type', 'locations', ['location_type'])
    op.create_index('ix_locations_display_level', 'locations', ['display_level'])

    # Foreign key for location hierarchy
    op.create_foreign_key(
        'fk_locations_parent',
        'locations', 'locations',
        ['parent_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # ========== LOCATIONS ==========
    op.drop_constraint('fk_locations_parent', 'locations', type_='foreignkey')
    op.drop_index('ix_locations_display_level', 'locations')
    op.drop_index('ix_locations_location_type', 'locations')
    op.drop_index('ix_locations_parent_id', 'locations')
    op.drop_column('locations', 'display_zoom_max')
    op.drop_column('locations', 'display_zoom_min')
    op.drop_column('locations', 'display_level')
    op.drop_column('locations', 'location_type')
    op.drop_column('locations', 'parent_id')

    # ========== EVENTS ==========
    op.drop_constraint('fk_events_parent_event', 'events', type_='foreignkey')
    op.drop_index('ix_events_aggregate_type', 'events')
    op.drop_index('ix_events_hierarchy_level', 'events')
    op.drop_index('ix_events_is_aggregate', 'events')
    op.drop_index('ix_events_parent_event_id', 'events')
    op.drop_column('events', 'min_zoom_level')
    op.drop_column('events', 'default_collapsed')
    op.drop_column('events', 'aggregate_type')
    op.drop_column('events', 'hierarchy_level')
    op.drop_column('events', 'is_aggregate')
    op.drop_column('events', 'parent_event_id')
