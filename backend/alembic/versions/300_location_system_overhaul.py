"""Location system overhaul.

Implements the Location Node system:
- Strip locations table to essential columns (name, coords, type, parent)
- Add match_method/distance_km to event_locations
- Create event_coords_cache table
- Create territories table (placeholder)
- Create territory_locations table

Revision ID: 300_location_system
Revises: 200_connections
Create Date: 2026-02-17
"""
from alembic import op
import sqlalchemy as sa

revision = '300_location_system'
down_revision = '200_connections'
branch_labels = None
depends_on = None


def _column_exists(table, column):
    """Check if a column exists using raw SQL (PostgreSQL)."""
    from alembic import context
    conn = context.get_context().connection
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table, "column": column})
    return result.fetchone() is not None


def _table_exists(table):
    """Check if a table exists using raw SQL (PostgreSQL)."""
    from alembic import context
    conn = context.get_context().connection
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = :table"
    ), {"table": table})
    return result.fetchone() is not None


def upgrade():
    # ========================================================
    # Phase 1: Data migration before schema changes
    # ========================================================

    # 1a. Normalize location_type values to new schema (point/natural/sea)
    op.execute("""
        UPDATE locations SET location_type = CASE
            WHEN location_type = 'sea' THEN 'sea'
            WHEN location_type IS NOT NULL THEN 'point'
            ELSE 'point'
        END
    """)

    # 1b. Deduplicate wikidata_id (keep the one with lowest id)
    op.execute("""
        UPDATE locations SET wikidata_id = NULL
        WHERE wikidata_id IS NOT NULL
        AND id NOT IN (
            SELECT MIN(id) FROM locations
            WHERE wikidata_id IS NOT NULL
            GROUP BY wikidata_id
        )
    """)

    # ========================================================
    # Phase 2: Locations table cleanup
    # ========================================================

    # 2a. Rename parent_id → parent_location_id (idempotent)
    if _column_exists('locations', 'parent_id') and not _column_exists('locations', 'parent_location_id'):
        op.execute("ALTER TABLE locations RENAME COLUMN parent_id TO parent_location_id")
    elif _column_exists('locations', 'parent_id') and _column_exists('locations', 'parent_location_id'):
        # Both exist — drop the old one (data already in parent_location_id)
        op.drop_column('locations', 'parent_id')

    # 2b. Drop all unnecessary columns (idempotent)
    columns_to_drop = [
        'name_original',
        'modern_name',
        'type',
        'country',
        'region',
        'is_region',
        'coords_source',
        'canonical_id',
        'hierarchy_level',
        'modern_parent_id',
        'historical_parent_id',
        'valid_from',
        'valid_until',
        'display_level',
        'display_zoom_min',
        'display_zoom_max',
        'description',
        'description_ko',
        'description_ja',
        'description_source',
        'description_source_url',
        'wikipedia_url',
        'geocoded_by',
        'geocoded_at',
        'connection_count',
        'is_light',
    ]
    for col in columns_to_drop:
        if _column_exists('locations', col):
            op.drop_column('locations', col)

    # 2c. Make location_type NOT NULL with default 'point'
    op.alter_column(
        'locations', 'location_type',
        existing_type=sa.String(30),
        nullable=False,
        server_default='point',
    )

    # 2d. Add UNIQUE constraint on wikidata_id
    # Drop the old non-unique index first
    op.execute("DROP INDEX IF EXISTS ix_locations_wikidata_id")
    try:
        op.create_unique_constraint('uq_locations_wikidata_id', 'locations', ['wikidata_id'])
    except Exception:
        pass  # Already exists

    # ========================================================
    # Phase 3: Enhance event_locations table
    # ========================================================

    if not _column_exists('event_locations', 'match_method'):
        op.add_column('event_locations', sa.Column('match_method', sa.String(30)))
    if not _column_exists('event_locations', 'distance_km'):
        op.add_column('event_locations', sa.Column('distance_km', sa.Float()))

    # ========================================================
    # Phase 4: Create new tables (idempotent)
    # ========================================================

    # 4a. event_coords_cache
    if not _table_exists('event_coords_cache'):
        op.create_table(
            'event_coords_cache',
            sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('latitude', sa.Numeric(10, 7)),
            sa.Column('longitude', sa.Numeric(10, 7)),
            sa.Column('coord_source', sa.String(30)),
            sa.Column('source_qid', sa.String(20)),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )

    # 4b. territories
    if not _table_exists('territories'):
        op.create_table(
            'territories',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('name_ko', sa.String(255)),
            sa.Column('name_ja', sa.String(255)),
            sa.Column('wikidata_id', sa.String(20), unique=True),
            sa.Column('territory_type', sa.String(50)),
            sa.Column('valid_from', sa.Integer()),
            sa.Column('valid_until', sa.Integer()),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )

    # 4c. territory_locations
    if not _table_exists('territory_locations'):
        op.create_table(
            'territory_locations',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('territory_id', sa.Integer(), sa.ForeignKey('territories.id', ondelete='CASCADE'), nullable=False),
            sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('valid_from', sa.Integer()),
            sa.Column('valid_until', sa.Integer()),
            sa.Column('relation_type', sa.String(50), server_default='contains'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint('territory_id', 'location_id', 'valid_from', name='uq_territory_location_period'),
        )
        op.create_index('ix_territory_locations_territory', 'territory_locations', ['territory_id'])
        op.create_index('ix_territory_locations_location', 'territory_locations', ['location_id'])

    # ========================================================
    # Phase 5: Populate event_coords_cache from existing data
    # ========================================================

    # Cache original event coordinates from their primary locations
    op.execute("""
        INSERT INTO event_coords_cache (event_id, latitude, longitude, coord_source)
        SELECT e.id, l.latitude, l.longitude, 'inherited'
        FROM events e
        JOIN locations l ON e.primary_location_id = l.id
        WHERE l.latitude IS NOT NULL AND l.longitude IS NOT NULL
        ON CONFLICT (event_id) DO NOTHING
    """)


def downgrade():
    # Drop new tables
    op.drop_table('territory_locations')
    op.drop_table('territories')
    op.drop_table('event_coords_cache')

    # Remove event_locations additions
    op.drop_column('event_locations', 'distance_km')
    op.drop_column('event_locations', 'match_method')

    # Restore wikidata_id to non-unique index
    op.drop_constraint('uq_locations_wikidata_id', 'locations', type_='unique')
    op.create_index('ix_locations_wikidata_id', 'locations', ['wikidata_id'])

    # Restore location_type to nullable
    op.alter_column(
        'locations', 'location_type',
        existing_type=sa.String(30),
        nullable=True,
        server_default=None,
    )

    # Rename back
    op.execute("ALTER TABLE locations RENAME COLUMN parent_location_id TO parent_id")

    # Re-add dropped columns (without data - data is lost)
    op.add_column('locations', sa.Column('is_light', sa.Boolean(), server_default='false'))
    op.add_column('locations', sa.Column('connection_count', sa.Integer(), server_default='0'))
    op.add_column('locations', sa.Column('geocoded_at', sa.DateTime()))
    op.add_column('locations', sa.Column('geocoded_by', sa.String(100)))
    op.add_column('locations', sa.Column('wikipedia_url', sa.String(500)))
    op.add_column('locations', sa.Column('description_source_url', sa.String(500)))
    op.add_column('locations', sa.Column('description_source', sa.String(50)))
    op.add_column('locations', sa.Column('description_ja', sa.Text()))
    op.add_column('locations', sa.Column('description_ko', sa.Text()))
    op.add_column('locations', sa.Column('description', sa.Text()))
    op.add_column('locations', sa.Column('display_zoom_max', sa.Float(), server_default='10'))
    op.add_column('locations', sa.Column('display_zoom_min', sa.Float(), server_default='0'))
    op.add_column('locations', sa.Column('display_level', sa.Integer(), server_default='3'))
    op.add_column('locations', sa.Column('valid_until', sa.Integer()))
    op.add_column('locations', sa.Column('valid_from', sa.Integer()))
    op.add_column('locations', sa.Column('historical_parent_id', sa.Integer()))
    op.add_column('locations', sa.Column('modern_parent_id', sa.Integer()))
    op.add_column('locations', sa.Column('hierarchy_level', sa.String(30)))
    op.add_column('locations', sa.Column('canonical_id', sa.Integer()))
    op.add_column('locations', sa.Column('coords_source', sa.String(20), server_default='exact'))
    op.add_column('locations', sa.Column('is_region', sa.Boolean(), server_default='false'))
    op.add_column('locations', sa.Column('region', sa.String(100)))
    op.add_column('locations', sa.Column('country', sa.String(100)))
    op.add_column('locations', sa.Column('type', sa.String(50)))
    op.add_column('locations', sa.Column('modern_name', sa.String(255)))
    op.add_column('locations', sa.Column('name_original', sa.String(255)))
