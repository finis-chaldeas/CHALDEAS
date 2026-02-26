"""Add history shift columns to historical_chains and chain_segments.

Extends existing tables with shift-related columns.
Also creates chain_segments and chain_entity_roles if missing (compact DB).

Revision ID: 600_history_shifts
Revises: 500_histories
Create Date: 2026-02-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '600_history_shifts'
down_revision = '500_histories'
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    insp = inspect(conn)
    return table_name in insp.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    insp = inspect(conn)
    columns = [c['name'] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # === Create chain_segments if missing (compact DB) ===
    if not _table_exists('chain_segments'):
        op.create_table(
            'chain_segments',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('chain_id', sa.Integer(), sa.ForeignKey('historical_chains.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('sequence_number', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(500)),
            sa.Column('narrative', sa.Text()),
            sa.Column('narrative_ko', sa.Text()),
            sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id'), index=True),
            sa.Column('person_id', sa.Integer(), sa.ForeignKey('persons.id'), index=True),
            sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), index=True),
            sa.Column('period_id', sa.Integer(), sa.ForeignKey('periods.id'), index=True),
            sa.Column('year_start', sa.Integer()),
            sa.Column('year_end', sa.Integer()),
            sa.Column('temporal_scale', sa.String(20)),
            sa.Column('transition_type', sa.String(30)),
            sa.Column('transition_strength', sa.Integer()),
            sa.Column('transition_narrative', sa.Text()),
            sa.Column('importance', sa.Integer(), default=3),
            sa.Column('is_keystone', sa.Boolean(), default=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            # Shift extension columns (included from creation)
            sa.Column('chapter_title', sa.String(200)),
            sa.Column('chapter_number', sa.Integer(), server_default='1'),
            sa.Column('page_narrative', sa.Text()),
            sa.Column('page_narrative_ko', sa.Text()),
            sa.Column('sub_shift_id', sa.Integer(), sa.ForeignKey('historical_chains.id')),
            sa.Column('media_url', sa.String(500)),
            sa.UniqueConstraint('chain_id', 'sequence_number', name='uq_chain_segment_order'),
        )
    else:
        # Table exists, just add new columns
        for col_name, col_def in [
            ('chapter_title', sa.Column('chapter_title', sa.String(200), nullable=True)),
            ('chapter_number', sa.Column('chapter_number', sa.Integer(), server_default='1')),
            ('page_narrative', sa.Column('page_narrative', sa.Text(), nullable=True)),
            ('page_narrative_ko', sa.Column('page_narrative_ko', sa.Text(), nullable=True)),
            ('sub_shift_id', sa.Column('sub_shift_id', sa.Integer(), sa.ForeignKey('historical_chains.id'), nullable=True)),
            ('media_url', sa.Column('media_url', sa.String(500), nullable=True)),
        ]:
            if not _column_exists('chain_segments', col_name):
                op.add_column('chain_segments', col_def)

    # === Create chain_entity_roles if missing ===
    if not _table_exists('chain_entity_roles'):
        op.create_table(
            'chain_entity_roles',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('chain_id', sa.Integer(), sa.ForeignKey('historical_chains.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('person_id', sa.Integer(), sa.ForeignKey('persons.id'), index=True),
            sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), index=True),
            sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id'), index=True),
            sa.Column('role', sa.String(50), nullable=False),
            sa.Column('importance', sa.Integer(), default=3),
            sa.Column('first_appearance', sa.Integer()),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )

    # === historical_chains: missing base columns (compact DB) + shift extension ===
    hc_columns = [
        # Base columns missing from compact DB
        ('summary_ko', sa.Column('summary_ko', sa.Text(), nullable=True)),
        ('focal_person_id', sa.Column('focal_person_id', sa.Integer(), sa.ForeignKey('persons.id'), nullable=True)),
        ('focal_location_id', sa.Column('focal_location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True)),
        ('focal_period_id', sa.Column('focal_period_id', sa.Integer(), sa.ForeignKey('periods.id'), nullable=True)),
        ('focal_event_id', sa.Column('focal_event_id', sa.Integer(), sa.ForeignKey('events.id'), nullable=True)),
        ('temporal_scale', sa.Column('temporal_scale', sa.String(20), nullable=True)),
        ('region', sa.Column('region', sa.String(100), nullable=True)),
        ('segment_count', sa.Column('segment_count', sa.Integer(), server_default='0')),
        ('entity_count', sa.Column('entity_count', sa.Integer(), server_default='0')),
        ('access_count', sa.Column('access_count', sa.Integer(), server_default='0')),
        ('last_accessed_at', sa.Column('last_accessed_at', sa.DateTime(), nullable=True)),
        ('is_auto_generated', sa.Column('is_auto_generated', sa.Boolean(), server_default='false')),
        ('generation_model', sa.Column('generation_model', sa.String(50), nullable=True)),
        ('generation_prompt_hash', sa.Column('generation_prompt_hash', sa.String(64), nullable=True)),
        ('quality_score', sa.Column('quality_score', sa.Float(), nullable=True)),
        ('human_reviewed', sa.Column('human_reviewed', sa.Boolean(), server_default='false')),
        ('created_by_master_id', sa.Column('created_by_master_id', sa.Integer(), nullable=True)),
        # Shift extension columns
        ('display_type', sa.Column('display_type', sa.String(10), server_default='modal')),
        ('chapter_count', sa.Column('chapter_count', sa.Integer(), server_default='1')),
        ('globe_importance', sa.Column('globe_importance', sa.Integer(), server_default='3')),
        ('thumbnail_url', sa.Column('thumbnail_url', sa.String(500), nullable=True)),
        ('parent_shift_id', sa.Column('parent_shift_id', sa.Integer(), sa.ForeignKey('historical_chains.id'), nullable=True)),
    ]
    for col_name, col_def in hc_columns:
        if not _column_exists('historical_chains', col_name):
            op.add_column('historical_chains', col_def)


def downgrade() -> None:
    # chain_segments columns (only drop if table existed before)
    if _table_exists('chain_segments'):
        for col in ['media_url', 'sub_shift_id', 'page_narrative_ko', 'page_narrative', 'chapter_number', 'chapter_title']:
            if _column_exists('chain_segments', col):
                op.drop_column('chain_segments', col)

    # historical_chains columns
    for col in ['parent_shift_id', 'thumbnail_url', 'globe_importance', 'chapter_count', 'display_type']:
        if _column_exists('historical_chains', col):
            op.drop_column('historical_chains', col)
