# Parquet 폴더 구조 복원 및 품질 검증 계획서 (11-003A Rev.2)

> **작성일**: 2026-01-14 08:30
> **우선순위**: 11 (Data Layer) | **예상 소요**: 4-5h | **위험도**: 중간
> **상태**: 📋 검토 대기

---

## 1. 목표

### 1.1 Intraday 폴더 구조 복원
**현재 평탄화(Flat) 구조를 타임프레임별 폴더 구조로 복원**

| 항목 | 현재 상태 | 목표 상태 |
|------|----------|----------|
| 경로 | `intraday/AAPL_1m.parquet` | `1m/AAPL.parquet` |
| 폴더 | 단일 `intraday/` | 타임프레임별 `1m/`, `5m/`, `15m/`, `1h/` |

### 1.2 Daily 폴더 구조 복원
| 항목 | 현재 상태 | 목표 상태 |
|------|----------|----------|
| 경로 | `daily/all_daily.parquet` (383MB 통합) | `daily/{ticker}.parquet` (티커별 분리) |

### 1.3 목표 폴더 구조
```
data/parquet/
├── daily/                    # ← 티커별 분리
│   ├── AAPL.parquet
│   ├── TSLA.parquet
│   └── ...
├── 1m/                       # ← 새 구조
│   ├── AAPL.parquet
│   ├── TSLA.parquet
│   └── ...
├── 5m/
│   └── ...
├── 15m/
│   └── ...
├── 1h/
│   └── ...
├── indicators/               # (변경 없음)
└── scores/                   # (변경 없음)
```

---

## 2. 레이어 체크

- [x] 레이어 규칙 위반 없음 (backend.data 내부 변경)
- [x] 순환 의존성 없음
- [x] DI Container 등록 필요: **아니오** (ParquetManager 이미 등록됨)

---

## 3. 영향 범위 분석

### 3.1 코드 변경

| 파일 | 유형 | 변경 내용 |
|------|------|----------|
| `backend/data/parquet_manager.py` | MODIFY | `__init__`, `_get_intraday_path`, `get_intraday_tickers`, `get_stats`, `delete_ticker_intraday`, Daily 관련 메서드 |
| `tests/test_parquet_manager.py` | MODIFY | 경로 테스트 업데이트 |
| `backend/scripts/migrate_parquet_structure.py` | NEW | 마이그레이션 스크립트 |
| `backend/scripts/validate_parquet_quality.py` | NEW | 품질 검사 스크립트 |

### 3.2 데이터 마이그레이션

| 현재 | 목표 | 규모 |
|------|------|------|
| `intraday/AAPL_1m.parquet` | `1m/AAPL.parquet` | ~수천 개 |
| `intraday/AAPL_1h.parquet` | `1h/AAPL.parquet` | ~수천 개 |
| `daily/all_daily.parquet` (383MB) | `daily/AAPL.parquet` 등 | ~15,000+ 티커 |

---

## 4. 실행 단계

### Step 1: ParquetManager 코드 수정 (1.5h)

#### 4.1.1 `__init__` 변경 (Intraday)
```python
# 현재
self.intraday_dir = self.base_dir / "intraday"
self.intraday_dir.mkdir(parents=True, exist_ok=True)

# 목표
self.tf_dirs = {
    "1m": self.base_dir / "1m",
    "3m": self.base_dir / "3m",
    "5m": self.base_dir / "5m",
    "15m": self.base_dir / "15m",
    "1h": self.base_dir / "1h",
    "4h": self.base_dir / "4h",
}
for tf_dir in self.tf_dirs.values():
    tf_dir.mkdir(parents=True, exist_ok=True)
```

#### 4.1.2 `_get_intraday_path` 변경
```python
# 현재
def _get_intraday_path(self, ticker: str, timeframe: str) -> Path:
    return self.intraday_dir / f"{ticker}_{timeframe}.parquet"

# 목표
def _get_intraday_path(self, ticker: str, timeframe: str) -> Path:
    tf_dir = self.tf_dirs.get(timeframe, self.base_dir / timeframe)
    tf_dir.mkdir(parents=True, exist_ok=True)  # 동적 생성 지원
    return tf_dir / f"{ticker}.parquet"
```

#### 4.1.3 Daily 관련 메서드 변경
```python
# 현재: 단일 파일
self.daily_file = self.daily_dir / "all_daily.parquet"

# 목표: 티커별 파일
def _get_daily_path(self, ticker: str) -> Path:
    return self.daily_dir / f"{ticker}.parquet"

def read_daily(self, ticker: str, days: int = None):
    path = self._get_daily_path(ticker)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    # 날짜 필터링 로직...
```

---

### Step 2: 데이터 마이그레이션 스크립트 (1h)

