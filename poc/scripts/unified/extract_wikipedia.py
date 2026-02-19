"""
Wikipedia에서 통합 스키마로 추출.

1. Wikipedia 문서 → sources
2. 본문 링크 → links + mentions
3. Navbox → tags + entity_tags

Usage:
    python extract_wikipedia.py --event "Battle of Waterloo" --dry-run
    python extract_wikipedia.py --event-list events.txt --save
"""

import sys
import os
import re
import json
import argparse
import psycopg2
from datetime import datetime
from pathlib import Path

# libzim import
try:
    from libzim.reader import Archive
except ImportError:
    print("Error: libzim not installed. Run: pip install libzim")
    sys.exit(1)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ZIM_PATH = 'C:/Projects/Chaldeas/data/kiwix/wikipedia_en_nopic.zim'

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}


SITELINKS_FILE = 'poc/data/wikipedia_extract/wiki_sitelinks.json'


class WikiExtractor:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.zim = Archive(ZIM_PATH)
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()

        # DB 캐시
        self.persons_by_qid = {}
        self.events_by_qid = {}
        self.locations_by_qid = {}

        # Wikipedia 타이틀 → 엔티티 매핑 (Wikidata sitelinks)
        self.wiki_to_entity = {}

        self._load_db_cache()
        self._load_sitelinks()

        # 통계
        self.stats = {
            'sources_created': 0,
            'mentions_created': 0,
            'links_created': 0,
            'tags_created': 0,
            'entity_tags_created': 0,
            'matched_by_sitelink': 0,
            'matched_by_name': 0,
            'tentative_created': 0,
            'unmatched': 0,
        }

    def _load_db_cache(self):
        """DB에서 QID 및 타이틀 매핑 로드."""
        print("Loading DB cache...")

        # QID 매핑
        self.cur.execute("SELECT id, wikidata_id FROM persons WHERE wikidata_id IS NOT NULL")
        self.persons_by_qid = {row[1]: row[0] for row in self.cur.fetchall()}

        self.cur.execute("SELECT id, wikidata_id FROM events WHERE wikidata_id IS NOT NULL")
        self.events_by_qid = {row[1]: row[0] for row in self.cur.fetchall()}

        self.cur.execute("SELECT id, wikidata_id FROM locations WHERE wikidata_id IS NOT NULL")
        self.locations_by_qid = {row[1]: row[0] for row in self.cur.fetchall()}

        # 타이틀 → (type, id, qid) 매핑 (Wikipedia 타이틀로 찾기 위해)
        self.entity_by_title = {}

        self.cur.execute("SELECT id, wikidata_id, name FROM persons WHERE wikidata_id IS NOT NULL")
        for row in self.cur.fetchall():
            title = row[2].replace(' ', '_')
            self.entity_by_title[title] = ('person', row[0], row[1])
            self.entity_by_title[row[2]] = ('person', row[0], row[1])

        self.cur.execute("SELECT id, wikidata_id, title FROM events WHERE wikidata_id IS NOT NULL")
        for row in self.cur.fetchall():
            title = row[2].replace(' ', '_') if row[2] else None
            if title:
                self.entity_by_title[title] = ('event', row[0], row[1])
                self.entity_by_title[row[2]] = ('event', row[0], row[1])

        self.cur.execute("SELECT id, wikidata_id, name FROM locations WHERE wikidata_id IS NOT NULL")
        for row in self.cur.fetchall():
            title = row[2].replace(' ', '_') if row[2] else None
            if title:
                self.entity_by_title[title] = ('location', row[0], row[1])
                self.entity_by_title[row[2]] = ('location', row[0], row[1])

        print(f"  persons: {len(self.persons_by_qid):,}")
        print(f"  events: {len(self.events_by_qid):,}")
        print(f"  locations: {len(self.locations_by_qid):,}")
        print(f"  title mappings: {len(self.entity_by_title):,}")

    def _load_sitelinks(self):
        """Wikidata sitelinks 매핑 로드 (Wikipedia 타이틀 → 엔티티)."""
        if not os.path.exists(SITELINKS_FILE):
            print(f"  sitelinks: FILE NOT FOUND ({SITELINKS_FILE})")
            return

        with open(SITELINKS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.wiki_to_entity = data.get('wiki_to_entity', {})
        print(f"  sitelinks: {len(self.wiki_to_entity):,} mappings")

    def get_entity_by_wiki_title(self, wiki_title, source_title=None):
        """
        Wikipedia 타이틀로 엔티티 조회.
        0. 기존 별칭에서 찾기
        1. sitelinks 매핑에서 찾기 (우선)
        2. DB 이름 매칭으로 fallback
        3. 리다이렉트 따라가서 다시 시도
        4. 로컬 Wikipedia 덤프에서 찾아서 생성
        5. 없으면 unmatched_candidates에 저장
        """
        original_title = wiki_title  # 별칭 등록용

        # 0. 기존 별칭에서 찾기
        alias_result = self.get_entity_by_alias(wiki_title)
        if alias_result:
            self.stats['matched_by_sitelink'] += 1  # 별칭도 sitelink 카운트에 포함
            return alias_result

        # 1. Sitelinks 매핑 (정확한 Wikipedia 타이틀)
        if wiki_title in self.wiki_to_entity:
            info = self.wiki_to_entity[wiki_title]
            self.stats['matched_by_sitelink'] += 1
            return (info['type'], info['id'], info['qid'])

        # 언더스코어 버전
        wiki_title_underscore = wiki_title.replace(' ', '_')
        if wiki_title_underscore in self.wiki_to_entity:
            info = self.wiki_to_entity[wiki_title_underscore]
            self.stats['matched_by_sitelink'] += 1
            return (info['type'], info['id'], info['qid'])

        # 2. DB 이름 매칭 (fallback)
        result = self.get_entity_by_title(wiki_title)
        if result[0]:
            self.stats['matched_by_name'] += 1
            return result

        # 3. 리다이렉트 따라가서 다시 시도 (Mozart → Wolfgang Amadeus Mozart)
        canonical_title = self.get_canonical_title(wiki_title)
        if canonical_title and canonical_title != wiki_title and canonical_title != wiki_title_underscore:
            # 정식 이름으로 다시 검색
            result = self._find_entity_direct(canonical_title)
            if result[0]:
                # 별칭 등록
                self.register_alias(original_title, canonical_title, result[0], result[1])
                self.stats['matched_by_sitelink'] += 1
                return result

        # 4. tentative_entities에 저장 (나중에 LLM이 분류)
        tentative_id = self.save_tentative_entity(canonical_title or wiki_title, source_title)
        if tentative_id:
            self.stats['tentative_created'] += 1
            return ('tentative', tentative_id, None)

        self.stats['unmatched'] += 1
        return (None, None, None)

    def _find_entity_direct(self, wiki_title):
        """sitelinks/DB에서 직접 검색 (재귀 방지용)."""
        if wiki_title in self.wiki_to_entity:
            info = self.wiki_to_entity[wiki_title]
            return (info['type'], info['id'], info['qid'])

        wiki_title_underscore = wiki_title.replace(' ', '_')
        if wiki_title_underscore in self.wiki_to_entity:
            info = self.wiki_to_entity[wiki_title_underscore]
            return (info['type'], info['id'], info['qid'])

        return self.get_entity_by_title(wiki_title)

    def get_entity_by_alias(self, alias):
        """별칭 테이블에서 엔티티 조회."""
        try:
            self.cur.execute("""
                SELECT entity_type, entity_id FROM entity_aliases
                WHERE alias = %s OR alias = %s
            """, (alias, alias.replace(' ', '_')))
            row = self.cur.fetchone()
            if row:
                return (row[0], row[1], None)
        except:
            self.conn.rollback()
        return None

    def register_alias(self, alias, canonical_name, entity_type, entity_id):
        """별칭 등록 (Mozart → Wolfgang Amadeus Mozart)."""
        if self.dry_run or not alias or not entity_type or not entity_id:
            return
        try:
            # 기존 entity_aliases 테이블 구조 사용
            self.cur.execute("""
                INSERT INTO entity_aliases (alias, entity_type, entity_id, alias_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (alias, entity_type, entity_id, 'wikipedia_redirect'))
            self.conn.commit()
        except:
            self.conn.rollback()

    def get_canonical_title(self, href):
        """ZIM에서 리다이렉트 따라가서 정식 타이틀 반환."""
        try:
            path = f"A/{href.replace(' ', '_')}"
            entry = self.zim.get_entry_by_path(path)
            item = entry.get_item()
            # item.title이 정식 타이틀 (리다이렉트 대상)
            return item.title
        except:
            return None

    def create_entity_from_wikipedia(self, wiki_title):
        """
        로컬 Wikipedia 덤프에서 문서를 찾아 새 엔티티 생성.
        반환: (type, id, qid) 또는 None
        """
        if self.dry_run:
            return None

        try:
            # Wikipedia 문서 가져오기
            path = f"A/{wiki_title.replace(' ', '_')}"
            entry = self.zim.get_entry_by_path(path)
            item = entry.get_item()
            html = bytes(item.content).decode('utf-8', errors='replace')

            # QID 추출
            qid = self.extract_qid(html)

            # 엔티티 타입 추측 (카테고리 기반)
            entity_type = self.guess_entity_type(html, wiki_title)
            if not entity_type:
                return None

            # 첫 문단 추출 (설명용)
            first_para = self.extract_first_paragraph(html)

            # slug 생성
            slug = self.generate_slug(wiki_title)
            description = self.clean_html(first_para)[:500] if first_para else None

            # DB에 새 엔티티 생성
            now = datetime.now()
            name = wiki_title.replace('_', ' ')

            # 자동 분류 메타데이터
            classification = 'title_heuristic'

            if entity_type == 'person':
                # created_at, updated_at 필수
                if qid:
                    self.cur.execute("""
                        INSERT INTO persons (name, slug, wikidata_id, description, created_at, updated_at, auto_created_at, auto_created_source, classification_method, needs_review)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
                        RETURNING id
                    """, (name, slug, qid, description, now, now, now, 'wikipedia_extract', classification, True))
                else:
                    self.cur.execute("""
                        INSERT INTO persons (name, slug, description, created_at, updated_at, auto_created_at, auto_created_source, classification_method, needs_review)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (name, slug, description, now, now, now, 'wikipedia_extract', classification, True))
                new_id = self.cur.fetchone()[0]
                self.conn.commit()
                if qid:
                    self.persons_by_qid[qid] = new_id
                return ('person', new_id, qid)

            elif entity_type == 'event':
                # date_start, created_at, updated_at 필수 - 플레이스홀더 사용
                if qid:
                    self.cur.execute("""
                        INSERT INTO events (title, slug, wikidata_id, description, date_start, created_at, updated_at, auto_created_at, auto_created_source, classification_method, needs_review)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (wikidata_id) DO UPDATE SET title = EXCLUDED.title
                        RETURNING id
                    """, (name, slug, qid, description, 0, now, now, now, 'wikipedia_extract', classification, True))
                else:
                    self.cur.execute("""
                        INSERT INTO events (title, slug, description, date_start, created_at, updated_at, auto_created_at, auto_created_source, classification_method, needs_review)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (name, slug, description, 0, now, now, now, 'wikipedia_extract', classification, True))
                new_id = self.cur.fetchone()[0]
                self.conn.commit()
                if qid:
                    self.events_by_qid[qid] = new_id
                return ('event', new_id, qid)

            elif entity_type == 'location':
                if qid:
                    self.cur.execute("""
                        INSERT INTO locations (name, wikidata_id, description, auto_created_at, auto_created_source, classification_method, needs_review)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
                        RETURNING id
                    """, (name, qid, description, now, 'wikipedia_extract', classification, True))
                else:
                    self.cur.execute("""
                        INSERT INTO locations (name, description, auto_created_at, auto_created_source, classification_method, needs_review)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (name, description, now, 'wikipedia_extract', classification, True))
                new_id = self.cur.fetchone()[0]
                self.conn.commit()
                if qid:
                    self.locations_by_qid[qid] = new_id
                return ('location', new_id, qid)

        except Exception as e:
            # 문서 없거나 오류 → rollback 후 None 반환
            print(f"  [create_entity_from_wikipedia ERROR] {wiki_title}: {e}")
            self.conn.rollback()
            return None

        return None

    def generate_slug(self, title):
        """URL-friendly slug 생성."""
        import re
        slug = title.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug)
        slug = slug[:100]  # 최대 100자
        return slug

    def guess_entity_type(self, html, title):
        """HTML 카테고리로 엔티티 타입 추측."""
        html_lower = html.lower()

        # 인물 키워드
        person_keywords = ['birth', 'death', 'biography', 'people from', 'politicians',
                          'military personnel', 'monarchs', 'emperors', 'kings', 'queens',
                          'presidents', 'philosophers', 'scientists', 'writers', 'artists']
        # 이벤트 키워드
        event_keywords = ['battles', 'wars', 'revolutions', 'treaties', 'sieges', 'campaigns',
                         'conflicts', 'rebellions', 'uprisings', 'massacres', 'invasions']
        # 장소 키워드
        location_keywords = ['cities', 'countries', 'regions', 'provinces', 'capitals',
                            'geography', 'populated places', 'landforms', 'municipalities']

        # 카테고리 섹션에서 검색
        cat_section = html_lower[html_lower.find('category'):] if 'category' in html_lower else html_lower

        person_score = sum(1 for k in person_keywords if k in cat_section)
        event_score = sum(1 for k in event_keywords if k in cat_section)
        location_score = sum(1 for k in location_keywords if k in cat_section)

        # 타이틀로 강력하게 추측
        title_lower = title.lower()
        if title_lower.startswith('battle of') or title_lower.startswith('siege of'):
            event_score += 10  # 거의 확실
        elif any(k in title_lower for k in ['war of', 'treaty of', 'campaign']):
            event_score += 5

        if any(k in title_lower for k in [' dynasty', ' empire', ' kingdom', ' republic']):
            event_score += 3  # 왕조/제국은 event 취급

        if title_lower.endswith(' city') or title_lower.endswith(' province'):
            location_score += 5

        # 최고 점수 타입 반환 (최소 2점 이상)
        max_score = max(person_score, event_score, location_score)
        if max_score < 2:
            return None  # 확신 없으면 생성 안 함

        if person_score == max_score:
            return 'person'
        elif event_score == max_score:
            return 'event'
        else:
            return 'location'

    def save_tentative_entity(self, wiki_title, source_title=None):
        """임시 엔티티 저장 (나중에 LLM이 분류)."""
        if self.dry_run or not wiki_title:
            return None
        try:
            self.cur.execute("""
                INSERT INTO tentative_entities (wiki_title, mentioned_in)
                VALUES (%s, %s)
                ON CONFLICT (wiki_title) DO UPDATE SET
                    mention_count = tentative_entities.mention_count + 1,
                    mentioned_in = array_append(tentative_entities.mentioned_in, %s),
                    last_seen_at = NOW()
                RETURNING id
            """, (wiki_title, [source_title] if source_title else [], source_title))
            result = self.cur.fetchone()
            self.conn.commit()
            return result[0] if result else None
        except Exception as e:
            self.conn.rollback()
            return None

    def save_unmatched_candidate(self, wiki_title, source_title=None):
        """매칭 실패한 엔티티를 후보 테이블에 저장."""
        if self.dry_run:
            return

        try:
            self.cur.execute("""
                INSERT INTO unmatched_candidates (wiki_title, mentioned_in_sources, guessed_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (wiki_title) DO UPDATE SET
                    mention_count = unmatched_candidates.mention_count + 1,
                    mentioned_in_sources = array_append(
                        CASE WHEN %s = ANY(unmatched_candidates.mentioned_in_sources)
                             THEN unmatched_candidates.mentioned_in_sources
                             ELSE unmatched_candidates.mentioned_in_sources END,
                        CASE WHEN %s = ANY(unmatched_candidates.mentioned_in_sources)
                             THEN NULL ELSE %s END
                    ),
                    last_seen_at = NOW()
            """, (wiki_title, [source_title] if source_title else [], 'unknown',
                  source_title, source_title, source_title))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()  # 오류 시 rollback

    def get_article(self, title):
        """ZIM에서 문서 가져오기."""
        # 타이틀 정규화
        title = self.normalize_title(title)

        # 여러 변형 시도
        variants = [
            title,
            title.replace("'s", "'s"),  # 's → 's
            title.replace("'", "'"),    # ' → '
        ]

        for variant in variants:
            try:
                path = f"A/{variant.replace(' ', '_')}"
                entry = self.zim.get_entry_by_path(path)
                item = entry.get_item()
                content = bytes(item.content).decode('utf-8', errors='replace')
                return content
            except:
                continue

        print(f"  Article not found: {title}")
        return None

    def extract_qid(self, html):
        """Wikipedia HTML에서 Wikidata QID 추출."""
        # 방법 1: wikibase-entity 링크
        match = re.search(r'href="https://www\.wikidata\.org/wiki/(Q\d+)"', html)
        if match:
            return match.group(1)

        # 방법 2: data-wikidata-id 속성
        match = re.search(r'data-wikidata-id="(Q\d+)"', html)
        if match:
            return match.group(1)

        return None

    def extract_first_paragraph(self, html):
        """첫 문단 추출 (설명용)."""
        # <p> 태그에서 첫 의미 있는 문단
        paragraphs = re.findall(r'<p[^>]*>(.+?)</p>', html, re.DOTALL)
        for p in paragraphs:
            # HTML 태그 제거
            text = re.sub(r'<[^>]+>', '', p)
            text = text.strip()
            if len(text) > 100:  # 의미 있는 길이
                return text[:2000]
        return None

    def clean_html(self, text):
        """HTML 태그 및 특수문자 완전 제거."""
        # 불완전한 HTML 태그 제거 (시작 부분)
        text = re.sub(r'^[^<]*>', '', text)
        # 불완전한 HTML 태그 제거 (끝 부분)
        text = re.sub(r'<[^>]*$', '', text)
        # HTML 태그 제거 (완전한 것들)
        text = re.sub(r'<[^>]+>', ' ', text)
        # CSS 주석 제거 (/* ... */)
        text = re.sub(r'/\*[^*]*\*+(?:[^/*][^*]*\*+)*/', ' ', text)
        # 불완전한 CSS 주석 제거 (시작/끝만 있는 경우)
        text = re.sub(r'/\*.*$', '', text)  # /* 이후 끝까지
        text = re.sub(r'^[^/]*\*/', '', text)  # 시작부터 */ 까지
        # CSS 클래스 잔재 제거 (.mw-*, .geo-*, .reference 등)
        text = re.sub(r'\.[a-z][a-z0-9-]*', ' ', text)
        # HTML 엔티티 변환
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = re.sub(r'&#\d+;', ' ', text)  # 숫자 엔티티
        text = re.sub(r'&[a-z]+;', ' ', text)  # 이름 엔티티
        # CSS/스타일 잔재 제거
        text = re.sub(r'[a-z-]+:\s*[^;]+;', ' ', text)
        text = re.sub(r'\{[^}]+\}', ' ', text)
        # 남은 < > 제거
        text = re.sub(r'[<>]', ' ', text)
        # 연속 공백 정리
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def normalize_title(self, title):
        """타이틀 정규화 (아포스트로피 등)."""
        # 다양한 아포스트로피 통일
        title = title.replace(''', "'")
        title = title.replace(''', "'")
        title = title.replace('`', "'")
        title = title.replace('´', "'")
        return title

    def extract_body_links(self, html):
        """본문에서 링크 추출 (링크 + 주변 텍스트)."""
        links = []
        seen_targets = set()  # 중복 링크 방지

        # 링크 패턴: <a href="Article_Name" title="Article Name">
        link_pattern = r'<a[^>]*href="([^"#]+)"[^>]*title="([^"]+)"[^>]*>([^<]*)</a>'

        for match in re.finditer(link_pattern, html):
            href = match.group(1)
            title = match.group(2)
            link_text = match.group(3)

            # Wikipedia 내부 링크만 (CSS, JS 등 제외)
            if href.startswith('.') or href.startswith('http') or href.startswith('/'):
                continue
            if ':' in href:  # Category:, File: 등 제외
                continue

            # URL 디코딩
            from urllib.parse import unquote
            href = unquote(href)
            title = unquote(title)
            title = self.normalize_title(title)

            # 중복 체크
            if title in seen_targets:
                continue
            seen_targets.add(title)

            # 주변 텍스트 추출 (링크 포함 문장)
            start = max(0, match.start() - 300)
            end = min(len(html), match.end() + 300)
            context = html[start:end]

            # HTML 완전 제거
            context = self.clean_html(context)

            if len(context) >= 50:
                links.append({
                    'target_title': title,
                    'href': href,
                    'link_text': link_text,
                    'evidence_raw': context[:500]
                })

        return links

    def extract_navboxes(self, html):
        """Navbox에서 그룹 정보 추출."""
        navboxes = []

        # Navbox 패턴
        navbox_pattern = r'<div[^>]*class="[^"]*navbox[^"]*"[^>]*>(.*?)</div>\s*</div>'

        for match in re.finditer(navbox_pattern, html, re.DOTALL):
            navbox_html = match.group(1)

            # 제목 추출
            title_match = re.search(r'<th[^>]*class="[^"]*navbox-title[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>', navbox_html, re.DOTALL)
            if not title_match:
                continue

            navbox_title = title_match.group(1).strip()

            # 멤버 링크 추출
            members = []
            link_pattern = r'<a[^>]*href="([^"#]+)"[^>]*title="([^"]+)"[^>]*>([^<]+)</a>'

            for link_match in re.finditer(link_pattern, navbox_html):
                members.append({
                    'href': link_match.group(1),
                    'title': link_match.group(2),
                    'text': link_match.group(3)
                })

            if members:
                navboxes.append({
                    'navbox_title': navbox_title,
                    'members': members
                })

        return navboxes

    def get_entity_type_and_id(self, qid):
        """QID로 엔티티 타입과 ID 조회."""
        if qid in self.persons_by_qid:
            return 'person', self.persons_by_qid[qid]
        if qid in self.events_by_qid:
            return 'event', self.events_by_qid[qid]
        if qid in self.locations_by_qid:
            return 'location', self.locations_by_qid[qid]
        return None, None

    def get_entity_by_title(self, title):
        """타이틀로 엔티티 타입, ID, QID 조회."""
        # 정확히 일치
        if title in self.entity_by_title:
            return self.entity_by_title[title]

        # 언더스코어 → 공백
        title_space = title.replace('_', ' ')
        if title_space in self.entity_by_title:
            return self.entity_by_title[title_space]

        # 공백 → 언더스코어
        title_underscore = title.replace(' ', '_')
        if title_underscore in self.entity_by_title:
            return self.entity_by_title[title_underscore]

        return None, None, None

    def process_article(self, title, source_entity=None):
        """
        문서 하나 처리.
        source_entity: (type, id, qid) - 이 문서가 설명하는 엔티티
        """
        print(f"\nProcessing: {title}")

        html = self.get_article(title)
        if not html:
            return None

        # 1. 소스 엔티티 찾기 (sitelinks 우선)
        if not source_entity:
            source_entity = self.get_entity_by_wiki_title(title)

        source_type, source_id, source_qid = source_entity if source_entity else (None, None, None)
        print(f"  Source entity: {source_type}/{source_id} ({source_qid})")

        # 2. 첫 문단 추출
        first_para = self.extract_first_paragraph(html)
        print(f"  First para: {len(first_para) if first_para else 0} chars")

        # 3. sources 테이블에 저장 (중복 체크)
        db_source_id = None
        if not self.dry_run:
            # 이미 있는지 체크
            self.cur.execute(
                "SELECT id FROM sources WHERE source_type = %s AND title = %s",
                ('wikipedia', title)
            )
            existing = self.cur.fetchone()
            if existing:
                db_source_id = existing[0]
                print(f"  Source already exists: id={db_source_id}")
            else:
                self.cur.execute("""
                    INSERT INTO sources (source_type, title, content_raw, url)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, ('wikipedia', title, first_para or '', f'https://en.wikipedia.org/wiki/{title.replace(" ", "_")}'))
                db_source_id = self.cur.fetchone()[0]
                self.conn.commit()  # source 즉시 커밋 (FK 제약 해결)
                self.stats['sources_created'] += 1

        # 4. 본문 링크 추출
        body_links = self.extract_body_links(html)
        print(f"  Body links: {len(body_links)}")

        # 5. 링크 처리 → links + mentions
        links_created = 0
        mentions_created = 0
        matched_links = 0

        for link_data in body_links:
            target_title = link_data['target_title']
            href = link_data.get('href', target_title)
            evidence_raw = link_data['evidence_raw']

            # 타겟 엔티티 찾기 (sitelinks 우선, ZIM 리다이렉트 추적)
            target_entity = self.get_entity_by_wiki_title(target_title)
            if not target_entity[0]:
                # href로 시도
                target_entity = self.get_entity_by_wiki_title(href)
            if not target_entity[0]:
                # ZIM에서 정식 타이틀 가져와서 시도
                canonical = self.get_canonical_title(href)
                if canonical and canonical != href and canonical != target_title:
                    target_entity = self.get_entity_by_wiki_title(canonical)
            if not target_entity[0]:
                continue

            target_type, target_id, target_qid = target_entity
            matched_links += 1

            if not self.dry_run and source_id:
                # 중복 링크 체크
                self.cur.execute("""
                    SELECT id FROM links
                    WHERE from_type = %s AND from_id = %s AND to_type = %s AND to_id = %s
                """, (source_type, source_id, target_type, target_id))
                existing_link = self.cur.fetchone()

                if existing_link:
                    link_id = existing_link[0]
                    # 새 mention만 추가 (다른 출처에서 같은 연결 발견)
                    self.cur.execute("""
                        INSERT INTO mentions (source_id, target_type, target_id, evidence_raw)
                        VALUES (%s, %s, %s, %s)
                    """, (db_source_id, 'link', link_id, evidence_raw))
                    mentions_created += 1
                else:
                    # links 테이블에 저장
                    self.cur.execute("""
                        INSERT INTO links (from_type, from_id, to_type, to_id, category)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                    """, (source_type, source_id, target_type, target_id, None))  # category는 나중에 분류
                    link_id = self.cur.fetchone()[0]
                    links_created += 1

                    # mentions 테이블에 저장 (link에 대한 근거)
                    self.cur.execute("""
                        INSERT INTO mentions (source_id, target_type, target_id, evidence_raw)
                        VALUES (%s, %s, %s, %s)
                    """, (db_source_id, 'link', link_id, evidence_raw))
                    mentions_created += 1

        print(f"  Matched to DB: {matched_links}")
        print(f"  Links created: {links_created}")
        print(f"  Mentions created: {mentions_created}")

        self.stats['links_created'] += links_created
        self.stats['mentions_created'] += mentions_created

        # 6. Navbox 추출 → tags + entity_tags
        navboxes = self.extract_navboxes(html)
        print(f"  Navboxes: {len(navboxes)}")

        tags_created = 0
        entity_tags_created = 0

        for navbox in navboxes:
            navbox_title = navbox['navbox_title']
            members = navbox.get('members', [])

            if not self.dry_run:
                # tag 생성 또는 조회
                self.cur.execute("SELECT id FROM tags WHERE name = %s", (navbox_title,))
                row = self.cur.fetchone()
                if row:
                    tag_id = row[0]
                else:
                    self.cur.execute("""
                        INSERT INTO tags (name, navbox_template)
                        VALUES (%s, %s)
                        RETURNING id
                    """, (navbox_title, f'Template:{navbox_title.replace(" ", "_")}'))
                    tag_id = self.cur.fetchone()[0]
                    tags_created += 1

                # 멤버들을 entity_tags로 연결
                for member in members:
                    member_title = member.get('title', '')
                    member_href = member.get('href', '')

                    # 엔티티 찾기
                    entity = self.get_entity_by_wiki_title(member_title)
                    if not entity[0]:
                        entity = self.get_entity_by_wiki_title(member_href)
                    if not entity[0]:
                        canonical = self.get_canonical_title(member_href)
                        if canonical:
                            entity = self.get_entity_by_wiki_title(canonical)

                    if entity[0]:
                        entity_type, entity_id, _ = entity
                        # 중복 체크
                        self.cur.execute("""
                            SELECT id FROM entity_tags
                            WHERE entity_type = %s AND entity_id = %s AND tag_id = %s
                        """, (entity_type, entity_id, tag_id))
                        if not self.cur.fetchone():
                            self.cur.execute("""
                                INSERT INTO entity_tags (entity_type, entity_id, tag_id, source_id)
                                VALUES (%s, %s, %s, %s)
                            """, (entity_type, entity_id, tag_id, db_source_id))
                            entity_tags_created += 1

        self.stats['tags_created'] += tags_created
        self.stats['entity_tags_created'] += entity_tags_created

        if not self.dry_run:
            self.conn.commit()

        return {
            'title': title,
            'source_entity': source_entity,
            'body_links': len(body_links),
            'matched_links': matched_links,
            'navboxes': len(navboxes)
        }

    def print_summary(self):
        """통계 출력."""
        print("\n" + "=" * 60)
        print("EXTRACTION SUMMARY" + (" (DRY RUN)" if self.dry_run else ""))
        print("=" * 60)
        for key, value in self.stats.items():
            print(f"  {key}: {value:,}")

    def close(self):
        self.conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--event', help='단일 이벤트 처리')
    parser.add_argument('--event-list', help='이벤트 목록 파일')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--save', action='store_true')
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()

    if not args.dry_run and not args.save:
        print("Error: --dry-run or --save required")
        return

    extractor = WikiExtractor(dry_run=args.dry_run)

    if args.event:
        extractor.process_article(args.event)
    elif args.event_list:
        with open(args.event_list, 'r', encoding='utf-8') as f:
            events = [line.strip() for line in f if line.strip()]

        for i, event in enumerate(events[:args.limit]):
            extractor.process_article(event)
            if (i + 1) % 10 == 0:
                print(f"\nProgress: {i + 1}/{min(len(events), args.limit)}")
    else:
        # 테스트용 기본 이벤트
        extractor.process_article("Battle of Waterloo")

    extractor.print_summary()
    extractor.close()


if __name__ == '__main__':
    main()
