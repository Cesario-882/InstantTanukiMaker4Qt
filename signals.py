# signals.py
from PySide6.QtCore import QObject, Signal

class AppSignals(QObject):
    """应用程序全局信号"""
    update = Signal(dict)
    append = Signal(dict)
    select = Signal(dict)
    layout = Signal()
    info = Signal(dict)
    start_progress = Signal(dict)
    end_progress = Signal(dict)
    play = Signal()

# 全局信号实例
signals = AppSignals()
