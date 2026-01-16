"""
finplot PyQt6 임베딩 테스트 스크립트

이 스크립트는 finplot을 PyQt6 위젯에 임베딩하는 다양한 방법을 테스트합니다.
"""
import os
os.environ['QT_API'] = 'pyqt6'

import sys
import pandas as pd
import numpy as np
from datetime import datetime

# PyQt6 먼저 import
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton

# finplot import
import finplot as fplt

# 테스트 데이터 생성
def create_sample_data(n=100):
    """샘플 OHLCV 데이터 생성"""
    dates = pd.date_range(end=datetime.now(), periods=n, freq='1D')
    np.random.seed(42)
    
    price = 100
    data = []
    for date in dates:
        open_price = price
        close_price = price + np.random.uniform(-2, 2)
        high_price = max(open_price, close_price) + np.random.uniform(0, 1)
        low_price = min(open_price, close_price) - np.random.uniform(0, 1)
        volume = np.random.randint(100000, 500000)
        
        data.append({
            'Date': date,
            'Open': open_price,
            'High': high_price,
            'Low': low_price,
            'Close': close_price,
            'Volume': volume
        })
        price = close_price
    
    df = pd.DataFrame(data)
    df = df.set_index('Date')
    return df


class TestWindow(QMainWindow):
    """finplot 임베딩 테스트 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Finplot Embedding Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # 중앙 위젯
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # 버튼
        btn = QPushButton("Refresh Data")
        btn.clicked.connect(self.load_data)
        layout.addWidget(btn)
        
        # ═══════════════════════════════════════════════════════════════════
        # 방법 1: create_plot_widget 사용
        # ═══════════════════════════════════════════════════════════════════
        # 이 위젯에 axs 속성이 필요함 (finplot 요구사항)
        central.axs = []
        
        # finplot 차트 생성
        self.axes = fplt.create_plot_widget(master=central, rows=2, init_zoom_periods=50)
        self.ax = self.axes[0]
        self.ax_vol = self.axes[1]
        
        # 데이터 로드
        self.load_data()
        
        # fplt.show()를 qt_exec=False로 호출 (우리가 이벤트 루프 관리)
        fplt.show(qt_exec=False)
    
    def load_data(self):
        """차트에 데이터 로드"""
        df = create_sample_data()
        
        # 캔들스틱 플롯
        fplt.candlestick_ochl(df[['Open', 'Close', 'High', 'Low']], ax=self.ax)
        
        # 볼륨 플롯
        fplt.volume_ocv(df[['Open', 'Close', 'Volume']], ax=self.ax_vol)
        
        # 새로고침
        fplt.refresh()
        print("Data loaded successfully!")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # finplot 테마 설정
    fplt.background = '#1a1a2e'
    fplt.foreground = '#e0e0e0'
    fplt.candle_bull_color = '#22c55e'
    fplt.candle_bear_color = '#ef4444'
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())
