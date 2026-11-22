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

"""基础显示组件：图像容器、状态图标、顶部栏。"""

from pathlib import Path
from PIL import Image

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QObject, QRunnable, Slot
from PySide6.QtGui import QPixmap, QImage, QIcon

import const
from config import CONFIG
import editor
import qtlib
from i18n import _


# ===== 后台任务信号 =====
class ThumbnailSignals(QObject):
    finished = Signal(Path, QIcon, object)
    error = Signal(Path, str)


# ===== 后台任务执行体 =====
class ThumbnailWorker(QRunnable):
    def __init__(self, path_image, panel_instance, item_ref):
        super().__init__()
        self.path_image = path_image
        self.panel = panel_instance
        self.item_ref = item_ref
        self.signals = ThumbnailSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        try:
            cache_file = const.get_thumb_cache_path(self.path_image)
            icon = None

            if cache_file.exists():
                try:
                    with Image.open(cache_file) as im:
                        pil_img = im.convert("RGBA")
                        icon = QIcon(const.pil_to_qpixmap(pil_img))
                except Exception:
                    try: cache_file.unlink()
                    except: pass

            if not icon:
                pil_img = self.panel.get_thumb_image(self.path_image)
                if pil_img:
                    try: pil_img.save(cache_file, "PNG")
                    except Exception: pass
                    icon = QIcon(const.pil_to_qpixmap(pil_img))

            if icon:
                self.signals.finished.emit(self.path_image, icon, self.item_ref)
            else:
                self.signals.error.emit(self.path_image, "Failed to generate")
        except Exception as e:
            self.signals.error.emit(self.path_image, str(e))


# ===== 图像显示组件 =====
class BitmapPanel(QWidget):
    def __init__(self, parent=None, pil_image=None, path_file=None, qimage=None):
        super().__init__(parent)
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("border: none;")

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.current_pixmap = QPixmap()
        self.pil_image = None

        if qimage is not None:
            self.set_qimage(qimage)
        elif pil_image is not None:
            self.set_pil_image(pil_image)
        elif path_file is not None:
            self.load_file(path_file)
        else:
            empty = QPixmap(1, 1)
            empty.fill(Qt.GlobalColor.transparent)
            self.set_pixmap(empty)

    def set_pixmap(self, pixmap: QPixmap):
        if pixmap is None or pixmap.isNull():
            empty = QPixmap(1, 1)
            empty.fill(Qt.GlobalColor.transparent)
            self.current_pixmap = empty
        else:
            self.current_pixmap = pixmap
        self.label.setPixmap(self.current_pixmap)
        self.label.setFixedSize(self.current_pixmap.size())
        self.setMinimumSize(self.current_pixmap.size())

    def set_pil_image(self, pil_image):
        self.pil_image = pil_image
        if pil_image is None: return
        if isinstance(pil_image, QPixmap): self.set_pixmap(pil_image)
        elif isinstance(pil_image, QImage): self.set_pixmap(QPixmap.fromImage(pil_image))
        else: self.set_pixmap(const.pil_to_qpixmap(pil_image))

    def set_qimage(self, qimage):
        if qimage is None or qimage.isNull(): self.set_pixmap(QPixmap())
        else: self.set_pixmap(QPixmap.fromImage(qimage))

    def load_file(self, path_file: Path):
        try:
            pil_image = Image.open(path_file).convert("RGBA")
            self.set_pil_image(pil_image)
        except Exception:
            self.set_pixmap(QPixmap())

    def get_pixmap(self) -> QPixmap:
        return self.current_pixmap


class FocusDisplayPanel(BitmapPanel):
    def __init__(self, parent):
        super().__init__(parent)
        self.pil_focus_on = editor.open_image(const.PATH_FOCUS_ON).convert("RGBA")
        self.pil_focus_off = editor.open_image(const.PATH_FOCUS_OFF).convert("RGBA")
        self.set_pil_image(self.pil_focus_off)
        self.label.setToolTip(_("キー受付"))
        self.label.mousePressEvent = self.on_click

    def on_click(self, event):
        parent = self.parent()
        while parent:
            if hasattr(parent, 'sbmp_preview') and parent.sbmp_preview:
                parent.sbmp_preview.setFocus()
                break
            parent = parent.parent()

    def set_focus(self, is_focused):
        self.set_pil_image(self.pil_focus_on if is_focused else self.pil_focus_off)


