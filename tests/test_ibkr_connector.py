# ============================================================================
# IBKRConnector 단위 테스트
# ============================================================================
# 📌 테스트 범위 (IB Gateway 연결 없이 실행 가능):
#   - 설정 로드 테스트
#   - Signal 정의 확인
#   - 상태 플래그 초기화 확인
#
# 📌 실행:
#   pytest tests/test_ibkr_connector.py -v
# ============================================================================

"""
IBKRConnector Unit Tests

IB Gateway 연결 없이 기본 동작을 검증하는 Mock 기반 테스트입니다.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

# 테스트 대상
from backend.broker.ibkr_connector import IBKRConnector


# ═══════════════════════════════════════════════════════════════════════════
# 설정 로드 테스트
# ═══════════════════════════════════════════════════════════════════════════

class TestIBKRConnectorInit:
    """IBKRConnector 초기화 테스트"""
    
    def test_default_config_values(self):
        """
        기본 설정값 테스트
        
        .env 파일이 없거나 환경 변수가 설정되지 않았을 때
        기본값이 올바르게 적용되는지 확인합니다.
        """
        # 환경 변수 없이 테스트
        with patch.dict(os.environ, {}, clear=True):
            connector = IBKRConnector()
            
            assert connector.host == "127.0.0.1"
            assert connector.port == 4002
            assert connector.client_id == 1
            assert connector.account == ""
    
    def test_custom_config_from_env(self):
        """
        환경 변수에서 설정 로드 테스트
        
        .env 또는 시스템 환경 변수에서 설정을 올바르게 로드하는지 확인합니다.
        """
        custom_env = {
            "IB_HOST": "192.168.1.100",
            "IB_PORT": "7497",
            "IB_CLIENT_ID": "42",
            "IB_ACCOUNT": "DU123456",
        }
        
        with patch.dict(os.environ, custom_env, clear=True):
            connector = IBKRConnector()
            
            assert connector.host == "192.168.1.100"
            assert connector.port == 7497
            assert connector.client_id == 42
            assert connector.account == "DU123456"
    
    def test_initial_state_flags(self):
        """
        초기 상태 플래그 테스트
        
        생성 직후에는 연결되지 않은 상태여야 합니다.
        """
        connector = IBKRConnector()
        
        assert connector._is_running == False
        assert connector._is_connected == False
        assert connector.is_connected() == False
        assert connector.get_ib() is None


# ═══════════════════════════════════════════════════════════════════════════
# Signal 정의 테스트
# ═══════════════════════════════════════════════════════════════════════════

class TestIBKRConnectorSignals:
    """PyQt Signals 정의 테스트"""
    
    def test_signals_defined(self):
        """
        모든 필수 시그널이 정의되어 있는지 확인
        """
        connector = IBKRConnector()
        
        # 시그널 존재 확인
        assert hasattr(connector, 'connected')
        assert hasattr(connector, 'price_update')
        assert hasattr(connector, 'account_update')
        assert hasattr(connector, 'error')
        assert hasattr(connector, 'log_message')
    
    def test_signal_emission(self, qtbot):
        """
        시그널 발생 테스트 (실제 emit 확인)
        
        Note: 이 테스트는 pytest-qt가 필요합니다.
              pip install pytest-qt
        """
        connector = IBKRConnector()
        
        # log_message 시그널 캡처 준비
        with qtbot.waitSignal(connector.log_message, timeout=1000) as blocker:
            connector.log_message.emit("테스트 메시지")
        
        assert blocker.args == ["테스트 메시지"]


# ═══════════════════════════════════════════════════════════════════════════
# 구독 관리 테스트
# ═══════════════════════════════════════════════════════════════════════════

class TestIBKRConnectorSubscription:
    """시세 구독 관리 테스트"""
    
    def test_subscribe_without_connection(self):
        """
        연결 없이 구독 시도 시 에러 처리 확인
        """
        connector = IBKRConnector()
        
        # 연결 안 된 상태에서 구독 시도
        connector.subscribe_ticker(["SPY"])
        
        # 구독되지 않아야 함
        assert len(connector._subscribed_tickers) == 0
    
    def test_unsubscribe_nonexistent(self):
        """
        존재하지 않는 구독 해제 시 에러 없이 처리
        """
        connector = IBKRConnector()
        
        # 에러 없이 통과해야 함
        connector.unsubscribe_ticker("NONEXISTENT")
        connector.unsubscribe_all()


# ═══════════════════════════════════════════════════════════════════════════
# 연결 로직 테스트 (Mock)
# ═══════════════════════════════════════════════════════════════════════════

class TestIBKRConnectorConnection:
    """연결 로직 테스트 (IB 객체 Mock)"""
    
    def test_stop_before_start(self):
        """
        시작 전 stop() 호출 시 안전하게 처리
        """
        connector = IBKRConnector()
        
        # 에러 없이 통과해야 함
        connector.stop()
        
        assert connector._is_running == False


# ═══════════════════════════════════════════════════════════════════════════
# 실행
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
