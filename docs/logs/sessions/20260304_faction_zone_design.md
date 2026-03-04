# Faction Zone Design (세력도/영역 색상)

## Status: 기획만 (코드 구현 아님)

## Concept

시프트 페이지에서 세력 영역을 반투명 폴리곤으로 글로브 위에 표시.
예: 초한전쟁에서 유방(빨강) vs 항우(파랑) 세력 범위를 지도에 오버레이.

## react-globe.gl Integration

`polygonsData` prop 활용:
```typescript
<Globe
  polygonsData={factionPolygons}
  polygonGeoJsonGeometry={d => d.geometry}
  polygonCapColor={d => d.color}
  polygonSideColor={() => 'rgba(0,0,0,0.1)'}
  polygonStrokeColor={() => '#fff'}
  polygonAltitude={0.01}
/>
```

## Data Structure

### Widget Type: `faction_zone`

```json
{
  "type": "faction_zone",
  "slot": "overlay",
  "data": {
    "zones": [
      {
        "name": "Han",
        "name_ko": "한",
        "color": "rgba(200, 50, 50, 0.25)",
        "center_lat": 34.5,
        "center_lng": 109.0,
        "radius_km": 300,
        "leader": "Liu Bang",
        "leader_ko": "유방"
      },
      {
        "name": "Chu",
        "name_ko": "초",
        "color": "rgba(50, 50, 200, 0.25)",
        "center_lat": 34.2,
        "center_lng": 117.0,
        "radius_km": 400,
        "leader": "Xiang Yu",
        "leader_ko": "항우"
      }
    ]
  }
}
```

## Polygon Generation

중심점 + 반경 → 원형 GeoJSON 폴리곤:
```typescript
function circlePolygon(lat: number, lng: number, radiusKm: number, points = 36) {
  const coords = []
  const R = 6371 // Earth radius km
  for (let i = 0; i <= points; i++) {
    const angle = (i / points) * 2 * Math.PI
    const dLat = (radiusKm / R) * Math.cos(angle) * (180 / Math.PI)
    const dLng = (radiusKm / R) * Math.sin(angle) * (180 / Math.PI) / Math.cos(lat * Math.PI / 180)
    coords.push([lng + dLng, lat + dLat])
  }
  return { type: 'Polygon', coordinates: [coords] }
}
```

## GPT Generation Compatibility

GPT가 생성 가능한 데이터:
- 세력명 + 색상 (진영별 고정 팔레트)
- 중심 좌표 (수도/거점)
- 대략적 반경 (km)
- 지도자명

복잡한 GeoJSON 경계는 GPT가 생성하기 어려움 → 원형 근사로 충분.

## Implementation Priority

1. **Phase 1** (현재): camera_altitude + highlight_locations ← 구현 완료
2. **Phase 2** (다음): faction_zone 위젯 등록 + GlobeContainer polygonsData 연동
3. **Phase 3** (나중): GPT 프롬프트에 faction_zone 힌트 추가, 자동 생성

## Considerations

- 폴리곤이 너무 많으면 성능 이슈 → 페이지당 최대 4-5개 세력
- 색상은 세력 고유 색상 지정 (붉은색=한, 파란색=초 등)
- 줌 레벨에 따라 opacity 조절 가능
- 페이지 전환 시 폴리곤도 애니메이션 전환
