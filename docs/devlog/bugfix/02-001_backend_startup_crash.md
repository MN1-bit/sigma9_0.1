# 02-001: Backend Startup Crash & Watchlist JSON Corruption Fix

**날짜**: 2026-01-08  
**유형**: Bugfix  
**상태**: ✅ 완료

---

## 📋 문제 요약

프론트엔드 GUI에서 "Connect" 버튼을 통해 백엔드를 자동 시작할 때:
1. **백엔드 터미널이 즉시 종료**됨 (크래시)
2. 수동 터미널 실행 시에는 정상 작동

---

## 🔍 원인 분석

### 문제 1: 백엔드 즉시 크래시

**증상**:
```
ModuleNotFoundError: No module named 'dependency_injector'
```

**원인**: 
- GUI가 `.venv` 환경의 Python을 명시적으로 호출
- `.venv`에 `dependency-injector` 패키지가 설치되어 있지 않음
- 수동 터미널에서는 다른 Python 환경(전역/conda 등)을 사용 중이었을 가능성

**해결**:
```bash
.venv\Scripts\pip.exe install dependency-injector
```

---

### 문제 2: Watchlist JSON 파일 손상

**증상**:
```
❌ Watchlist 로드 실패: Expecting value: line 24 column 20 (char 634)
```

JSON 파일이 `"can_trade": ` 이후로 잘린 채 저장됨.

**원인**:
- `_periodic_watchlist_broadcast()` (1초 폴링)
- `_handle_new_gainer()` (신규 종목 발견 시)

두 비동기 태스크가 **동시에 같은 파일**에 쓰기 시도 → **Race Condition**

**해결**: Queue 기반 전담 Writer 스레드 구현

---

## 🛠️ 구현 내용

### 1. subprocess 디버깅 개선

[dashboard.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/dashboard.py#L1165-L1171)

```python
# 기존: 크래시 시 창 즉시 닫힘
subprocess.Popen([venv_python, "-m", "backend"], ...)

# 수정: cmd /k로 창 유지 (에러 확인 가능)
subprocess.Popen(['cmd', '/k', venv_python, '-m', 'backend'], ...)
```

---

### 2. Queue 기반 WatchlistWriter

[watchlist_store.py](file:///d:/Codes/Sigma9-0.1/backend/data/watchlist_store.py#L55-L128)

```python
class WatchlistWriter:
    """전담 Watchlist 쓰기 스레드"""
    _instance = None  # 싱글톤
    
    def __init__(self):
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._thread.start()
    
    def enqueue(self, data, path, temp_path):
        """쓰기 작업을 큐에 추가"""
        self._queue.put((data, path, temp_path))
    
    def _writer_loop(self):
        """전담 쓰기 루프 - Atomic Write"""
        while self._running:
            data, path, temp_path = self._queue.get(timeout=0.1)
            
            # 1. 임시 파일에 완전히 쓰기
            with open(temp_path, "w") as f:
                json.dump(data, f, cls=NumpyEncoder)
                f.flush()
                os.fsync(f.fileno())
            
            # 2. 원자적 rename
            if path.exists():
                path.unlink()
            temp_path.rename(path)
```

**핵심 포인트**:
- 모든 쓰기가 단일 스레드에서 순차 처리 → Race Condition 제거
- Atomic Write (tmp → rename) → 부분 파일 방지
- `NumpyEncoder` → numpy 타입 자동 변환

---

### 3. NumpyEncoder 추가

```python
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        return super().default(obj)
```

---

## 📁 수정된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/gui/dashboard.py` | `cmd /k` 추가로 에러 디버깅 가능 |
| `backend/data/watchlist_store.py` | Queue 기반 Writer + NumpyEncoder |

---

## ✅ 검증 결과

1. GUI에서 Connect 클릭 → 백엔드 정상 시작
2. Watchlist JSON 저장 → 손상 없이 완전한 파일
3. 1초 폴링 + 신규 종목 발견 동시 발생 → 충돌 없음

---

## 📝 교훈

1. **venv 환경 확인**: 프로덕션 코드에서 사용하는 Python 환경에 모든 의존성이 설치되어 있는지 확인
2. **Race Condition 대응**: 공유 자원(파일)에 여러 스레드/태스크가 접근할 때는 Queue 기반 순차 처리 고려
3. **Atomic Write**: 파일 쓰기 시 tmp → rename 패턴으로 부분 파일 방지
