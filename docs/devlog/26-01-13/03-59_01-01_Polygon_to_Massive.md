# 01-01: Polygon → Massive 리네이밍

> **날짜**: 2026-01-07  
> **Branch**: `refactor/polygon-to-massive`  
> **Commit**: `dc69539`

---

## 📋 개요

프로젝트 전체에서 "Polygon" (이전 API 제공업체명)을 "Massive"로 일괄 변경하는 리팩터링 작업을 수행했습니다.

### 작업 범위
- 파일명 변경: 3개
- 클래스/변수명 변경: 10+ 항목
- 설정 파일 수정: 2개
- Python 소스 파일 수정: 12개

---

## 🔍 사전 분석

### API 엔드포인트 검증
- `api.massive.com` 접속 확인 (401 = 인증 필요 → 정상)
- 환경변수 `MASSIVE_API_KEY`는 이미 코드 전체에서 사용 중

### 발견된 불일치
| 위치 | 기존 값 | 문제 |
|------|--------|------|
| `polygon_client.py:93` | `api.massive.com` | ✅ 이미 변경됨 |
| `config_loader.py:71` | `api.polygon.io` | ❌ 불일치 |
| `ignition_monitor.py:322` | `api.polygon.io` | ❌ 하드코딩 |
| `server_config.yaml` | `api.polygon.io` | ❌ 불일치 |

---

## 📁 파일명 변경

| 변경 전 | 변경 후 |
|--------|--------|
| `backend/data/polygon_client.py` | `backend/data/massive_client.py` |
| `backend/data/polygon_loader.py` | `backend/data/massive_loader.py` |
| `tests/test_polygon_loader.py` | `tests/test_massive_loader.py` |

---

## 🏷️ 클래스/상수명 변경

| 카테고리 | 변경 전 | 변경 후 |
|----------|--------|--------|
| 클래스 | `PolygonClient` | `MassiveClient` |
| 클래스 | `PolygonLoader` | `MassiveLoader` |
| 예외 | `PolygonAPIError` | `MassiveAPIError` |
| 예외 | `PolygonRateLimitError` | `MassiveRateLimitError` |
| 설정 | `PolygonConfig` | `MassiveConfig` |
| 상수 | `POLYGON_TO_IBKR_MANUAL` | `MASSIVE_TO_IBKR_MANUAL` |
| 상수 | `IBKR_TO_POLYGON_MANUAL` | `IBKR_TO_MASSIVE_MANUAL` |
| 메서드 | `polygon_to_ibkr()` | `massive_to_ibkr()` |
| 메서드 | `ibkr_to_polygon()` | `ibkr_to_massive()` |
| 변수 | `polygon_client` | `massive_client` |
| 변수 | `polygon_symbol` | `massive_symbol` |

---

## ⚙️ 설정 파일 변경

### `backend/config/server_config.yaml`
```diff
-polygon:
-  base_url: "https://api.polygon.io"
+massive:
+  base_url: "https://api.massive.com"
```

### `backend/config/settings.yaml`
```diff
-polygon:
-  base_url: "https://api.polygon.io"
+massive:
+  base_url: "https://api.massive.com"
```

---

## 📝 수정된 Python 파일

1. `backend/data/massive_client.py` (renamed)
2. `backend/data/massive_loader.py` (renamed)
3. `backend/data/__init__.py`
4. `backend/data/symbol_mapper.py`
5. `backend/data/massive_ws_client.py`
6. `backend/data/database.py`
7. `backend/server.py`
8. `backend/core/config_loader.py`
9. `backend/core/ignition_monitor.py`
10. `backend/core/scheduler.py`
11. `backend/core/scanner.py`
12. `backend/core/realtime_scanner.py`
13. `backend/api/routes.py`
14. `tests/test_massive_loader.py` (renamed)
15. `tests/test_database.py`

---

## ✅ 검증 결과

```bash
# 구문 검사
python -m py_compile backend/data/massive_client.py  ✅
python -m py_compile backend/data/massive_loader.py  ✅
python -m py_compile backend/server.py               ✅

# Import 검증
python -c "from backend.data import MassiveClient, MassiveLoader"  ✅
python -c "from backend.data.massive_client import MassiveAPIError"  ✅

# 잔여 참조 확인
grep -r "PolygonClient" backend/  # 0 results ✅
```

---

## 🚀 Git 커밋 정보

```
Branch: refactor/polygon-to-massive
Commit: dc69539

Message:
  refactor: rename Polygon to Massive across codebase
  
  - Renamed polygon_client.py -> massive_client.py
  - Renamed polygon_loader.py -> massive_loader.py
  - Updated all class names: PolygonClient -> MassiveClient, etc.
  - Updated YAML configs to use massive: section
  - Updated API URLs to api.massive.com
```

---

## ⏭️ 후속 작업 (선택사항)

1. **문서 치환**: `docs/` 폴더 내 50+ 마크다운 파일에 "Polygon" 참조 남아있음
2. **PR/Merge**: `refactor/polygon-to-massive` 브랜치를 main에 병합
3. **환경변수 확인**: 실행 환경에 `MASSIVE_API_KEY`가 설정되어 있는지 확인

---

## 📊 작업 통계

| 항목 | 수량 |
|------|------|
| 파일명 변경 | 3개 |
| 클래스/메서드 리네이밍 | 11개 항목 |
| Python 파일 수정 | 15개 |
| YAML 파일 수정 | 2개 |
| 총 소요 시간 | ~20분 |

---

## 🔧 추가 수정 (2026-01-08)

> **시간**: 00:26 KST

### 발견된 문제
백엔드 실행 시 다음 오류 발생:
```
AttributeError: 'ServerConfig' object has no attribute 'massive'
```

### 원인
`config_loader.py`에서 `ServerConfig` 클래스의 속성명이 아직 `polygon`으로 남아있었음:
- **YAML 키**: `massive` (이미 변경됨)
- **Python 속성**: `polygon` (미변경)
- **로더**: `massive` 키로 접근 시도 → 속성 불일치 에러

### 수정 내역
```diff
# backend/core/config_loader.py (Line 153)
-    polygon: MassiveConfig = field(default_factory=MassiveConfig)
+    massive: MassiveConfig = field(default_factory=MassiveConfig)
```

### 검증
```bash
python -m backend  # ✅ 정상 시작
```

