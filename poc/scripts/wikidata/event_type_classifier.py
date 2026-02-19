"""
Wikidata 이벤트 타입 분류기.

P31 (instance of) QID를 CHALDEAS 카테고리로 변환.
알 수 없는 타입은 로그에 기록해서 나중에 매핑 추가.
"""

import os
import json
from typing import Dict, Optional, Tuple
from datetime import datetime


class EventTypeClassifier:
    """Wikidata 이벤트 타입 분류기."""

    def __init__(self, mapping_path: str = None):
        self.mapping_path = mapping_path or os.path.join(
            os.path.dirname(__file__), 'event_type_mapping.json'
        )
        self.unknown_log_path = os.path.join(
            os.path.dirname(__file__), 'unknown_event_types.json'
        )

        self.mapping = self._load_mapping()
        self.unknown_types = self._load_unknown_log()

        # QID → (category, nature, label) 빠른 조회용
        self._qid_lookup = self._build_lookup()

    def _load_mapping(self) -> Dict:
        """매핑 파일 로드."""
        if os.path.exists(self.mapping_path):
            with open(self.mapping_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _load_unknown_log(self) -> Dict:
        """알 수 없는 타입 로그 로드."""
        if os.path.exists(self.unknown_log_path):
            with open(self.unknown_log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'_meta': {'description': '알 수 없는 이벤트 타입 로그'}, 'types': {}}

    def _save_unknown_log(self):
        """알 수 없는 타입 로그 저장."""
        with open(self.unknown_log_path, 'w', encoding='utf-8') as f:
            json.dump(self.unknown_types, f, ensure_ascii=False, indent=2)

    def _build_lookup(self) -> Dict[str, Tuple[str, str, str]]:
        """QID → (category, nature, label) 룩업 테이블 생성."""
        lookup = {}

        for category, data in self.mapping.items():
            if category.startswith('_'):  # _meta, _exclude 제외
                continue

            types = data.get('types', {})
            for qid, info in types.items():
                lookup[qid] = (category, info['nature'], info['label'])

        return lookup

    def classify(self, qid: str, label: str = None) -> Tuple[str, str]:
        """
        QID를 카테고리와 nature로 분류.

        Args:
            qid: Wikidata QID (예: Q178561)
            label: 타입 라벨 (알 수 없는 타입 로깅용)

        Returns:
            (category, nature) 튜플
            알 수 없으면 ('unknown', 'unknown')
        """
        if qid in self._qid_lookup:
            category, nature, _ = self._qid_lookup[qid]
            return category, nature

        # 제외 목록에 있으면
        if qid in self.mapping.get('_exclude', {}).get('types', {}):
            return 'excluded', 'excluded'

        # 알 수 없는 타입 - 로그에 기록
        self._log_unknown(qid, label)
        return 'unknown', 'unknown'

    def _log_unknown(self, qid: str, label: str = None):
        """알 수 없는 타입을 로그에 기록."""
        if qid not in self.unknown_types['types']:
            self.unknown_types['types'][qid] = {
                'label': label or 'unknown',
                'first_seen': datetime.now().isoformat(),
                'count': 0
            }

        self.unknown_types['types'][qid]['count'] += 1
        self.unknown_types['types'][qid]['last_seen'] = datetime.now().isoformat()

        # 주기적으로 저장 (10개마다)
        total = sum(t['count'] for t in self.unknown_types['types'].values())
        if total % 10 == 0:
            self._save_unknown_log()

    def get_category_info(self, category: str) -> Optional[Dict]:
        """카테고리 정보 반환."""
        return self.mapping.get(category)

    def get_all_qids_for_category(self, category: str) -> list:
        """특정 카테고리의 모든 QID 반환."""
        if category in self.mapping:
            return list(self.mapping[category].get('types', {}).keys())
        return []

    def get_historical_qids(self) -> list:
        """역사적으로 의미 있는 모든 QID 반환 (exclude 제외)."""
        qids = []
        for category, data in self.mapping.items():
            if category.startswith('_'):
                continue
            qids.extend(data.get('types', {}).keys())
        return qids

    def is_excluded(self, qid: str) -> bool:
        """제외 목록에 있는지 확인."""
        return qid in self.mapping.get('_exclude', {}).get('types', {})

    def get_unknown_types(self) -> Dict:
        """알 수 없는 타입들 반환 (검토용)."""
        return self.unknown_types['types']

    def add_mapping(self, qid: str, category: str, nature: str, label: str):
        """새 매핑 추가 (알 수 없는 타입 해결용)."""
        if category not in self.mapping:
            self.mapping[category] = {'description': '', 'types': {}}

        self.mapping[category]['types'][qid] = {
            'nature': nature,
            'label': label
        }

        # 룩업 테이블 갱신
        self._qid_lookup[qid] = (category, nature, label)

        # 알 수 없는 타입 로그에서 제거
        if qid in self.unknown_types['types']:
            del self.unknown_types['types'][qid]

        # 저장
        self._save_mapping()
        self._save_unknown_log()

    def _save_mapping(self):
        """매핑 파일 저장."""
        with open(self.mapping_path, 'w', encoding='utf-8') as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)

    def print_stats(self):
        """통계 출력."""
        print("\nEvent Type Classifier Stats")
        print("=" * 50)

        total_types = 0
        for category, data in self.mapping.items():
            if category.startswith('_'):
                continue
            count = len(data.get('types', {}))
            total_types += count
            print(f"  {category}: {count} types")

        print("-" * 50)
        print(f"  Total mapped types: {total_types}")
        print(f"  Unknown types logged: {len(self.unknown_types['types'])}")

        if self.unknown_types['types']:
            print("\n  Top unknown types:")
            sorted_unknown = sorted(
                self.unknown_types['types'].items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )
            for qid, info in sorted_unknown[:10]:
                print(f"    {qid}: {info['label']} (seen {info['count']}x)")

    def finalize(self):
        """종료 시 로그 저장."""
        self._save_unknown_log()


# 전역 인스턴스
_classifier = None


def get_classifier() -> EventTypeClassifier:
    """싱글톤 분류기 반환."""
    global _classifier
    if _classifier is None:
        _classifier = EventTypeClassifier()
    return _classifier


def classify_event_type(qid: str, label: str = None) -> Tuple[str, str]:
    """간편 함수: QID를 분류."""
    return get_classifier().classify(qid, label)


if __name__ == '__main__':
    # 테스트
    classifier = EventTypeClassifier()

    test_qids = [
        ('Q178561', 'battle'),
        ('Q198', 'war'),
        ('Q131569', 'treaty'),
        ('Q164950', 'dynasty'),
        ('Q16510064', 'sporting event'),  # 제외
        ('Q9999999', 'unknown type'),  # 알 수 없음
    ]

    print("Testing Event Type Classifier")
    print("=" * 60)

    for qid, expected_label in test_qids:
        category, nature = classifier.classify(qid, expected_label)
        print(f"  {qid} ({expected_label}): category={category}, nature={nature}")

    classifier.print_stats()
    classifier.finalize()
