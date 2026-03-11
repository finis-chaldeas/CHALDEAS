# 01. React ErrorBoundary 추가

## 문제

현재 프론트엔드에 ErrorBoundary가 없다. API 에러, 렌더링 에러, undefined 접근 등 어떤 에러든 전체 앱이 흰 화면으로 크래시된다. 공개 서비스에서 치명적.

## 현재 상태

- **ErrorBoundary 컴포넌트**: 없음
- **Suspense fallback**: 있음 (GlobeLoader, PanelLoader 등 lazy 컴포넌트용)
- **에러 처리**: 개별 컴포넌트에서 try-catch 일부 있으나, 전역 catch 없음

## 구현 계획

### 1. 전역 ErrorBoundary 컴포넌트

**파일**: `frontend/src/components/common/ErrorBoundary.tsx`

```tsx
class ErrorBoundary extends React.Component<Props, State> {
  state = { hasError: false, error: null }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('CHALDEAS Error:', error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} onReset={this.handleReset} />
    }
    return this.props.children
  }
}
```

### 2. 폴백 UI

글로브 테마에 맞는 에러 화면:
- "Something went wrong" 메시지
- "Reload" 버튼 (페이지 새로고침)
- "Go Home" 버튼 (상태 초기화 후 랜딩)
- 에러 디테일 접기/펼치기 (개발자용)

### 3. 적용 위치

```tsx
// App.tsx — 최상위
<ErrorBoundary>
  <Suspense fallback={<GlobeLoader />}>
    <GlobeContainer />
  </Suspense>
  {/* ...나머지 UI */}
</ErrorBoundary>

// 개별 패널 (선택)
<ErrorBoundary fallback={<PanelError />}>
  <ShiftPanel />
</ErrorBoundary>
```

최소한 App 최상위에 1개. 가능하면 주요 패널(ShiftPanel, NarrativePanel, TrismegistosPortal)에도 각각.

## 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/components/common/ErrorBoundary.tsx` | **신규** |
| `frontend/src/App.tsx` | ErrorBoundary 래핑 |

## 소요

- 시간: 30분
- 비용: 없음
- 위험: 없음
