"""Add location_names table for temporal naming

Revision ID: 008_location_names
Revises: 007_add_event_parents
Create Date: 2026-02-05

같은 좌표의 위치가 시대별로 다른 이름을 가질 수 있음.
- London = Londinium (로마 시대)
- Seoul = 한양 = 한성 = 경성
- Istanbul = Constantinople = Byzantium

location_names 테이블로 시대별 명칭 관리.
"""
from alembic import op
import sqlalchemy as sa


revision = '008_location_names'
down_revision = '100_v2_schema'  # After V2 schema
branch_labels = None
depends_on = None


def upgrade():
    # 1. location_names 테이블 생성
    op.create_table(
        'location_names',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_ko', sa.String(255)),
        sa.Column('name_ja', sa.String(255)),
        sa.Column('language', sa.String(10), default='en'),  # en, ko, ja, zh, la, ar, gr
        sa.Column('valid_from', sa.Integer()),  # 시작 연도 (BCE는 음수)
        sa.Column('valid_until', sa.Integer()),  # 종료 연도
        sa.Column('is_primary', sa.Boolean(), default=False),  # 해당 시기 대표 명칭
        sa.Column('name_type', sa.String(30), default='official'),  # official, alternate, vernacular, colonial
        sa.Column('source', sa.String(100)),  # wikidata, manual, wikipedia
        sa.Column('wikidata_id', sa.String(50)),  # 해당 명칭의 Wikidata QID
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # 인덱스
    op.create_index('idx_location_names_location', 'location_names', ['location_id'])
    op.create_index('idx_location_names_period', 'location_names', ['valid_from', 'valid_until'])
    op.create_index('idx_location_names_name', 'location_names', ['name'])
    op.create_index('idx_location_names_wikidata', 'location_names', ['wikidata_id'])

    # 2. locations 테이블에 컬럼 추가
    op.add_column('locations', sa.Column('is_region', sa.Boolean(), server_default='false'))
    op.add_column('locations', sa.Column('coords_source', sa.String(20), server_default='exact'))
    op.add_column('locations', sa.Column('canonical_id', sa.Integer(), sa.ForeignKey('locations.id')))

    # 인덱스
    op.create_index('idx_locations_canonical', 'locations', ['canonical_id'])
    op.create_index('idx_locations_is_region', 'locations', ['is_region'])

    # 3. 기존 locations.name을 location_names로 마이그레이션
    op.execute("""
        INSERT INTO location_names (location_id, name, name_ko, language, is_primary, source)
        SELECT id, name, name_ko, 'en', TRUE, 'migration'
        FROM locations
        WHERE name IS NOT NULL
    """)


def downgrade():
    # location_names 테이블 삭제
    op.drop_index('idx_location_names_wikidata')
    op.drop_index('idx_location_names_name')
    op.drop_index('idx_location_names_period')
    op.drop_index('idx_location_names_location')
    op.drop_table('location_names')

    # locations 컬럼 삭제
    op.drop_index('idx_locations_is_region')
    op.drop_index('idx_locations_canonical')
    op.drop_column('locations', 'canonical_id')
    op.drop_column('locations', 'coords_source')
    op.drop_column('locations', 'is_region')
