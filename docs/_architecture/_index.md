# 📂 Sigma9 전체 디렉토리 구조 인덱스

> **Version**: 1.0  
> **Created**: 2026-01-16  
> **Purpose**: 문서화 진행 상황 추적용 전체 파일 체크리스트

---

## 📊 진행 상황 요약

| 영역 | 파일 수 (실제) | 완료 | 진행률 |
|------|---------------|------|--------|
| **backend/** | 98 | 98 | 100% |
| **frontend/** | 36 | 36 | 100% |
| **scripts/** | 10 | 10 | 100% |
| **tests/** | 15 | 15 | 100% |
| **.agent/** | 8 | 8 | 100% |
| **Root Files** | 8 | 8 | 100% |

**총 파일 수: 175개**

---

## Phase 1: Backend Layer (98 files) ✅

```
backend/
├── [x] __init__.py
├── [x] __main__.py
├── [x] server.py                 # FastAPI 메인 서버
├── [x] container.py              # DI Container
│
├── core/                         # 핵심 비즈니스 로직 (27 files) ✅
│   ├── [x] __init__.py
│   ├── interfaces/               # 추상 인터페이스 (2 files) ✅
│   │   ├── [x] __init__.py
│   │   └── [x] scoring.py
│   ├── [x] audit_logger.py       # 감사 로깅
│   ├── [x] backtest_engine.py    # 백테스트 엔진
│   ├── [x] backtest_report.py    # 백테스트 리포트
│   ├── [x] config_loader.py      # 설정 로더
│   ├── [x] deduplicator.py       # 중복 제거
│   ├── [x] divergence_detector.py # 다이버전스 감지
│   ├── [x] double_tap.py         # 재진입 로직
│   ├── [x] event_sequencer.py    # 이벤트 시퀀서
│   ├── [x] ignition_monitor.py   # 점화 모니터
│   ├── [x] mock_data.py          # 목 데이터
│   ├── [x] order_manager.py      # 주문 관리
│   ├── [x] realtime_scanner.py   # 실시간 스캐너
│   ├── [x] risk_manager.py       # 리스크 관리
│   ├── [x] scanner.py            # 스캐너
│   ├── [x] scheduler.py          # 스케줄러
│   ├── [x] strategy_base.py      # 전략 베이스 클래스
│   ├── [x] strategy_loader.py    # 전략 로더
│   ├── [x] subscription_manager.py # 구독 관리
│   ├── [x] technical_analysis.py # 기술적 분석
│   ├── [x] tick_broadcaster.py   # 틱 브로드캐스터
│   ├── [x] tick_dispatcher.py    # 틱 디스패처
│   ├── [x] ticker_filter.py      # 티커 필터
│   ├── [x] trading_context.py    # 트레이딩 컨텍스트
│   ├── [x] trailing_stop.py      # 트레일링 스탑
│   └── [x] zscore_calculator.py  # Z-Score 계산기
│
├── api/                          # REST/WebSocket API ✅
│   ├── [x] __init__.py
│   ├── [x] websocket.py          # WebSocket 핸들러
│   └── routes/                   # REST 라우트 (15 files) ✅
│       ├── [x] __init__.py
│       ├── [x] chart.py
│       ├── [x] common.py
│       ├── [x] control.py
│       ├── [x] ignition.py
│       ├── [x] llm.py
│       ├── [x] models.py
│       ├── [x] position.py
│       ├── [x] scanner.py
│       ├── [x] status.py
│       ├── [x] strategy.py
│       ├── [x] sync.py
│       ├── [x] tier2.py
│       ├── [x] watchlist.py
│       └── [x] zscore.py
│
├── models/                       # 데이터 모델 (8 files) ✅
│   ├── [x] __init__.py
│   ├── [x] backtest.py
│   ├── [x] order.py
│   ├── [x] risk.py
│   ├── [x] technical.py
│   ├── [x] tick.py
│   ├── [x] ticker_info.py
│   └── [x] watchlist.py
│
├── strategies/                   # 전략 플러그인 (15 files)
│   ├── [x] __init__.py
│   ├── [x] _template.py          # 전략 템플릿
│   ├── [x] score_v3_config.py    # Score V3 설정
│   ├── Rheograph/                # Rheograph 전략 (빈 폴더)
│   └── seismograph/              # Seismograph 전략
│       ├── [x] __init__.py
│       ├── [x] strategy.py       # 메인 전략
│       ├── scoring/              # 점수 계산 모듈 (4 files) ✅
│       │   ├── [x] __init__.py
│       │   ├── [x] v1.py         # Score V1
│       │   ├── [x] v2.py         # Score V2
│       │   └── [x] v3.py         # Score V3 (Pinpoint)
│       └── signals/              # 시그널 모듈 (6 files) ✅
│           ├── [x] __init__.py
│           ├── [x] base.py       # 시그널 베이스
│           ├── [x] accumulation_bar.py  # 매집 바
│           ├── [x] obv_divergence.py    # OBV 다이버전스
│           ├── [x] tight_range.py       # VCP 타이트 레인지
│           └── [x] volume_dryout.py     # 볼륨 드라이아웃
│
├── broker/                       # 브로커 연동 ✅
│   ├── [x] __init__.py
│   └── [x] ibkr_connector.py     # IBKR 연동
│
├── startup/                      # 서버 시작 모듈 ✅
│   ├── [x] __init__.py
│   ├── [x] config.py
│   ├── [x] database.py
│   ├── [x] realtime.py
│   └── [x] shutdown.py
│
├── llm/                          # LLM 관련 ✅
│   ├── [x] __init__.py
│   └── [x] oracle.py
│
├── config/                       # 설정 (3 files)
│   ├── [ ] server_config.yaml    # 서버 설정
│   ├── [ ] settings.yaml         # 일반 설정
│   └── [ ] ticker_exclusions.yaml # 티커 제외 목록
│
├── data/                         # 데이터 관련 (12 files)
│   ├── [x] __init__.py
│   ├── [x] data_repository.py    # 통합 데이터 접근 레이어
│   ├── [x] database.py           # MarketDB (SQLite)
│   ├── [x] flush_policy.py       # 플러시 정책
│   ├── [x] massive_client.py     # Massive REST 클라이언트
│   ├── [x] massive_loader.py     # Massive 데이터 로더
│   ├── [x] massive_ws_client.py  # Massive WebSocket 클라이언트
│   ├── [x] parquet_manager.py    # Parquet I/O 관리자
│   ├── [x] symbol_mapper.py      # 심볼 매핑 (Massive ↔ IBKR)
│   ├── [x] ticker_info_service.py # 티커 정보 서비스
│   ├── [x] validators.py         # 데이터 검증
│   └── [x] watchlist_store.py    # Watchlist JSON 저장소
│
└── scripts/                      # 백엔드 스크립트 (7 files)
    ├── [x] check_tickers.py      # 티커 체크
    ├── [x] diagnose_chart.py     # 차트 진단
    ├── [x] migrate_intraday_structure.py # 인트라데이 구조 마이그레이션
    ├── [x] migrate_to_parquet.py # Parquet 마이그레이션
    ├── [x] procure_intraday_data.py # 인트라데이 데이터 수집
    ├── [x] repair_parquet_data.py # Parquet 데이터 복구
    └── [x] validate_parquet_quality.py # Parquet 품질 검증
```

---

## Phase 2: Frontend Layer (36 files)

```
frontend/
├── [x] __main__.py
├── [x] main.py                   # PyQt6 진입점
│
├── gui/                          # GUI 컴포넌트
│   ├── [x] __init__.py
│   ├── [x] dashboard.py          # 메인 대시보드 (99KB!)
│   ├── [x] chart_widget.py       # 차트 위젯
│   ├── [x] control_panel.py      # 컨트롤 패널
│   ├── [x] custom_window.py      # 커스텀 윈도우
│   ├── [x] particle_effects.py   # 파티클 효과
│   ├── [x] settings_dialog.py    # 설정 다이얼로그
│   ├── [x] theme.py              # 테마 설정
│   ├── [x] ticker_info_window.py # 티커 정보 윈도우
│   ├── [x] watchlist_model.py    # 워치리스트 모델
│   ├── [x] window_effects.py     # 윈도우 효과
│   │
│   ├── panels/                   # UI 패널
│   │   ├── [x] __init__.py
│   │   ├── [x] chart_panel.py
│   │   ├── [x] log_panel.py
│   │   ├── [x] oracle_panel.py
│   │   ├── [x] position_panel.py
│   │   ├── [x] resample_panel.py
│   │   ├── [x] tier2_panel.py
│   │   └── [x] watchlist_panel.py
│   │
│   ├── chart/                    # 차트 모듈 (5 files)
│   │   ├── [x] __init__.py
│   │   ├── [x] chart_data_manager.py
│   │   └── [x] finplot_chart.py
│   │   └── _legacy/              # 레거시 차트 (2 files)
│   │       ├── [x] candlestick_item.py
│   │       └── [x] pyqtgraph_chart.py
│   │
│   ├── state/                    # 상태 관리
│   │   ├── [x] __init__.py
│   │   └── [x] dashboard_state.py
│   │
│   ├── widgets/                  # 재사용 위젯
│   │   ├── [x] __init__.py
│   │   ├── [x] ticker_search_bar.py
│   │   └── [x] time_display_widget.py
│   │
│   └── assets/                   # 에셋 파일 (제외)
│
├── services/                     # 서비스 레이어 ✅
│   ├── [x] __init__.py
│   ├── [x] backend_client.py     # 백엔드 클라이언트
│   ├── [x] chart_data_service.py # 차트 데이터 서비스
│   ├── [x] ibkr_adapter.py       # IBKR 이벤트 어댑터 [02-003]
│   ├── [x] rest_adapter.py       # REST 어댑터
│   └── [x] ws_adapter.py         # WebSocket 어댑터
│
├── config/                       # 프론트엔드 설정 (1 py + 2 yaml)
│   ├── [x] loader.py             # 설정 로더
│   ├── [x] client_config.yaml
│   └── [x] settings.yaml
│
└── client/                       # 클라이언트 유틸리티 (1 file)
    └── [x] __init__.py
```

---

## Phase 3: Scripts & Tests (25 files)

```
scripts/                          # 루트 레벨 스크립트 (10 files)
├── [x] analyze_daygainers.py
├── [x] build_control_group.py
├── [x] build_d1_features.py
├── [x] build_features_brute_force.py
├── [x] build_m_n_features.py
├── [x] check_minute_coverage.py
├── [x] download_target_minutes.py
├── [x] eda_features.py
├── [x] train_xgboost.py
└── demos/                        # 데모 스크립트 (1 file)
    └── [x] ticker_info_demo.py

tests/                            # 테스트 스위트 (15 files)
├── [x] __init__.py
├── [x] test_backtest.py
├── [x] test_data_integrity.py
├── [x] test_database.py
├── [x] test_double_tap.py
├── [x] test_finplot_embed.py
├── [x] test_ibkr_connector.py
├── [x] test_massive_loader.py
├── [x] test_order_manager.py
├── [x] test_parquet_manager.py
├── [x] test_risk_manager.py
├── [x] test_score_v2.py
├── [x] test_score_v3.py
├── [x] test_strategies.py
└── [x] test_time_sync.py
```

---

## Phase 4: Configuration & Root Files

```
Sigma9-0.1/
├── [x] @PROJECT_DNA.md           # 프로젝트 DNA
├── [x] .gitignore
├── [x] .env                      # 환경 변수
├── [x] .env.example              # 환경 변수 예시
├── [x] pytest.ini                # Pytest 설정
├── [x] requirements.txt          # 의존성
├── [x] massive_rest_spec.json    # Massive API REST 스펙
├── [x] massive_websocket_spec.json # Massive WebSocket 스펙
│
├── .agent/                       # 에이전트 설정 (8 files)
│   └── workflows/                # 워크플로우 (8 files)
│       ├── [x] IMP-execution.md
│       ├── [x] IMP-planning.md
│       ├── [x] IMP-verification.md
│       ├── [x] Theme-policy.md
│       ├── [x] refactoring-execution.md
│       ├── [x] refactoring-planning.md
│       ├── [x] refactoring-pr.md
│       └── [x] refactoring-verification.md
│
└── docs/                         # 문서 (폴더 구조만)
    ├── _architecture/            # 파일별 문서화 결과물 (164 files)
    ├── Plan/                     # 구현 계획서 (날짜별 정리: 26-01-13/, 등)
    │   └── backtest/             # 백테스트 관련 계획
    ├── devlog/                   # 개발 로그 (날짜별 정리: 26-01-13/, 등)
    ├── context/                  # 참조 자료
    │   ├── references/           # 외부 API, 연구 문서, 레거시 코드 (47 files)
    │   └── strategy/             # 전략 관련 문서 (25 files)
    ├── archive/                  # 아카이브
    ├── diagrams/                 # 다이어그램
    └── references/               # 추가 참조 자료
```

---

## 관련 문서

- [📋 문서화 계획서](./plan.md) - 프로젝트 목표, 문서화 깊이, 실행 단계
