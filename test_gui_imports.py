
print("Testing PyQt6 Imports...")
try:
    from PyQt6.QtWidgets import QWidget, QToolButton, QLabel, QHBoxLayout, QPushButton, QComboBox, QSlider, QAbstractButton, QLineEdit
    print("PyQt6 Imports SUCCESS")
except ImportError as e:
    print(f"PyQt6 Import FAILED: {e}")

try:
    import sys
    sys.path.append('.')
    import frontend.gui.custom_window
    print("custom_window import SUCCESS")
except Exception as e:
    print(f"custom_window import FAILED: {e}")
