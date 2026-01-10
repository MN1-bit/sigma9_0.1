# 05-004: Frontend/Backend 책임 분리 Devlog

> **작성일**: 2026-01-08 16:15  
> **상태**: ✅ 완료

---

## 1. 변경 요약

Tier 2 승격 조건 판단 로직을 Frontend에서 Backend로 이동:
- **비즈니스 로직 분리**: 4가지 승격 조건 판단이 Backend API에서 수행
- **Frontend 간소화**: `_check_tier2_promotion` 52줄 → 40줄 (-12줄)

---

## 2. 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/api/routes/models.py` | `Tier2CheckRequest` 모델 추가 (+14줄) |
| `backend/api/routes/tier2.py` | `POST /tier2/check-promotion` 엔드포인트 추가 (+71줄) |
| `frontend/services/backend_client.py` | `check_tier2_promotion_sync` 메서드 추가 (+53줄) |
| `frontend/gui/dashboard.py` | `_check_tier2_promotion` Backend API 호출로 교체 (-12줄) |

---

## 3. 구현 세부사항

### 3.1 Backend API (`/api/tier2/check-promotion`)

4가지 승격 조건을 서버에서 판단:
1. **Ignition Score ≥ 70** + Anti-Trap 필터 통과
2. **Stage ≥ 4** (VCP Breakout Imminent)
3. **zenV ≥ 2.0 && zenP < 0.5** (Accumulation Divergence)
4. **Acc Score ≥ 80** + realtime_gainer 소스

### 3.2 Frontend 호출 패턴

```python
resp = self.backend_client.check_tier2_promotion_sync(
    ticker=ticker,
    ignition_score=ignition_score,
    passed_filter=passed_filter,
    stage_number=...,
    acc_score=...,
    source=...,
    zenV=zenV,
    zenP=zenP,
)
return resp.get("should_promote", False), resp.get("reason", "")
```

---

## 4. 검증 결과

- [x] `ruff check` 통과
- [x] 코드 구조 일관성 유지
- [ ] 수동 테스트 (Backend 실행 후 Tier 2 승격 동작 확인 필요)

---

## 5. 후속 작업

- `chart_data_service.py` DB 직접 접근 → 현행 유지 (사용자 결정)
- `_create_right_panel` 분리 → 별도 계획서 필요
