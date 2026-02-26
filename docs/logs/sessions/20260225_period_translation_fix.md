# 세션 로그: 2025-02-25 (번역 수정)

## 세션 정보
- **목적**: period_narratives 한국어 번역 실행 (이전 세션에서 시작했으나 실패)

## 발견한 문제
- 이전 세션에서 97/97 번역 완료로 보고했으나, DB에는 모두 빈 문자열로 저장됨
- **근본 원인**: `gpt-5-mini`는 reasoning 모델이라 `max_completion_tokens`에 reasoning 토큰이 포함됨
  - `max_completion_tokens=200` → 200개 전부 reasoning에 사용, 출력 0개 → 빈 문자열
  - `finish_reason: length` (토큰 부족으로 잘린 것)
- headline은 ~400 reasoning + ~25 output = ~425 토큰 필요
- narrative는 ~1000 reasoning + ~500 output = ~1500 토큰 필요

## 수정 사항
1. `translate_period_narratives.py` 수정:
   - headline: `max_completion_tokens=200` → `2000`
   - narrative: `max_completion_tokens=2000` → `8000`
   - `--global-only`, `--regional-only` 플래그 추가 (이전엔 global만)
   - region 정보도 SELECT에 포함
2. DB에서 빈 문자열 136개 → NULL로 리셋
3. 전체 391개 번역 재실행 (background task beb08d1)

## 결과
- 번역 품질 검증 완료 (자연스러운 한국어 역사 용어 사용)
- 처리 속도: ~1.7개/분 (reasoning 토큰 오버헤드)
- 예상 완료: ~4시간 (391개)
- 비용: ~$0.50-1.00

## 반성
- reasoning 모델의 토큰 구조를 사전에 파악했어야 함
- `finish_reason`을 체크하는 로직이 스크립트에 없어서 빈 문자열이 그대로 저장됨

## 다음 작업
- 번역 완료 후 WorldBriefing에서 한국어 표시 확인
- History Shift 플랜 Step 1-4 (백엔드) 진행
