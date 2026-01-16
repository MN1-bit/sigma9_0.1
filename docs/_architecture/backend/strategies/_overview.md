# Backend Strategies Overview

> 📍 **Location**: `backend/strategies/`  
> **Role**: 전략 플러그인 - 런타임 로드 가능한 트레이딩 전략

---

## 구조

```
strategies/
├── __init__.py
├── _template.py          # 전략 템플릿
├── score_v3_config.py    # Score V3 설정
└── seismograph/          # Seismograph 전략
    ├── __init__.py
    ├── strategy.py       # 메인 전략
    ├── scoring/          # 점수 계산 모듈
    └── signals/          # 시그널 모듈
```

---

## 파일 목록

| 파일 | 역할 |
|------|------|
| [_template.py](./_template.md) | 전략 템플릿 |
| [score_v3_config.py](./score_v3_config.md) | Score V3 설정 |

### Seismograph 전략

| 파일 | 역할 |
|------|------|
| [seismograph/strategy.py](./seismograph/strategy.md) | 메인 전략 |
| seismograph/scoring/ | 점수 계산 모듈 (TBD) |
| seismograph/signals/ | 시그널 모듈 (TBD) |
