# Verify Skill

백엔드와 프론트엔드 코드 검증을 한 번에 실행합니다.

## 실행 순서

1. **Backend 검증**
   ```bash
   cd backend
   python -m pytest tests/ -v --tb=short 2>&1 | head -50
   ```

2. **Frontend 검증**
   ```bash
   cd frontend
   npm run lint 2>&1 | head -30
   npx tsc --noEmit 2>&1 | head -30
   ```

3. **결과 요약**
   - 각 단계 성공/실패 표시
   - 실패 시 주요 에러 내용 포함

## 출력 형식

```
## 검증 결과

| 항목 | 상태 |
|------|------|
| Backend Tests | ✅/❌ |
| Frontend Lint | ✅/❌ |
| TypeScript | ✅/❌ |

### 실패 항목 상세
(있을 경우만)
```
