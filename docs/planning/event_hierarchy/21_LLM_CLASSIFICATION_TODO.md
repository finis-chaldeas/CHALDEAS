# LLM 분류 실행 TODO

## 현황 (2026-01-28)

| 상태 | 개수 | 설명 |
|------|------|------|
| pending | ~5,000+ | Period 매칭으로 분류됨 (0.7 신뢰도) |
| none | ~65 | 최상위 이벤트 확정 |
| confirmed | ~10 | 수동 확인됨 |
| unknown | ~41,000 | **LLM 분류 필요** |

## LLM 분류가 필요한 경우

1. **Wikidata P361 없음**: 이벤트에 wikidata_id가 없거나 P361 관계가 없음
2. **Period 매칭 실패**:
   - 위치 정보 없음
   - 정의된 Period 범위 밖
   - 글로벌 이벤트 (특정 지역 아님)

## 실행 명령어

```bash
# LLM 분류 활성화 (비용 발생!)
cd C:\Projects\Chaldeas
python poc/scripts/hierarchy/unified_classifier.py --limit 1000 --create-parents

# dry-run으로 먼저 테스트
python poc/scripts/hierarchy/unified_classifier.py --limit 100 --dry-run
```

## 예상 비용

- 모델: `gpt-5.1-chat-latest`
- 이벤트당 토큰: ~500 input + ~200 output = ~700 토큰
- 41,000 이벤트 × 700 토큰 = ~29M 토큰
- 예상 비용: ~$290 (gpt-5.1 기준 $0.01/1K tokens)

## 비용 절감 방안

1. **배치 처리**: 중요도 높은 이벤트부터 (importance DESC)
2. **Period 확장**: 더 많은 지역/시대 정의 추가
3. **Wikidata 보강**: wikipedia_url에서 wikidata_id 추출

## 다음 단계

1. [ ] Period 정의 확장 (아시아, 아프리카, 아메리카)
2. [ ] Wikidata ID 보강 스크립트
3. [ ] LLM 분류 실행 (배치별)
4. [ ] 분류 결과 검토 및 수동 확인
