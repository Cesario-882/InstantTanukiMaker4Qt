# Copyright (C) 2026 Cesario-882
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
