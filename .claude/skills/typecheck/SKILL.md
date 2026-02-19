# TypeScript Type Check Skill

TypeScript 컴파일러 검사를 실행하고 에러를 우선순위대로 수정합니다.

## 실행 순서

1. `cd frontend && npx tsc --noEmit` 실행하여 모든 에러 확인
2. 에러를 우선순위대로 분류:
   - **P1**: 타입 에러 (Type 'X' is not assignable to type 'Y')
   - **P2**: 미사용 변수/import (is declared but never used)
   - **P3**: 스타일 이슈
3. P1 → P2 → P3 순서로 수정
4. 수정 후 `npx tsc --noEmit`으로 검증
5. 모든 에러 해결될 때까지 반복
6. 변경 사항 요약 출력

## 출력 형식

```
## TypeScript 검사 결과

### 발견된 에러
- P1 (타입): N개
- P2 (미사용): N개
- P3 (스타일): N개

### 수정 완료
- [파일]: 변경 내용

### 검증
✅ 모든 에러 해결됨
```
