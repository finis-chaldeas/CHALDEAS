"""
로컬 덤프 리더 - Wikidata 덤프 파일에서 데이터 읽기

처리 로직 없음. 순수 데이터 읽기만.
"""

import bz2
import json
import os
from typing import Generator, Dict, Any, Optional, Set
from dataclasses import dataclass


DUMP_PATH = "C:/Projects/Chaldeas/data/wikidata/latest-all.json.bz2"


@dataclass
class DumpStats:
    """덤프 파일 통계"""
    file_size_gb: float
    exists: bool


class LocalDumpReader:
    """로컬 Wikidata 덤프 리더"""

    def __init__(self, dump_path: str = DUMP_PATH):
        self.dump_path = dump_path

    def get_stats(self) -> DumpStats:
        """덤프 파일 상태 확인"""
        exists = os.path.exists(self.dump_path)
        size_gb = 0

        if exists:
            size_gb = os.path.getsize(self.dump_path) / (1024 ** 3)

        return DumpStats(file_size_gb=size_gb, exists=exists)

    def stream_all(self) -> Generator[Dict[str, Any], None, None]:
        """모든 엔티티 스트리밍"""
        if not os.path.exists(self.dump_path):
            raise FileNotFoundError(f"Dump not found: {self.dump_path}")

        with bz2.open(self.dump_path, 'rt', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                if line in ('[', ']', ''):
                    continue

                if line.endswith(','):
                    line = line[:-1]

                try:
                    entity = json.loads(line)
                    yield entity
                except json.JSONDecodeError:
                    continue

    def find_by_qids(self, target_qids: Set[str]) -> Generator[Dict[str, Any], None, None]:
        """특정 QID들만 찾기"""
        remaining = set(target_qids)

        for entity in self.stream_all():
            qid = entity.get('id', '')

            if qid in remaining:
                yield entity
                remaining.discard(qid)

                if not remaining:
                    break

    def find_by_types(self, type_qids: Set[str], limit: int = None) -> Generator[Dict[str, Any], None, None]:
        """특정 타입(P31)의 엔티티들 찾기"""
        count = 0

        for entity in self.stream_all():
            # P31 (instance of) 확인
            claims = entity.get('claims', {}).get('P31', [])

            for claim in claims:
                mainsnak = claim.get('mainsnak', {})
                datavalue = mainsnak.get('datavalue', {})

                if datavalue.get('type') == 'wikibase-entityid':
                    instance_qid = datavalue.get('value', {}).get('id')

                    if instance_qid in type_qids:
                        yield entity
                        count += 1

                        if limit and count >= limit:
                            return

                        break  # 이 엔티티는 이미 yield 함