class FrameNumberDisplayPanel(BitmapPanel):
    def __init__(self, parent):
        super().__init__(parent)
        self.im_display = editor.open_image(const.PATH_DISPLAY_NUM).convert("RGBA")
        self.label.setToolTip(_("現在フレーム"))
        self.label.mousePressEvent = self.on_click
        self.draw_number()

    def update_display(self):
        self.draw_number()

    def draw_number(self):
        ix_frame = CONFIG.manager.ix_frame + 1
        num_frame = CONFIG.manager.number_frames
        text_display = f"{ix_frame}/{num_frame}"
        size_font = const.DISPLAY_FONT_DOUBLE_SIZE if num_frame >= 10 else const.DISPLAY_FONT_SINGLE_SIZE
        im_draw = editor.draw_text(self.im_display, text_display, size_font, const.PATH_FONT_GENEI, (0, 0, 0), const.DISPLAY_BBOX)
        self.set_pil_image(im_draw)

    def on_click(self, event):
        if event.button() == Qt.MouseButton.LeftButton: ix_delta = -1
        elif event.button() == Qt.MouseButton.RightButton: ix_delta = 1
        else: return
        CONFIG.manager.shift_ix_frame(ix_delta)

        parent = self.parent()
        while parent:
            if hasattr(parent, 'stop_animation'):
                parent.stop_animation()
                break
            parent = parent.parent()
        qtlib.post_update(self.window(), True, True, True)


class SelectionMarkerStatusPanel(BitmapPanel):
    def __init__(self, parent):
        super().__init__(parent)
        self.pil_mark_on = editor.open_image(const.PATH_MARK_ON).convert("RGBA")
        self.pil_mark_off = editor.open_image(const.PATH_MARK_OFF).convert("RGBA")
        self.set_pil_image(self.pil_mark_off)
        self.label.setToolTip(_("マーカー表示"))
        self.label.mousePressEvent = self.on_left

    def update_display(self):
        marked = CONFIG.manager.marked_selection
        self.label.setToolTip(_("マーカー非表示") if marked else _("マーカー表示"))
        self.set_pil_image(self.pil_mark_on if marked else self.pil_mark_off)

    def on_left(self, event):
        if event.button() == Qt.MouseButton.LeftButton and CONFIG.manager.can_marking():
            CONFIG.manager.switch_marking()
            qtlib.post_update(self.window(), preview=True)


class PlayingStatusPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.is_playing = False

        self.btn = QWidget()
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.mousePressEvent = self.on_click
        self.btn.paintEvent = self.paint_button

        layout = QHBoxLayout(self)
        layout.addWidget(self.btn)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.set_playing(False)

    def paint_button(self, event):
        from PySide6.QtGui import QPainter
        painter = QPainter(self.btn)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        path_icon = const.PATH_PLAYING if self.is_playing else const.PATH_PAUSE
        pixmap = QPixmap(str(path_icon))

        if pixmap.isNull():
            painter.setPen(Qt.GlobalColor.white)
            text = "■" if self.is_playing else "▶"
            painter.drawText(self.btn.rect(), Qt.AlignmentFlag.AlignCenter, text)
        else:
            painter.drawPixmap(0, 0, pixmap)

    def set_playing(self, is_playing):
        self.is_playing = is_playing
        self.btn.setToolTip(_("停止") if is_playing else _("再生"))

        path_icon = const.PATH_PLAYING if is_playing else const.PATH_PAUSE
        pixmap = QPixmap(str(path_icon))
        if not pixmap.isNull():
            self.btn.setFixedSize(pixmap.size())
        else:
            self.btn.setFixedSize(32, 32)

        self.btn.update()

    def on_click(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_playing:
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'stop_animation'):
                        parent.stop_animation()
                        break
                    parent = parent.parent()
                qtlib.post_update(self.window(), preview=True)
            else:
                if not CONFIG.manager.can_save():
                    qtlib.post_info(self.window(), _("画像が表示されていません！"), _("画像未表示"), QMessageBox.Icon.Warning)
                    return
                qtlib.post_play(self.window())


class HeaderPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.panel_focus = FocusDisplayPanel(self)
        self.panel_display_num = FrameNumberDisplayPanel(self)
        self.panel_marker = SelectionMarkerStatusPanel(self)
        self.panel_playing = PlayingStatusPanel(self)

        layout = QHBoxLayout(self)
        layout.addWidget(self.panel_focus)
        layout.addWidget(self.panel_display_num)
        layout.addWidget(self.panel_marker)
        layout.addWidget(self.panel_playing)
        layout.setSpacing(5)
        self.setLayout(layout)

    def update_display(self):
        self.panel_display_num.update_display()
        self.panel_marker.update_display()
        self.panel_playing.set_playing(False)

    def set_focus(self, is_focused):
        self.panel_focus.set_focus(is_focused)
