"""Person system overhaul.

Implements the Person Node system:
1. Create person_details table and migrate data from persons
2. Create location_details table (Location system complement)
3. Create person_names table and migrate name_original
4. Strip persons table to 15 essential columns

Revision ID: 301_person_system
Revises: 300_location_system
Create Date: 2026-02-17
"""
from alembic import op
import sqlalchemy as sa

revision = '301_person_system'
down_revision = '300_location_system'
branch_labels = None
depends_on = None


def upgrade():
    # ========================================================
    # Phase 1: Create new tables
    # ========================================================

    # 1a. person_details table
    op.create_table(
        'person_details',
        sa.Column('person_id', sa.Integer, sa.ForeignKey('persons.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('slug', sa.String(255)),
        sa.Column('wikipedia_url', sa.String(500)),
        sa.Column('image_url', sa.String(500)),
        sa.Column('birth_month', sa.Integer),
        sa.Column('birth_day', sa.Integer),
        sa.Column('death_month', sa.Integer),
        sa.Column('death_day', sa.Integer),
        sa.Column('birth_date_precision', sa.String(20), server_default='year'),
        sa.Column('death_date_precision', sa.String(20), server_default='year'),
        sa.Column('biography', sa.Text),
        sa.Column('biography_ko', sa.Text),
        sa.Column('biography_ja', sa.Text),
        sa.Column('biography_source', sa.String(50)),
        sa.Column('biography_source_url', sa.String(500)),
        sa.Column('category_id', sa.Integer, sa.ForeignKey('categories.id')),
        sa.Column('era', sa.String(100)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # 1b. location_details table
    op.create_table(
        'location_details',
        sa.Column('location_id', sa.Integer, sa.ForeignKey('locations.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('description', sa.Text),
        sa.Column('description_ko', sa.Text),
        sa.Column('description_ja', sa.Text),
        sa.Column('description_source', sa.String(50)),
        sa.Column('description_source_url', sa.String(500)),
        sa.Column('wikipedia_url', sa.String(500)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # 1c. person_names table
    op.create_table(
        'person_names',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('person_id', sa.Integer, sa.ForeignKey('persons.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('name_ko', sa.String(255)),
        sa.Column('name_ja', sa.String(255)),
        sa.Column('valid_from', sa.Integer),
        sa.Column('valid_until', sa.Integer),
        sa.Column('language', sa.String(10), server_default='en'),
        sa.Column('is_primary', sa.Boolean, server_default='false'),
        sa.Column('name_type', sa.String(30), server_default='official'),
        sa.Column('source', sa.String(100)),
        sa.Column('wikidata_id', sa.String(50), index=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # ========================================================
    # Phase 2: Migrate data from persons to person_details
    # ========================================================

    # 2a. Copy detail columns from persons → person_details
    # Only for persons that have at least one non-null detail field
    op.execute("""
        INSERT INTO person_details (
            person_id, slug, wikipedia_url, image_url,
            birth_month, birth_day, death_month, death_day,
            birth_date_precision, death_date_precision,
            biography, biography_ko, biography_ja,
            biography_source, biography_source_url,
            category_id, era
        )
        SELECT
            id, slug, wikipedia_url, image_url,
            birth_month, birth_day, death_month, death_day,
            birth_date_precision, death_date_precision,
            biography, biography_ko, biography_ja,
            biography_source, biography_source_url,
            category_id, era
        FROM persons
        WHERE slug IS NOT NULL
           OR wikipedia_url IS NOT NULL
           OR image_url IS NOT NULL
           OR birth_month IS NOT NULL
           OR birth_day IS NOT NULL
           OR death_month IS NOT NULL
           OR death_day IS NOT NULL
           OR biography IS NOT NULL
           OR biography_ko IS NOT NULL
           OR biography_ja IS NOT NULL
           OR category_id IS NOT NULL
           OR era IS NOT NULL
    """)

    # 2b. Migrate name_original → person_names (name_type='native')
    op.execute("""
        INSERT INTO person_names (person_id, name, language, name_type, is_primary, source)
        SELECT id, name_original, 'native', 'native', FALSE, 'migration'
        FROM persons
        WHERE name_original IS NOT NULL AND name_original != ''
    """)

    # ========================================================
    # Phase 3: Add floruit columns if they don't exist
    # ========================================================
    # floruit_start/end already exist from V1 schema, so skip

    # ========================================================
    # Phase 4: Drop columns from persons
    # ========================================================

    # Drop columns that moved to person_details
    columns_to_drop = [
        'slug', 'birth_month', 'birth_day', 'death_month', 'death_day',
        'birth_date_precision', 'death_date_precision',
        'biography', 'biography_ko', 'biography_ja',
        'biography_source', 'biography_source_url',
        'image_url', 'wikipedia_url',
        'category_id', 'era',
        'name_original',
    ]
    for col in columns_to_drop:
        try:
            op.drop_column('persons', col)
        except Exception:
            pass  # Column may not exist

    # Drop fully deleted columns
    deleted_columns = [
        'canonical_id', 'primary_polity_id',
        'mention_count', 'avg_confidence',
        'connection_count', 'is_light',
        'enriched_by', 'enriched_at', 'enrichment_version',
        'data_quality', 'source_type', 'verified_at',
    ]
    for col in deleted_columns:
        try:
            op.drop_column('persons', col)
        except Exception:
            pass  # Column may not exist

    # ========================================================
    # Phase 5: Ensure wikidata_id has UNIQUE constraint
    # ========================================================
    try:
        op.create_index('ix_persons_wikidata_id_unique', 'persons', ['wikidata_id'], unique=True)
    except Exception:
        pass  # Index may already exist


def downgrade():
    # Re-add columns to persons (data will be lost from person_details)
    columns_to_readd = [
        ('slug', sa.String(255)),
        ('birth_month', sa.Integer),
        ('birth_day', sa.Integer),
        ('death_month', sa.Integer),
        ('death_day', sa.Integer),
        ('birth_date_precision', sa.String(20)),
        ('death_date_precision', sa.String(20)),
        ('biography', sa.Text),
        ('biography_ko', sa.Text),
        ('biography_ja', sa.Text),
        ('biography_source', sa.String(50)),
        ('biography_source_url', sa.String(500)),
        ('image_url', sa.String(500)),
        ('wikipedia_url', sa.String(500)),
        ('category_id', sa.Integer),
        ('era', sa.String(100)),
        ('name_original', sa.String(255)),
        ('canonical_id', sa.Integer),
        ('primary_polity_id', sa.Integer),
        ('mention_count', sa.Integer),
        ('avg_confidence', sa.Float),
        ('connection_count', sa.Integer),
        ('is_light', sa.Boolean),
        ('enriched_by', sa.String(100)),
        ('enriched_at', sa.DateTime),
        ('enrichment_version', sa.String(50)),
        ('data_quality', sa.String(50)),
        ('source_type', sa.String(50)),
        ('verified_at', sa.DateTime),
    ]

    for col_name, col_type in columns_to_readd:
        try:
            op.add_column('persons', sa.Column(col_name, col_type))
        except Exception:
            pass

    # Restore data from person_details back to persons
    op.execute("""
        UPDATE persons p SET
            slug = pd.slug,
            wikipedia_url = pd.wikipedia_url,
            image_url = pd.image_url,
            birth_month = pd.birth_month,
            birth_day = pd.birth_day,
            death_month = pd.death_month,
            death_day = pd.death_day,
            birth_date_precision = pd.birth_date_precision,
            death_date_precision = pd.death_date_precision,
            biography = pd.biography,
            biography_ko = pd.biography_ko,
            biography_ja = pd.biography_ja,
            biography_source = pd.biography_source,
            biography_source_url = pd.biography_source_url,
            category_id = pd.category_id,
            era = pd.era
        FROM person_details pd
        WHERE pd.person_id = p.id
    """)

    # Restore name_original from person_names
    op.execute("""
        UPDATE persons p SET name_original = pn.name
        FROM person_names pn
        WHERE pn.person_id = p.id AND pn.name_type = 'native'
    """)

    # Drop new tables
    op.drop_table('person_names')
    op.drop_table('location_details')
    op.drop_table('person_details')
