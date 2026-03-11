# 06. 온보딩 + 투어 진입점

## 문제

1. 랜딩이 버튼 2개짜리 한 화면뿐. "이게 뭔데?" → 이탈.
2. 투어 시스템이 18개 에피소드까지 구현되어 있는데 **진입점이 없다**. 유저가 접근 불가.
3. 시프트(핵심 기능)가 랜딩에서 전혀 소개되지 않음.

## 현재 상태

### 랜딩 (FeaturedPersons.tsx)

- 투명 오버레이 (backdrop blur) + "C H A L D E A S" 타이틀
- 2개 카드: **Explore** (글로브 비행) / **Read Stories** (포탈 열기)
- Explore → 그리스로 비행 (37.97, 23.72), year=-480
- Read Stories → TRISMEGISTOS 포탈
- `localStorage 'chaldeas-explored'`로 최초 1회만 표시
- 시프트 소개 없음, 조작법 안내 없음

### 투어 시스템 (TourOverlay.tsx)

- 구현 완료: 18개 에피소드 (`shebaEpisodes.ts`)
- Netflix 스타일 UI: 하단 스토리 카드 + 프로그레스바 + 자동 글로브 이동
- 키보드: 화살표/스페이스 = 다음, ESC = 닫기
- 에피소드 목록:
  - 테르모필레 (480 BCE, 4 steps)
  - 알렉산더 동방원정 (334-323 BCE, 5 steps)
  - 메소포타미아 여명 (3500-2000 BCE)
  - 카이사르와 로마
  - 트로이 전쟁
  - 잔 다르크, 대항해시대, 십자군, 네로, 이집트 피라미드
  - 몽골 제국, 아서왕, 전국시대, 르네상스
  - 프랑스 혁명, 바이킹, 페르시아 제국, 인도 서사시
- **문제**: App.tsx에서 TourOverlay를 렌더링하는 코드 없음 → 유저 접근 불가

### 모드바 (ModeBar.tsx)

- 상단 네비게이션 바: Globe / Shift / Portal 모드 전환
- 투어 진입 버튼 없음

## 구현 계획

### 1. 투어 진입점 추가

**가장 빠른 방법**: ModeBar 또는 랜딩에 투어 버튼 추가.

#### 방법 A: 랜딩에 3번째 카드 추가

```
[Explore]  [Read Stories]  [Guided Tour]
 글로브 탐험    포탈 읽기       가이드 투어
```

- "Guided Tour" 클릭 → TourOverlay 열기 (첫 번째 에피소드)
- 기존 2-card → 3-card 레이아웃

#### 방법 B: ModeBar에 투어 아이콘

```
[Globe] [Shift] [Portal] [🎬 Tour]
```

- 항상 접근 가능
- 클릭 → 에피소드 선택 메뉴 or 바로 첫 에피소드

#### 권장: A + B 모두

랜딩에서 첫인상 + ModeBar에서 상시 접근.

### 2. 랜딩 개선

현재 랜딩이 너무 단순. 아래 정보 추가:

```
C H A L D E A S
"Experience history like time travel"

[Explore]           [Guided Tour]        [Read Stories]
 지구본을 돌려       역사를 따라가며       큐레이션된 역사
 시간을 움직여       글로브가 자동 이동    매거진처럼 읽기

── 조작 안내 ──
🖱️ 드래그: 글로브 회전
⏱️ 타임라인: 시간 이동
🔍 줌: 지역 탐색
```

핵심: **3초 안에 "아 이걸 이렇게 쓰는 거구나"** 전달.

### 3. 최초 사용 3-step 투어 (선택)

`TourOverlay` 활용하여 "조작법 투어" 에피소드 1개 추가:

```
Step 1: "글로브를 드래그해보세요" (인터랙티브)
Step 2: "타임라인을 움직여보세요" (자동 → 사용자 액션 대기)
Step 3: "마커를 클릭하면 이야기가 시작됩니다" (자동 → 클릭 유도)
```

단, 기존 `TourOverlay`는 자동 진행 방식이라 인터랙티브 투어와 맞지 않을 수 있음.
최소한 기존 에피소드 진입점만 열어주는 것이 현실적.

## 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/App.tsx` | TourOverlay 렌더링 + 상태 관리 |
| `frontend/src/components/landing/FeaturedPersons.tsx` | 3번째 카드(투어) 추가 + 조작 안내 |
| `frontend/src/components/navigation/ModeBar.tsx` | 투어 버튼 추가 |
| `frontend/src/store/` | tourStore or globeStore에 투어 상태 추가 (선택) |

## 소요

- 투어 진입점만: 2-3시간
- 랜딩 개선 포함: 반나절
- 인터랙티브 최초 투어: 추가 반나절