`backend/scripts/migrate_parquet_structure.py`:
```python
"""
Parquet 폴더 구조 마이그레이션

Intraday: data/parquet/intraday/AAPL_1m.parquet → data/parquet/1m/AAPL.parquet
Daily: data/parquet/daily/all_daily.parquet → data/parquet/daily/AAPL.parquet (티커별)

실행: python -m backend.scripts.migrate_parquet_structure
"""
import shutil
from pathlib import Path
import pandas as pd

def migrate_intraday():
    """Intraday 파일 마이그레이션"""
    base = Path("data/parquet")
    intraday_dir = base / "intraday"
    
    if not intraday_dir.exists():
        print("❌ intraday/ 폴더가 없습니다")
        return 0
    
    migrated = 0
    for old_file in intraday_dir.glob("*.parquet"):
        # AAPL_1m.parquet → ticker=AAPL, tf=1m
        parts = old_file.stem.rsplit("_", 1)
        if len(parts) != 2:
            print(f"⚠️ 스킵: {old_file.name} (형식 불일치)")
            continue
        
        ticker, tf = parts
        new_dir = base / tf
        new_dir.mkdir(parents=True, exist_ok=True)
        
        new_file = new_dir / f"{ticker}.parquet"
        shutil.move(str(old_file), str(new_file))
        migrated += 1
        
    print(f"✅ Intraday 마이그레이션 완료: {migrated} 파일")
    
    if not any(intraday_dir.iterdir()):
        intraday_dir.rmdir()
        print("🗑️ 빈 intraday/ 폴더 삭제됨")
    
    return migrated

def migrate_daily():
    """Daily 통합 파일 → 티커별 분리"""
    base = Path("data/parquet")
    daily_dir = base / "daily"
    all_daily = daily_dir / "all_daily.parquet"
    
    if not all_daily.exists():
        print("❌ all_daily.parquet 파일이 없습니다")
        return 0
    
    df = pd.read_parquet(all_daily)
    tickers = df["ticker"].unique()
    migrated = 0
    
    for ticker in tickers:
        ticker_df = df[df["ticker"] == ticker].copy()
        ticker_df = ticker_df.sort_values("date")
        out_path = daily_dir / f"{ticker}.parquet"
        ticker_df.to_parquet(out_path, engine="pyarrow", compression="snappy")
        migrated += 1
        if migrated % 1000 == 0:
            print(f"  진행 중: {migrated}/{len(tickers)}")
    
    print(f"✅ Daily 마이그레이션 완료: {migrated} 파일")
    
    # 원본 백업 후 보관 (안전)
    backup_path = daily_dir / "all_daily.parquet.backup"
    shutil.move(str(all_daily), str(backup_path))
    print(f"📦 원본 백업: {backup_path}")
    
    return migrated

if __name__ == "__main__":
    print("=" * 50)
    print("Parquet 폴더 구조 마이그레이션 시작")
    print("=" * 50)
    migrate_intraday()
    migrate_daily()
    print("=" * 50)
    print("마이그레이션 완료!")
```

---

### Step 3: 데이터 품질 검사 스크립트 (1h)

