import sys
import ctypes
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt

def apply_glass(hwnd):
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    DWMWA_SYSTEMBACKDROP_TYPE = 38
    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    
    # 1. Dark mode
    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(1)), 4)
    # 2. Mica Alt (4) or Acrylic (3)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(ctypes.c_int(4)), 4)
    # 3. Round corners
    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(ctypes.c_int(2)), 4)
    # 4. Remove 1px border
    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(ctypes.c_int(0xFFFFFFFE)), 4)

app = QApplication(sys.argv)
w = QWidget()
w.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
w.resize(360, 200)

layout = QVBoxLayout(w)
layout.setContentsMargins(0,0,0,0)

bg = QFrame()
bg.setStyleSheet("""
    QFrame {
        background-color: rgba(15, 15, 15, 80);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 0px; 
    }
""")
layout.addWidget(bg)

inner = QVBoxLayout(bg)
inner.addWidget(QLabel("<h2 style='color:white'>Native Windows 11 Glass</h2>"))

w.show()
apply_glass(int(w.winId()))

from PyQt6.QtCore import QTimer
QTimer.singleShot(4000, app.quit)
app.exec()
