"""Trismegistus Portal tables + fgo_servants extensions.

Creates portal_items, collections, collection_entries tables.
Adds name_ko, dialogue_lines, chapter_count, is_original, atlas_id
columns to fgo_servants.

Revision ID: 602_trismegistus_portal
Revises: 601_add_widgets_jsonb
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

revision = '602_trismegistus_portal'
down_revision = '601_add_widgets_jsonb'
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    return table_name in insp.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    columns = [c['name'] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # === portal_items ===
    if not _table_exists('portal_items'):
        op.create_table(
            'portal_items',
            sa.Column('id', sa.Integer, primary_key=True, index=True),
            sa.Column('slug', sa.String(200), unique=True, nullable=False, index=True),
            sa.Column('item_type', sa.String(30), nullable=False, index=True),
            # Multilingual
            sa.Column('title', sa.String(300), nullable=False),
            sa.Column('title_ko', sa.String(300)),
            sa.Column('title_ja', sa.String(300)),
            sa.Column('subtitle', sa.String(300)),
            sa.Column('subtitle_ko', sa.String(300)),
            sa.Column('subtitle_ja', sa.String(300)),
            sa.Column('description', sa.Text, nullable=False),
            sa.Column('description_ko', sa.Text),
            sa.Column('description_ja', sa.Text),
            # Metadata
            sa.Column('chapter', sa.String(50)),
            sa.Column('era', sa.String(100)),
            sa.Column('year', sa.Integer),
            sa.Column('location', sa.String(200)),
            # FGO
            sa.Column('historical_basis', sa.Text),
            sa.Column('historical_basis_ko', sa.Text),
            sa.Column('historical_basis_ja', sa.Text),
            # JSONB
            sa.Column('sections', JSONB, server_default='[]'),
            sa.Column('related_servants', JSONB, server_default='[]'),
            sa.Column('related_event_ids', JSONB, server_default='[]'),
            sa.Column('sources', JSONB, server_default='[]'),
            # Curation
            sa.Column('sort_order', sa.Integer, server_default='0'),
            sa.Column('is_featured', sa.Boolean, server_default='false', index=True),
            sa.Column('thumbnail_url', sa.String(500)),
            # Timestamps
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
            # Constraints
            sa.CheckConstraint(
                "item_type IN ('singularity', 'lostbelt', 'servant_column', "
                "'history', 'literature', 'music', 'essay')",
                name="ck_portal_item_type"
            ),
        )

    # === collections ===
    if not _table_exists('collections'):
        op.create_table(
            'collections',
            sa.Column('id', sa.Integer, primary_key=True, index=True),
            sa.Column('slug', sa.String(200), unique=True, nullable=False, index=True),
            sa.Column('collection_type', sa.String(30), nullable=False, index=True),
            # Multilingual
            sa.Column('title', sa.String(300), nullable=False),
            sa.Column('title_ko', sa.String(300)),
            sa.Column('title_ja', sa.String(300)),
            sa.Column('description', sa.Text),
            sa.Column('description_ko', sa.Text),
            sa.Column('description_ja', sa.Text),
            # Display
            sa.Column('icon', sa.String(50)),
            sa.Column('cover_image_url', sa.String(500)),
            sa.Column('sort_order', sa.Integer, server_default='0'),
            sa.Column('is_featured', sa.Boolean, server_default='false', index=True),
            # Tags / time range
            sa.Column('tags', JSONB, server_default='[]'),
            sa.Column('year_start', sa.Integer),
            sa.Column('year_end', sa.Integer),
            sa.Column('region', sa.String(100)),
            # Timestamps
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
            # Constraints
            sa.CheckConstraint(
                "collection_type IN ('fgo_storyline', 'era', 'theme', 'content')",
                name="ck_collection_type"
            ),
        )

    # === collection_entries ===
    if not _table_exists('collection_entries'):
        op.create_table(
            'collection_entries',
            sa.Column('id', sa.Integer, primary_key=True, index=True),
            sa.Column('collection_id', sa.Integer,
                      sa.ForeignKey('collections.id', ondelete='CASCADE'),
                      nullable=False, index=True),
            sa.Column('entry_type', sa.String(30), nullable=False),
            # Polymorphic FKs
            sa.Column('shift_id', sa.Integer,
                      sa.ForeignKey('historical_chains.id'), index=True),
            sa.Column('portal_item_id', sa.Integer,
                      sa.ForeignKey('portal_items.id'), index=True),
            sa.Column('person_id', sa.Integer,
                      sa.ForeignKey('persons.id'), index=True),
            sa.Column('event_id', sa.Integer,
                      sa.ForeignKey('events.id'), index=True),
            sa.Column('period_id', sa.Integer,
                      sa.ForeignKey('periods.id'), index=True),
            # Display
            sa.Column('sort_order', sa.Integer, server_default='0'),
            sa.Column('is_highlighted', sa.Boolean, server_default='false'),
            sa.Column('note', sa.String(300)),
            sa.Column('note_ko', sa.String(300)),
            # Timestamp
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            # Constraints
            sa.CheckConstraint(
                "entry_type IN ('shift', 'portal_item', 'person', 'event', 'period')",
                name="ck_entry_type"
            ),
            sa.CheckConstraint(
                "((shift_id IS NOT NULL)::int + (portal_item_id IS NOT NULL)::int + "
                "(person_id IS NOT NULL)::int + (event_id IS NOT NULL)::int + "
                "(period_id IS NOT NULL)::int) = 1",
                name="exactly_one_entry_ref"
            ),
        )

    # === fgo_servants (create if missing, extend if exists) ===
    if not _table_exists('fgo_servants'):
        op.create_table(
            'fgo_servants',
            sa.Column('id', sa.Integer, primary_key=True, index=True),
            sa.Column('servant_id', sa.Integer, unique=True, nullable=False, index=True),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('name_jp', sa.String(200)),
            sa.Column('name_ko', sa.String(200)),
            sa.Column('class_name', sa.String(50), nullable=False),
            sa.Column('rarity', sa.Integer),
            sa.Column('person_id', sa.Integer, sa.ForeignKey('persons.id'), index=True),
            sa.Column('noble_phantasm', sa.String(200)),
            sa.Column('attribute', sa.String(50)),
            sa.Column('gender', sa.String(20)),
            sa.Column('portrait_url', sa.String(500)),
            # Extended columns
            sa.Column('dialogue_lines', sa.Integer, server_default='0'),
            sa.Column('chapter_count', sa.Integer, server_default='0'),
            sa.Column('is_original', sa.Boolean, server_default='false'),
            sa.Column('atlas_id', sa.Integer),
            # Timestamps
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        )
    else:
        # Table exists — add new columns if missing
        new_columns = {
            'name_ko': sa.Column('name_ko', sa.String(200)),
            'dialogue_lines': sa.Column('dialogue_lines', sa.Integer, server_default='0'),
            'chapter_count': sa.Column('chapter_count', sa.Integer, server_default='0'),
            'is_original': sa.Column('is_original', sa.Boolean, server_default='false'),
            'atlas_id': sa.Column('atlas_id', sa.Integer),
        }
        for col_name, col_def in new_columns.items():
            if not _column_exists('fgo_servants', col_name):
                op.add_column('fgo_servants', col_def)

    # === fgo_history_comparison (create if missing) ===
    if not _table_exists('fgo_history_comparison'):
        op.create_table(
            'fgo_history_comparison',
            sa.Column('id', sa.Integer, primary_key=True, index=True),
            sa.Column('servant_id', sa.Integer,
                      sa.ForeignKey('fgo_servants.id', ondelete='CASCADE'),
                      nullable=False, index=True),
            sa.Column('aspect', sa.String(50), nullable=False),
            sa.Column('fgo_description', sa.Text),
            sa.Column('historical_description', sa.Text),
            sa.Column('accuracy_score', sa.Integer),
            sa.Column('assessment', sa.String(30)),
            sa.Column('notes', sa.Text),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.CheckConstraint(
                "aspect IN ('biography', 'appearance', 'abilities', 'personality', 'relationships', 'noble_phantasm')",
                name='ck_fgo_comparison_aspect'
            ),
            sa.CheckConstraint(
                "assessment IN ('accurate', 'artistic_license', 'fictional', 'composite', 'gender_swap')",
                name='ck_fgo_comparison_assessment'
            ),
        )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    if _table_exists('collection_entries'):
        op.drop_table('collection_entries')
    if _table_exists('collections'):
        op.drop_table('collections')
    if _table_exists('portal_items'):
        op.drop_table('portal_items')
    if _table_exists('fgo_history_comparison'):
        op.drop_table('fgo_history_comparison')
    if _table_exists('fgo_servants'):
        op.drop_table('fgo_servants')
