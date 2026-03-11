# 07. 모바일 경험 복구

## 문제

`MobileLayout.tsx`가 존재하지만 `App.tsx`에서 **비활성화** 상태. 현재 모바일 접속 시 데스크톱 레이아웃이 그대로 나온다.

## 현재 상태

### 존재하는 모바일 컴포넌트

| 컴포넌트 | 위치 | 상태 |
|----------|------|------|
| `MobileLayout.tsx` | `components/mobile/` | 구현됨, 미사용 |
| `HeroCardDeck.tsx` | `components/mobile/` | 구현됨, MobileLayout에서 사용 |
| `useIsMobile` hook | `App.tsx` export | 구현됨 (breakpoint: 768px) |

### MobileLayout 구조

```
┌──────────────────┐
│    2D Map (50%)   │  ← Leaflet MapView (현재 비활성)
├──────────────────┤
│   Feed (50%)      │  ← ViewportFeed, HeroCardDeck
├──────────────────┤
│ Map Feed Srch Arc │  ← 5-tab 하단 바
└──────────────────┘
```

**비활성화 이유**: Leaflet 2D MapView가 제거됨 ("no proper support yet").
MobileLayout이 2D 맵에 의존하고 있어 같이 비활성화.

### CSS 반응형 현황

- `@media (max-width: 768px)`: 41개 CSS 파일에 존재
- 개별 패널/컴포넌트는 모바일 대응 CSS가 일부 있음
- 하지만 레이아웃 자체가 데스크톱 전용

### 핵심 이슈

1. **MobileLayout이 2D 맵 의존**: 3D 글로브로 교체 필요
2. **글로브 터치 조작**: react-globe.gl는 터치 지원하지만, 시프트 패널/타임라인과의 상호작용이 좁은 화면에서 문제
3. **패널 겹침**: 데스크톱에서 왼쪽 패널 + 오른쪽 패널이 모바일에서 겹침

## 접근 방식 선택지

### 방법 A: MobileLayout 3D 글로브 교체 (중간 난이도)

MobileLayout에서 2D Leaflet → 3D Globe로 교체:

```
┌──────────────────┐
│  3D Globe (50%)   │  ← GlobeContainer (touch enabled)
├──────────────────┤
│  Content (50%)    │  ← ShiftPanel / Feed / Portal
├──────────────────┤
│ Globe Shift Portal│  ← 3-tab 하단 바
└──────────────────┘
```

- 장점: 기존 MobileLayout 재활용
- 단점: 글로브가 화면 반만 차지 → 시각 임팩트 감소

### 방법 B: 풀스크린 글로브 + 오버레이 (권장)

모바일에서도 글로브를 풀스크린으로 유지하고, 패널을 바텀시트로:

```
┌──────────────────┐
│                   │
│   3D Globe (전체)  │
│                   │
├──────────────────┤  ← 스와이프 업 바텀시트
│  Shift / Feed     │
│  (드래그 가능)     │
├──────────────────┤
│ Globe Shift Portal│  ← 3-tab 하단 바
└──────────────────┘
```

- 장점: 글로브 임팩트 유지, 데스크톱과 일관된 경험
- 단점: 바텀시트 UI 새로 구현 필요

### 방법 C: 모바일 최소 지원 (최소 난이도)

MobileLayout 없이, 데스크톱 레이아웃의 CSS만 조정:
- 패널 width: 100%로
- 한 번에 하나의 패널만 표시
- 글로브는 백그라운드

- 장점: 가장 빠름, 레이아웃 코드 변경 없음
- 단점: UX 최적화 아님

## 권장: 방법 C (단기) → 방법 B (중기)

공개 시점에는 C로 최소 동작을 보장하고, 이후 B로 전환.

### 방법 C 구현

```tsx
// App.tsx
const isMobile = useIsMobile()

// 모바일: 패널을 풀스크린 오버레이로
// 데스크톱: 기존 사이드 패널
<div className={isMobile ? 'mobile-panel-overlay' : 'desktop-panel'}>
  {activePanel === 'shift' && <ShiftPanel />}
  {activePanel === 'portal' && <TrismegistosPortal />}
</div>

// 모바일: 하단 네비게이션 바
{isMobile && <MobileTabBar />}
```

## 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/App.tsx` | `useIsMobile` 분기 + 모바일 패널 레이아웃 |
| `frontend/src/components/mobile/MobileTabBar.tsx` | **신규** — 3-tab 하단 바 |
| `frontend/src/styles/globals.css` | 모바일 패널 오버레이 스타일 |
| 기존 CSS 파일들 | 패널 width/position 조정 |

## 소요

| 방법 | 시간 |
|------|------|
| C (CSS 조정) | 반나절 |
| B (바텀시트) | 1-2일 |
| A (MobileLayout 교체) | 1일 |

## 검증

- Chrome DevTools → 모바일 뷰포트 (iPhone 14, Galaxy S23)
- 글로브 터치 조작 확인
- 시프트 패널 열기/닫기
- 타임라인 조작
- 포탈 브라우징
