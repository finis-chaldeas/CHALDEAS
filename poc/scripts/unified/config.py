"""
통합 추출 시스템 설정
"""

from pathlib import Path

# ============================================
# 경로 설정 (E: 드라이브 통일)
# ============================================

# 입력 (E: 드라이브)
WIKIDATA_JSON = Path("E:/wikidata/latest-all.json")  # 압축 해제된 전체 덤프 (1.6TB)
WIKIPEDIA_ZIM = Path("E:/chaldeas_data/kiwix/wikipedia_en_nopic.zim")
GUTENBERG_ZIM = Path("E:/chaldeas_data/kiwix/gutenberg_en_all.zim")

# 출력 (E: 드라이브)
OUTPUT_DIR = Path("E:/chaldeas_data/unified")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 중간 파일
QID_WIKI_MAP = OUTPUT_DIR / "qid_wiki_map.json"
WIKIDATA_EXTRACTED = OUTPUT_DIR / "wikidata_full_multilang.jsonl"  # 다국어 보강 버전
WIKIPEDIA_EXTRACTED = OUTPUT_DIR / "wikipedia_full.jsonl"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# DB 설정
# ============================================

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}

# ============================================
# 엔티티 타입 분류
# ============================================

# P31 값 → 엔티티 타입
PERSON_TYPES = {'Q5'}  # human

LOCATION_TYPES = {
    'Q515',     # city
    'Q3957',    # town
    'Q532',     # village
    'Q5119',    # capital
    'Q486972',  # human settlement
    'Q839954',  # archaeological site
    'Q4895508', # historical country
    'Q41176',   # building
    'Q16560',   # palace
    'Q23413',   # castle
    'Q8502',    # mountain
    'Q4022',    # river
    'Q23397',   # lake
    'Q23442',   # island
    'Q165',     # sea
    'Q9430',    # ocean
}

TERRITORY_TYPES = {
    'Q6256',    # country
    'Q3624078', # sovereign state
    'Q48349',   # empire
    'Q417175',  # former country
    'Q3024240', # historical country
    'Q7270',    # republic
    'Q28575',   # city-state
    'Q5107',    # continent
    'Q82794',   # geographic region
}

GROUP_TYPES = {
    'Q176799',  # military unit
    'Q37726',   # dynasty
    'Q189573',  # religious order
    'Q1133779', # religious organization
    'Q41710',   # ethnic group
    'Q43229',   # organization
    'Q7278',    # political party
}

EVENT_TYPES = {
    'Q178561',  # battle
    'Q198',     # war
    'Q180684',  # conflict
    'Q188055',  # siege
    'Q131569',  # treaty
    'Q10931',   # revolution
    'Q124734',  # rebellion
    'Q45382',   # coup
    'Q8465',    # civil war
    'Q13418847', # historical event
    'Q192909',  # disaster
}

# 제외할 타입 (영화, 앨범 등)
EXCLUDED_TYPES = {
    'Q16521',   # taxon
    'Q11424',   # film
    'Q5398426', # TV series
    'Q7725634', # literary work
    'Q482994',  # album
    'Q134556',  # single
}

# ============================================
# 속성 정의
# ============================================

# 주요 속성 이름
PROPERTY_NAMES = {
    # 가족
    "P22": "father",
    "P25": "mother",
    "P26": "spouse",
    "P40": "child",
    "P3373": "sibling",
    "P451": "partner",
    "P1038": "relative",

    # 직업/소속
    "P106": "occupation",
    "P39": "position_held",
    "P108": "employer",
    "P463": "member_of",
    "P102": "political_party",
    "P140": "religion",
    "P69": "educated_at",

    # 이벤트
    "P607": "conflict",
    "P1344": "participant_in",
    "P793": "significant_event",

    # 공간
    "P625": "coordinate",
    "P17": "country",
    "P131": "located_in",
    "P276": "location",
    "P19": "birthplace",
    "P20": "deathplace",
    "P119": "burial_place",
    "P551": "residence",
    "P937": "work_location",
    "P36": "capital",

    # 시간
    "P569": "birth_date",
    "P570": "death_date",
    "P580": "start_time",
    "P582": "end_time",
    "P585": "point_in_time",
    "P571": "inception",
    "P576": "dissolved",

    # 계층
    "P31": "instance_of",
    "P279": "subclass_of",
    "P361": "part_of",
    "P527": "has_part",
    "P155": "follows",
    "P156": "followed_by",
}

# ============================================
# 처리 설정
# ============================================

# 배치 크기
BATCH_SIZE = 10000

# 체크포인트 간격 (줄 수)
CHECKPOINT_INTERVAL = 1000000

# 로그 간격
LOG_INTERVAL = 100000
