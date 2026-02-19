"""Event system overhaul.

Implements the Event Node slim-down:
1. Create event_details table
2. Migrate content/URL/date/display data from events to event_details
3. Drop moved and deleted columns from events

Revision ID: 302_event_system
Revises: 301_person_system
Create Date: 2026-02-17
"""
from alembic import op
import sqlalchemy as sa

revision = '302_event_system'
down_revision = '301_person_system'
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
    # Phase 1: Create event_details table
    # ========================================================
    if not _table_exists('event_details'):
        op.create_table(
            'event_details',
            sa.Column('event_id', sa.Integer, sa.ForeignKey('events.id', ondelete='CASCADE'), primary_key=True),

            # URL / slug
            sa.Column('slug', sa.String(500)),
            sa.Column('wikipedia_url', sa.String(500)),
            sa.Column('image_url', sa.String(500)),

            # Content (multilingual)
            sa.Column('description', sa.Text),
            sa.Column('description_ko', sa.Text),
            sa.Column('description_ja', sa.Text),
            sa.Column('description_source', sa.String(50)),
            sa.Column('description_source_url', sa.String(500)),

            # Precise dates
            sa.Column('date_start_month', sa.Integer),
            sa.Column('date_start_day', sa.Integer),
            sa.Column('date_end_month', sa.Integer),
            sa.Column('date_end_day', sa.Integer),

            # Display hints
            sa.Column('source_reliability', sa.Integer, server_default='3'),
            sa.Column('default_collapsed', sa.Boolean, server_default='false'),
            sa.Column('min_zoom_level', sa.Float, server_default='1.0'),

            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        )

    # ========================================================
    # Phase 2: Migrate data from events to event_details
    # ========================================================
    # Only migrate if source columns still exist on events
    if _column_exists('events', 'description'):
        op.execute("""
            INSERT INTO event_details (
                event_id,
                slug, wikipedia_url, image_url,
                description, description_ko, description_ja,
                description_source, description_source_url,
                date_start_month, date_start_day,
                date_end_month, date_end_day,
                source_reliability, default_collapsed, min_zoom_level
            )
            SELECT
                id,
                slug, wikipedia_url, image_url,
                description, description_ko, description_ja,
                description_source, description_source_url,
                date_start_month, date_start_day,
                date_end_month, date_end_day,
                COALESCE(source_reliability, 3),
                COALESCE(default_collapsed, false),
                COALESCE(min_zoom_level, 1.0)
            FROM events
            WHERE slug IS NOT NULL
               OR description IS NOT NULL
               OR wikipedia_url IS NOT NULL
               OR image_url IS NOT NULL
               OR date_start_month IS NOT NULL
               OR date_start_day IS NOT NULL
               OR description_ko IS NOT NULL
               OR description_ja IS NOT NULL
               OR description_source IS NOT NULL
            ON CONFLICT (event_id) DO NOTHING
        """)

    # ========================================================
    # Phase 3: Drop moved columns from events (idempotent)
    # ========================================================
    moved_columns = [
        'slug', 'description', 'description_ko', 'description_ja',
        'description_source', 'description_source_url',
        'image_url', 'wikipedia_url',
        'date_start_month', 'date_start_day', 'date_end_month', 'date_end_day',
        'source_reliability', 'default_collapsed', 'min_zoom_level',
    ]
    for col in moved_columns:
        if _column_exists('events', col):
            op.drop_column('events', col)

    # ========================================================
    # Phase 4: Drop deleted columns (computed/pipeline metadata)
    # ========================================================
    deleted_columns = [
        'connection_count', 'is_light',
        'enriched_by', 'enriched_at', 'enrichment_version',
        'event_type', 'description_model', 'description_at',
    ]
    for col in deleted_columns:
        if _column_exists('events', col):
            op.drop_column('events', col)


def downgrade():
    # ========================================================
    # Restore deleted columns
    # ========================================================
    op.add_column('events', sa.Column('enrichment_version', sa.String(50)))
    op.add_column('events', sa.Column('enriched_at', sa.DateTime))
    op.add_column('events', sa.Column('enriched_by', sa.String(100)))
    op.add_column('events', sa.Column('is_light', sa.Boolean, server_default='false'))
    op.add_column('events', sa.Column('connection_count', sa.Integer, server_default='0'))

    # ========================================================
    # Restore moved columns
    # ========================================================
    op.add_column('events', sa.Column('min_zoom_level', sa.Float, server_default='1.0'))
    op.add_column('events', sa.Column('default_collapsed', sa.Boolean, server_default='false'))
    op.add_column('events', sa.Column('source_reliability', sa.Integer, server_default='3'))
    op.add_column('events', sa.Column('date_end_day', sa.Integer))
    op.add_column('events', sa.Column('date_end_month', sa.Integer))
    op.add_column('events', sa.Column('date_start_day', sa.Integer))
    op.add_column('events', sa.Column('date_start_month', sa.Integer))
    op.add_column('events', sa.Column('wikipedia_url', sa.String(500)))
    op.add_column('events', sa.Column('image_url', sa.String(500)))
    op.add_column('events', sa.Column('description_source_url', sa.String(500)))
    op.add_column('events', sa.Column('description_source', sa.String(50)))
    op.add_column('events', sa.Column('description_ja', sa.Text))
    op.add_column('events', sa.Column('description_ko', sa.Text))
    op.add_column('events', sa.Column('description', sa.Text))
    op.add_column('events', sa.Column('slug', sa.String(500)))

    # ========================================================
    # Migrate data back from event_details to events
    # ========================================================
    op.execute("""
        UPDATE events e SET
            slug = ed.slug,
            description = ed.description,
            description_ko = ed.description_ko,
            description_ja = ed.description_ja,
            description_source = ed.description_source,
            description_source_url = ed.description_source_url,
            image_url = ed.image_url,
            wikipedia_url = ed.wikipedia_url,
            date_start_month = ed.date_start_month,
            date_start_day = ed.date_start_day,
            date_end_month = ed.date_end_month,
            date_end_day = ed.date_end_day,
            source_reliability = ed.source_reliability,
            default_collapsed = ed.default_collapsed,
            min_zoom_level = ed.min_zoom_level
        FROM event_details ed
        WHERE ed.event_id = e.id
    """)

    # Drop event_details table
    op.drop_table('event_details')
