# ============================================================================
# Sigma9 Configuration Loader
# ============================================================================
import yaml
from functools import lru_cache
from pathlib import Path

# 설정 파일 경로 상수
CONFIG_DIR = Path(__file__).parent
SETTINGS_PATH = CONFIG_DIR / "settings.yaml"


@lru_cache()
def load_settings() -> dict:
    """
    settings.yaml 파일을 로드하여 딕셔너리로 반환합니다.
    (LRU Cache를 사용하여 반복적인 파일 I/O 방지)
    """
    if not SETTINGS_PATH.exists():
        # 파일이 없을 경우 기본값 반환 (혹은 예외 발생)
        return {}

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[ERROR] Failed to load settings.yaml: {e}")
        return {}


def get_setting(key_path: str, default=None):
    """
    점(.)으로 구분된 키 경로를 사용하여 설정값을 가져옵니다.
    예: get_setting("gui.theme", "dark")
    """
    data = load_settings()
    keys = key_path.split(".")

    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default

    return data


def save_settings(new_config: dict) -> bool:
    """
    설정을 settings.yaml 파일에 저장합니다.
    주의: 주석은 보존되지 않습니다.
    """
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            yaml.dump(
                new_config,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        load_settings.cache_clear()  # 캐시 초기화
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save settings.yaml: {e}")
        return False


def save_setting(key_path: str, value):
    """
    단일 설정값을 변경하고 저장합니다.
    예: save_setting("gui.theme", "light")
    """
    data = load_settings()
    if isinstance(data, dict):
        # Deep copy needed if we want to be safe, but simple dict is fine here
        current = data
        keys = key_path.split(".")

        # Nested dict navigation/creation
        for i, key in enumerate(keys[:-1]):
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value
        return save_settings(data)
    return False
