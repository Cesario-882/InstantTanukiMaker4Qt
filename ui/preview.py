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

"""预览面板：静态帧显示、GIF 播放、鼠标/键盘交互。"""

import threading
import numpy as np

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QPoint, Signal
from PySide6.QtGui import QMovie

import const
from config import CONFIG
import qtlib
from ui.base import HeaderPanel


class PreviewPanel(QWidget):
    DELAY_UPDATE = 10
    frame_loaded = Signal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.panel_header = HeaderPanel(self)
        self.sbmp_preview = QLabel()
        self.sbmp_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sbmp_preview.setStyleSheet("border: 1px solid gray;")
        self.sbmp_preview.setMinimumSize(*const.DEFAULT_SIZE)

        self.anime_preview = QLabel()
        self.anime_preview.hide()

        layout = QVBoxLayout(self)
        layout.addWidget(self.panel_header, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sbmp_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.anime_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        self.pos_start = QPoint(0, 0)
        self.is_dragging = False

        self.delay_update = QTimer()
        self.delay_update.setSingleShot(True)
        self.delay_update.timeout.connect(self.start_loading)

        self.movie = None
        self.current_task_id = 0
        self.frame_loaded.connect(self.show_frame)

        self.sbmp_preview.mousePressEvent = self.on_left
        self.sbmp_preview.mouseDoubleClickEvent = self.on_left
        self.sbmp_preview.mouseReleaseEvent = self.on_up
        self.sbmp_preview.mouseMoveEvent = self.on_motion
        self.sbmp_preview.setMouseTracking(True)
        self.sbmp_preview.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.sbmp_preview.keyPressEvent = self.on_press
        self.sbmp_preview.wheelEvent = self.on_wheel

    def update_display(self):
        self.delay_update.start(self.DELAY_UPDATE)
        self.panel_header.update_display()

    def start_loading(self):
        self.current_task_id += 1
        task_id = self.current_task_id
        threading.Thread(target=self.load_frame, args=(task_id,), daemon=True).start()

    def load_frame(self, task_id):
        if task_id != self.current_task_id: return
        image_preview = CONFIG.manager.get_preview()
        if task_id == self.current_task_id:
            self.frame_loaded.emit(image_preview)

    def stop_animation(self):
        if self.movie:
            self.movie.stop()
            self.movie = None
        self.anime_preview.hide()
        self.sbmp_preview.show()
        self.panel_header.panel_playing.set_playing(False)

    def show_frame(self, image_preview):
        if image_preview is None: return

        if self.movie and self.movie.state() == QMovie.MovieState.Running:
            self.stop_animation()

        pixmap = const.pil_to_qpixmap(image_preview)
        self.sbmp_preview.setPixmap(pixmap)
        self.sbmp_preview.setFixedSize(pixmap.size())
        self.sbmp_preview.show()
        self.anime_preview.hide()
        qtlib.post_layout(self.window())

    def show_animation(self):
        if self.movie:
            self.movie.stop()
            self.movie = None

        path_gif = const.PATH_GIF_PREVIEW
        if not path_gif.exists(): return

        self.movie = QMovie(str(path_gif))
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.anime_preview.setMovie(self.movie)

        self.sbmp_preview.hide()
        self.anime_preview.show()
        self.movie.start()
        self.panel_header.panel_playing.set_playing(True)

    def on_left(self, event):
        pos = event.position().toPoint()
        is_collide = CONFIG.manager.select_by_pos(np.array([pos.x(), pos.y()]), event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if is_collide:
            self.is_dragging = True
            self.pos_start = pos
        qtlib.post_update(self.window(), preview=True, prop=True)

    def on_motion(self, event):
        self.sbmp_preview.setFocus()
        if not self.is_dragging: return
        pos_cur = event.position().toPoint()
        offset = pos_cur - self.pos_start
        self.pos_start = pos_cur
        CONFIG.manager.add_offset(np.array([offset.x(), offset.y()]))
        qtlib.post_update(self.window(), preview=True, prop=True)

    def on_up(self, event): self.is_dragging = False

    def on_press(self, event):
        key = event.key()
        if key == Qt.Key.Key_Tab:
            ix_delta = -1 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            CONFIG.manager.shift_ix_frame(ix_delta)
            self.stop_animation()
            qtlib.post_update(self.window(), True, True, True)
            return
        elif key == Qt.Key.Key_Escape:
            CONFIG.manager.switch_marking()
            qtlib.post_update(self.window(), True, True, True)
            return

        if not CONFIG.manager.is_selected(): return

        direction = {
            Qt.Key.Key_Up: np.array((0, -1)), Qt.Key.Key_W: np.array((0, -1)),
            Qt.Key.Key_Down: np.array((0, 1)), Qt.Key.Key_S: np.array((0, 1)),
            Qt.Key.Key_Left: np.array((-1, 0)), Qt.Key.Key_A: np.array((-1, 0)),
            Qt.Key.Key_Right: np.array((1, 0)), Qt.Key.Key_D: np.array((1, 0)),
        }.get(key)
        if direction is None: return

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            direction = direction * 5
        CONFIG.manager.add_offset(direction)
        qtlib.post_update(self.window(), preview=True, prop=True)

    def on_wheel(self, event):
        if not CONFIG.manager.is_selected(): return
        delta = event.angleDelta().y()
        rate_angle = 10 if event.modifiers() & Qt.KeyboardModifier.ControlModifier else 1
        angle_delta = -1 if delta < 0 else 1
        CONFIG.manager.add_angle(angle_delta * rate_angle)
        qtlib.post_update(self.window(), preview=True, prop=True)

"""预览面板：静态帧显示、GIF 播放、鼠标/键盘交互。"""

import threading
import numpy as np

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QPoint, Signal
from PySide6.QtGui import QMovie

import const
from config import CONFIG
import qtlib
from ui.base import HeaderPanel


class PreviewPanel(QWidget):
    DELAY_UPDATE = 10
    frame_loaded = Signal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.panel_header = HeaderPanel(self)
        self.sbmp_preview = QLabel()
        self.sbmp_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sbmp_preview.setStyleSheet("border: 1px solid gray;")
        self.sbmp_preview.setMinimumSize(*const.DEFAULT_SIZE)

        self.anime_preview = QLabel()
        self.anime_preview.hide()

        layout = QVBoxLayout(self)
        layout.addWidget(self.panel_header, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sbmp_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.anime_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        self.pos_start = QPoint(0, 0)
        self.is_dragging = False

        self.delay_update = QTimer()
        self.delay_update.setSingleShot(True)
        self.delay_update.timeout.connect(self.start_loading)

        self.movie = None
        self.current_task_id = 0
        self.frame_loaded.connect(self.show_frame)

        self.sbmp_preview.mousePressEvent = self.on_left
        self.sbmp_preview.mouseDoubleClickEvent = self.on_left
        self.sbmp_preview.mouseReleaseEvent = self.on_up
        self.sbmp_preview.mouseMoveEvent = self.on_motion
        self.sbmp_preview.setMouseTracking(True)
        self.sbmp_preview.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.sbmp_preview.keyPressEvent = self.on_press
        self.sbmp_preview.wheelEvent = self.on_wheel

    def update_display(self):
        self.delay_update.start(self.DELAY_UPDATE)
        self.panel_header.update_display()

    def start_loading(self):
        self.current_task_id += 1
        task_id = self.current_task_id
        threading.Thread(target=self.load_frame, args=(task_id,), daemon=True).start()

    def load_frame(self, task_id):
        if task_id != self.current_task_id: return
        image_preview = CONFIG.manager.get_preview()
        if task_id == self.current_task_id:
            self.frame_loaded.emit(image_preview)

    def stop_animation(self):
        if self.movie:
            self.movie.stop()
            self.movie = None
        self.anime_preview.hide()
        self.sbmp_preview.show()
        self.panel_header.panel_playing.set_playing(False)

    def show_frame(self, image_preview):
        if image_preview is None: return

        if self.movie and self.movie.state() == QMovie.MovieState.Running:
            self.stop_animation()

        pixmap = const.pil_to_qpixmap(image_preview)
        self.sbmp_preview.setPixmap(pixmap)
        self.sbmp_preview.setFixedSize(pixmap.size())
        self.sbmp_preview.show()
        self.anime_preview.hide()
        qtlib.post_layout(self.window())

    def show_animation(self):
        if self.movie:
            self.movie.stop()
            self.movie = None

        path_gif = const.PATH_GIF_PREVIEW
        if not path_gif.exists(): return

        self.movie = QMovie(str(path_gif))
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.anime_preview.setMovie(self.movie)

        self.sbmp_preview.hide()
        self.anime_preview.show()
        self.movie.start()
        self.panel_header.panel_playing.set_playing(True)

    def on_left(self, event):
        pos = event.position().toPoint()
        is_collide = CONFIG.manager.select_by_pos(np.array([pos.x(), pos.y()]), event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if is_collide:
            self.is_dragging = True
            self.pos_start = pos
        qtlib.post_update(self.window(), preview=True, prop=True)

    def on_motion(self, event):
        self.sbmp_preview.setFocus()
        if not self.is_dragging: return
        pos_cur = event.position().toPoint()
        offset = pos_cur - self.pos_start
        self.pos_start = pos_cur
        CONFIG.manager.add_offset(np.array([offset.x(), offset.y()]))
        qtlib.post_update(self.window(), preview=True, prop=True)

    def on_up(self, event): self.is_dragging = False

    def on_press(self, event):
        key = event.key()
        if key == Qt.Key.Key_Tab:
            ix_delta = -1 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            CONFIG.manager.shift_ix_frame(ix_delta)
            self.stop_animation()
            qtlib.post_update(self.window(), True, True, True)
            return
        elif key == Qt.Key.Key_Escape:
            CONFIG.manager.switch_marking()
            qtlib.post_update(self.window(), True, True, True)
            return

        if not CONFIG.manager.is_selected(): return

        direction = {
            Qt.Key.Key_Up: np.array((0, -1)), Qt.Key.Key_W: np.array((0, -1)),
            Qt.Key.Key_Down: np.array((0, 1)), Qt.Key.Key_S: np.array((0, 1)),
            Qt.Key.Key_Left: np.array((-1, 0)), Qt.Key.Key_A: np.array((-1, 0)),
            Qt.Key.Key_Right: np.array((1, 0)), Qt.Key.Key_D: np.array((1, 0)),
        }.get(key)
        if direction is None: return

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            direction = direction * 5
        CONFIG.manager.add_offset(direction)
        qtlib.post_update(self.window(), preview=True, prop=True)

    def on_wheel(self, event):
        if not CONFIG.manager.is_selected(): return
        delta = event.angleDelta().y()
        rate_angle = 10 if event.modifiers() & Qt.KeyboardModifier.ControlModifier else 1
        angle_delta = -1 if delta < 0 else 1
        CONFIG.manager.add_angle(angle_delta * rate_angle)
        qtlib.post_update(self.window(), preview=True, prop=True)