`backend/scripts/validate_parquet_quality.py`:
```python
"""
Parquet 데이터 품질 검사

검사 항목:
1. 파일 무결성 (읽기 가능 여부)
2. 필수 컬럼 존재 여부
3. 데이터 범위 (날짜, 가격)
4. 중복 레코드 검사
5. NULL 값 비율

실행: python -m backend.scripts.validate_parquet_quality
"""
from pathlib import Path
import pandas as pd
from collections import defaultdict

DAILY_REQUIRED_COLS = ["ticker", "date", "open", "high", "low", "close", "volume"]
INTRADAY_REQUIRED_COLS = ["timestamp", "open", "high", "low", "close", "volume"]

def validate_daily(daily_dir: Path) -> dict:
    """Daily Parquet 품질 검사"""
    results = {"files": 0, "valid": 0, "errors": []}
    
    for f in daily_dir.glob("*.parquet"):
        if f.name == "all_daily.parquet.backup":
            continue
        results["files"] += 1
        
        try:
            df = pd.read_parquet(f)
            
            # 필수 컬럼 검사
            missing = set(DAILY_REQUIRED_COLS) - set(df.columns)
            if missing:
                results["errors"].append(f"{f.name}: 누락 컬럼 {missing}")
                continue
            
            # 데이터 존재 검사
            if len(df) == 0:
                results["errors"].append(f"{f.name}: 빈 파일")
                continue
            
            # 중복 검사
            dups = df.duplicated(subset=["date"]).sum()
            if dups > 0:
                results["errors"].append(f"{f.name}: 중복 {dups}건")
            
            results["valid"] += 1
            
        except Exception as e:
            results["errors"].append(f"{f.name}: 읽기 실패 - {e}")
    
    return results

def validate_intraday(base_dir: Path) -> dict:
    """Intraday Parquet 품질 검사"""
    results = {"files": 0, "valid": 0, "errors": [], "by_tf": defaultdict(int)}
    
    for tf in ["1m", "5m", "15m", "1h", "4h"]:
        tf_dir = base_dir / tf
        if not tf_dir.exists():
            continue
        
        for f in tf_dir.glob("*.parquet"):
            results["files"] += 1
            results["by_tf"][tf] += 1
            
            try:
                df = pd.read_parquet(f)
                
                # 필수 컬럼 검사
                missing = set(INTRADAY_REQUIRED_COLS) - set(df.columns)
                if missing:
                    results["errors"].append(f"{tf}/{f.name}: 누락 컬럼 {missing}")
                    continue
                
                if len(df) == 0:
                    results["errors"].append(f"{tf}/{f.name}: 빈 파일")
                    continue
                
                results["valid"] += 1
                
            except Exception as e:
                results["errors"].append(f"{tf}/{f.name}: 읽기 실패 - {e}")
    
    return results

def main():
    base = Path("data/parquet")
    
    print("=" * 60)
    print("Parquet 데이터 품질 검사")
    print("=" * 60)
    
    # Daily 검사
    print("\n📊 Daily 데이터 검사:")
    daily_results = validate_daily(base / "daily")
    print(f"  파일 수: {daily_results['files']}")
    print(f"  정상: {daily_results['valid']}")
    print(f"  오류: {len(daily_results['errors'])}")
    if daily_results["errors"][:5]:
        for e in daily_results["errors"][:5]:
            print(f"    ⚠️ {e}")
    
    # Intraday 검사
    print("\n📊 Intraday 데이터 검사:")
    intraday_results = validate_intraday(base)
    print(f"  파일 수: {intraday_results['files']}")
    print(f"  정상: {intraday_results['valid']}")
    print(f"  타임프레임별: {dict(intraday_results['by_tf'])}")
    print(f"  오류: {len(intraday_results['errors'])}")
    if intraday_results["errors"][:5]:
        for e in intraday_results["errors"][:5]:
            print(f"    ⚠️ {e}")
    
    print("\n" + "=" * 60)
    
    # 최종 판정
    total_errors = len(daily_results["errors"]) + len(intraday_results["errors"])
    if total_errors == 0:
        print("✅ 모든 데이터 품질 검사 통과!")
    else:
        print(f"⚠️ 총 {total_errors}건의 오류 발견")
    
    return total_errors

if __name__ == "__main__":
    exit(main())
```

---

### Step 4: 테스트 수정 (0.5h)

`tests/test_parquet_manager.py` 업데이트:
```python
# 경로 테스트 수정
def test_intraday_path():
    pm = ParquetManager()
    path = pm._get_intraday_path("AAPL", "1m")
    assert path.name == "AAPL.parquet"
    assert path.parent.name == "1m"

def test_daily_path():
    pm = ParquetManager()
    path = pm._get_daily_path("AAPL")
    assert path.name == "AAPL.parquet"
    assert path.parent.name == "daily"
```

---

## 5. 검증 계획

### 5.1 자동화 테스트
```powershell
# 기존 테스트 실행
pytest tests/test_parquet_manager.py -v

# ruff 린트
ruff check backend/data/parquet_manager.py
ruff check backend/scripts/migrate_parquet_structure.py
ruff check backend/scripts/validate_parquet_quality.py
```

### 5.2 마이그레이션 검증
```powershell
# 마이그레이션 전 파일 수 확인
(Get-ChildItem data\parquet\intraday\*.parquet).Count
(Get-ChildItem data\parquet\daily\*.parquet).Count

# 마이그레이션 실행
python -m backend.scripts.migrate_parquet_structure

# 마이그레이션 후 확인
(Get-ChildItem data\parquet\1m\*.parquet).Count
(Get-ChildItem data\parquet\1h\*.parquet).Count
(Get-ChildItem data\parquet\daily\*.parquet).Count  # 티커 수
```

### 5.3 품질 검사
```powershell
# 품질 검사 실행
python -m backend.scripts.validate_parquet_quality
```

### 5.4 수동 검증 (GUI)
1. Frontend 실행 후 차트 로딩 정상 동작 확인
2. 스캐너 실행

---

## 6. 롤백 계획

```powershell
# Git으로 코드 롤백
git checkout HEAD -- backend/data/parquet_manager.py

# 데이터 역마이그레이션: all_daily.parquet.backup 복원
Move-Item data\parquet\daily\all_daily.parquet.backup data\parquet\daily\all_daily.parquet

# intraday 역마이그레이션은 역스크립트 필요 시 제공
```

---

## 7. 실행 시작 전 체크리스트

- [ ] 사용자 승인
- [ ] 현재 데이터 백업 확인 (마이그레이션 스크립트가 자동 백업)
- [ ] `/IMP-execution` 워크플로우 따라 실행

---

> [!WARNING]
> **Daily 분리 시 주의사항**
> 현재 `all_daily.parquet`는 383MB로 통합되어 있으며, 티커별 분리 시 약 15,000개의 파일이 생성됩니다.
> `read_daily_bulk()` 메서드도 새 구조에 맞게 수정이 필요합니다.
