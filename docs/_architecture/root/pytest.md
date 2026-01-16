# pytest.ini

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `pytest.ini` |
| **역할** | Pytest 설정 파일 |
| **라인 수** | 7 |

## 설정 옵션

| 옵션 | 값 | 설명 |
|------|---|------|
| `asyncio_mode` | `auto` | 비동기 테스트 자동 감지 |
| `asyncio_default_fixture_loop_scope` | `function` | 픽스처별 이벤트 루프 |
| `testpaths` | `tests` | 테스트 디렉터리 |
| `python_files` | `test_*.py` | 테스트 파일 패턴 |
| `python_functions` | `test_*` | 테스트 함수 패턴 |

## 실행 방법
```bash
pytest                # 전체 테스트
pytest -v             # 상세 출력
pytest tests/test_*.py  # 특정 패턴
```
