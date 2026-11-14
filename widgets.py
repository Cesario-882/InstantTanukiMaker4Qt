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

import numpy as np
import threading
from pathlib import Path
from PIL import Image

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QRadioButton,
    QTabWidget, QScrollArea, QSizePolicy, QGridLayout,
    QTableWidget, QTableWidgetItem, QGroupBox, QMessageBox,
    QListView, QTreeView, QStyledItemDelegate, QStyle, QListWidget, QListWidgetItem
)
from PySide6.QtCore import (
    Qt, QTimer, QPoint, QSize, Signal, QAbstractListModel, QModelIndex,
    QObject, QRunnable, QThreadPool, Slot
)
from PySide6.QtGui import QPixmap, QImage, QIcon, QMovie, QFont, QColor, QStandardItemModel, QStandardItem

import const
from config import CONFIG
import editor
import menus
import qtlib
from signals import signals
from i18n import _, display


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
            if isinstance(parent, PreviewPanel):
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
        # 核心修改：不限制 32x32 了，让它保持 100x100，或者由图片大小决定
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

        # 拿到 100x100 的原图
        path_icon = const.PATH_PLAYING if self.is_playing else const.PATH_PAUSE
        pixmap = QPixmap(str(path_icon))

        if pixmap.isNull():
            painter.setPen(Qt.GlobalColor.white)
            text = "■" if self.is_playing else "▶"
            painter.drawText(self.btn.rect(), Qt.AlignmentFlag.AlignCenter, text)
        else:
            # 核心修改：直接画！不缩放！因为原图就是 100x100！
            painter.drawPixmap(0, 0, pixmap)

    def set_playing(self, is_playing):
        self.is_playing = is_playing
        self.btn.setToolTip(_("停止") if is_playing else _("再生"))

        # 核心修改：让 Widget 的尺寸完全等于图片的 100x100 尺寸！
        path_icon = const.PATH_PLAYING if is_playing else const.PATH_PAUSE
        pixmap = QPixmap(str(path_icon))
        if not pixmap.isNull():
            self.btn.setFixedSize(pixmap.size())
        else:
            self.btn.setFixedSize(32, 32) # 兜底

        self.btn.update()

    def on_click(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_playing:
                parent = self.parent()
                while parent:
                    if isinstance(parent, PreviewPanel):
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


class FileListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []

    def rowCount(self, parent=QModelIndex()): return len(self.files)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        file = self.files[index.row()]
        if role == Qt.ItemDataRole.DisplayRole: return file.label
        elif role == Qt.ItemDataRole.DecorationRole: return QIcon(file.get_qpixmap_icon())
        elif role == Qt.ItemDataRole.CheckStateRole: return Qt.CheckState.Checked if file.visible else Qt.CheckState.Unchecked
        elif role == Qt.ItemDataRole.UserRole: return file.id_file
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.CheckStateRole:
            file = self.files[index.row()]
            file.visible = (value == Qt.CheckState.Checked.value)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True
        return False

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled

    def update_files(self, new_files):
        self.beginResetModel()
        self.files = new_files
        self.endResetModel()


class FileListCtrl(QListView):
    def __init__(self, parent):
        super().__init__(parent)
        self.setIconSize(QSize(48, 48))
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setWordWrap(False)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QListView.DragDropMode.InternalMove)
        self.target_post = parent.window() if hasattr(parent, 'window') else parent

        self.model = FileListModel(self)
        self.setModel(self.model)
        
        self.clicked.connect(self.on_item_clicked)
        self.doubleClicked.connect(self.on_item_double_clicked)
        self.model.dataChanged.connect(self.on_data_changed)

    def update_display(self):
        self.model.update_files(CONFIG.manager.get_order_file_display())

    def on_item_clicked(self, index):
        id_file = index.data(Qt.ItemDataRole.UserRole)
        if id_file:
            CONFIG.manager.select(None, id_file, False)
            qtlib.post_update(self.window(), preview=True, prop=True)

    def on_item_double_clicked(self, index): pass

    def on_data_changed(self, top_left, bottom_right, roles):
        if Qt.ItemDataRole.CheckStateRole in roles:
            id_file = top_left.data(Qt.ItemDataRole.UserRole)
            visible = top_left.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked.value
            if id_file:
                CONFIG.manager.set_file_visible(id_file, visible)
                qtlib.post_update(self.window(), preview=True, component=True)

    def reset_icon(self): self.model.update_files([])

    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            id_file = index.data(Qt.ItemDataRole.UserRole)
            if id_file: menus.ComponentMenu(self.target_post, id_file).exec(event.globalPos())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            index = self.currentIndex()
            if index.isValid():
                id_file = index.data(Qt.ItemDataRole.UserRole)
                if id_file:
                    CONFIG.manager.remove(id_file)
                    qtlib.post_update(self.window(), True, True, True)
        super().keyPressEvent(event)


class PartsTreeCtrl(QTreeView):
    def __init__(self, parent):
        super().__init__(parent)
        self.setHeaderHidden(False)
        self.setIconSize(QSize(24, 24))
        self.setStyleSheet("QTreeView::item { height: 28px; }")
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeView.DragDropMode.InternalMove)
        self.target_post = parent.window() if hasattr(parent, 'window') else parent
        
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([_("詳細構成")])
        self.setModel(self.model)

    def update_display(self):
        self.model.clear()
        self.model.setHorizontalHeaderLabels([_("詳細構成")])
        order_frame = CONFIG.manager.get_order_frame()
        ix_selection = CONFIG.manager.ix_frame

        for ix, frame in enumerate(order_frame):
            frame_item = QStandardItem(_("フレーム【{num}】").format(num=ix + 1))
            frame_item.setData(ix, Qt.ItemDataRole.UserRole)
            frame_item.setEditable(False)
            
            for parts in frame.get_order_parts_display():
                parts_item = QStandardItem(parts.label)
                parts_item.setIcon(QIcon(parts.get_qpixmap_icon()))
                parts_item.setData(parts.id_parts, Qt.ItemDataRole.UserRole)
                parts_item.setCheckable(True)
                parts_item.setCheckState(Qt.CheckState.Checked if parts.visible else Qt.CheckState.Unchecked)
                frame_item.appendRow(parts_item)

            self.model.appendRow(frame_item)
            if ix_selection == ix: self.expand(frame_item.index())

    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            data = index.data(Qt.ItemDataRole.UserRole)
            if data and not isinstance(data, int): menus.ComponentMenu(self.target_post, data).exec(event.globalPos())

    def reset_icon(self): self.model.clear()


class SelectionViewerPanel(QScrollArea):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.lst_icon = []
        self.lst_id = [None]

        container = QWidget()
        self.layout = QHBoxLayout(container)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        self.setWidget(container)

        self.text_selected = QLabel(_("未選択"))
        self.layout.addWidget(self.text_selected)
        self.create_icon(const.UNSELECTED_QIMAGE)

    def update_display(self):
        lst_id_selection = CONFIG.manager.get_selections_id()
        count_selection = len(lst_id_selection)

        if count_selection == 0:
            self.text_selected.show()
            self.text_selected.setText(_("未選択"))
            lst_id_selection.append(None)
        elif count_selection == 1:
            self.text_selected.show()
            self.text_selected.setText(CONFIG.manager.get_image(lst_id_selection[0]).label)
        else:
            self.text_selected.hide()

        if set(self.lst_id) == set(lst_id_selection): return

        for icon, id_exist, id_selection in zip(self.lst_icon, self.lst_id, lst_id_selection):
            if id_exist == id_selection: continue
            if id_selection is None:
                icon.set_pil_image(const.BG_UNSELECTED)
                continue
            icon.set_pixmap(CONFIG.manager.get_image(id_selection).get_qpixmap_icon())

        num_selection, num_exists = len(lst_id_selection), len(self.lst_id)
        if num_selection > num_exists:
            for im in CONFIG.manager.get_images_selection()[num_exists:]:
                self.create_icon(im.get_qpixmap_icon())
        elif num_selection < num_exists:
            for panel in self.lst_icon[num_selection:]: panel.deleteLater()
            self.lst_icon = self.lst_icon[:num_selection]
        self.lst_id = lst_id_selection

    def create_icon(self, pil_or_qpixmap):
        panel_bmp = BitmapPanel(self)
        if isinstance(pil_or_qpixmap, QPixmap): panel_bmp.set_pixmap(pil_or_qpixmap)
        else: panel_bmp.set_pil_image(pil_or_qpixmap)
        self.lst_icon.append(panel_bmp)
        self.layout.insertWidget(len(self.lst_icon) - 1, panel_bmp)

    def reset_icon(self):
        for icon in self.lst_icon[1:]: icon.deleteLater()
        self.lst_icon = self.lst_icon[:1]
        self.lst_icon[0].set_pil_image(const.BG_UNSELECTED)
        self.lst_id = [None]


class PropertyPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.target_post = parent.window() if hasattr(parent, 'window') else parent
        self.panel_selection = SelectionViewerPanel(self)

        self.spin_offset_x = QSpinBox(); self.spin_offset_x.setRange(-250, 250)
        self.spin_offset_y = QSpinBox(); self.spin_offset_y.setRange(-250, 250)
        self.spin_angle = QSpinBox(); self.spin_angle.setRange(-360, 360)
        self.spin_trans = QSpinBox(); self.spin_trans.setRange(0, 254)

        self.spin_zoom_x = QDoubleSpinBox(); self.spin_zoom_x.setRange(0.1, 3.0); self.spin_zoom_x.setSingleStep(0.01); self.spin_zoom_x.setValue(1.0)
        self.spin_zoom_y = QDoubleSpinBox(); self.spin_zoom_y.setRange(0.1, 3.0); self.spin_zoom_y.setSingleStep(0.01); self.spin_zoom_y.setValue(1.0)

        self.combo_blend = QComboBox()
        for mode in const.MODES_BLEND: self.combo_blend.addItem(_(mode), mode)
        self.combo_blend.setCurrentIndex(self.combo_blend.findData(const.BlendMode.NONE))

        self.ctrl_color = QPushButton(); self.ctrl_color.setStyleSheet("background-color: #ff0000;"); self.ctrl_color.setFixedSize(30, 30)
        self.ctrl_color.clicked.connect(self.on_color_picker)

        self.spin_alpha = QDoubleSpinBox(); self.spin_alpha.setRange(0.1, 1.0); self.spin_alpha.setSingleStep(0.01); self.spin_alpha.setValue(0.3)

        self.check_alias = QCheckBox(_("アンチエイリアス"))
        self.check_flip = QCheckBox(_("左右反転"))

        self.spin_offset_x.valueChanged.connect(self.on_offset)
        self.spin_offset_y.valueChanged.connect(self.on_offset)
        self.spin_angle.valueChanged.connect(self.on_angle)
        self.spin_zoom_x.valueChanged.connect(self.on_zoom)
        self.spin_zoom_y.valueChanged.connect(self.on_zoom)
        self.spin_trans.valueChanged.connect(self.on_trans)
        self.combo_blend.currentTextChanged.connect(self.on_blend)
        self.check_alias.stateChanged.connect(self.on_alias)
        self.check_flip.stateChanged.connect(self.on_flip)

        self.setup_layout()
        self.setEnabled(False)

    def setup_layout(self):
        group = QGroupBox(_("パーツプロパティ"))
        layout = QVBoxLayout(group)

        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel(_("選択中画像:")))
        select_layout.addWidget(self.panel_selection)
        layout.addLayout(select_layout)

        grid = QGridLayout()
        grid.addWidget(QLabel(_("オフセット")), 0, 0)
        ox = QHBoxLayout(); ox.addWidget(QLabel("X:")); ox.addWidget(self.spin_offset_x); grid.addLayout(ox, 0, 1)
        oy = QHBoxLayout(); oy.addWidget(QLabel("Y:")); oy.addWidget(self.spin_offset_y); grid.addLayout(oy, 0, 2)
        grid.addWidget(self.check_alias, 0, 3)

        grid.addWidget(QLabel(_("角度")), 1, 0); grid.addWidget(self.spin_angle, 1, 1); grid.addWidget(QLabel(""), 1, 2); grid.addWidget(self.check_flip, 1, 3)

        grid.addWidget(QLabel(_("拡大率")), 2, 0)
        zx = QHBoxLayout(); zx.addWidget(QLabel("X:")); zx.addWidget(self.spin_zoom_x); grid.addLayout(zx, 2, 1)
        zy = QHBoxLayout(); zy.addWidget(QLabel("Y:")); zy.addWidget(self.spin_zoom_y); grid.addLayout(zy, 2, 2)
        grid.addWidget(QLabel(""), 2, 3)

        grid.addWidget(QLabel(_("透過率")), 3, 0); grid.addWidget(self.spin_trans, 3, 1); grid.addWidget(QLabel(""), 3, 2); grid.addWidget(QLabel(""), 3, 3)

        grid.addWidget(QLabel(_("カラーブレンド")), 4, 0); grid.addWidget(self.combo_blend, 4, 1); grid.addWidget(self.ctrl_color, 4, 2); grid.addWidget(self.spin_alpha, 4, 3)

        layout.addLayout(grid)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(group)
        self.setLayout(main_layout)

        self.spin_alpha.hide()
        self.ctrl_color.setEnabled(False)

    def on_color_picker(self):
        from PySide6.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            self.ctrl_color.setStyleSheet(f"background-color: {color.name()};")
            self.on_blend()

    def on_offset(self):
        self.panel_selection.setFocus()
        CONFIG.manager.set_offset((self.spin_offset_x.value(), self.spin_offset_y.value()))
        qtlib.post_update(self.target_post, preview=True)

    def on_angle(self):
        self.panel_selection.setFocus()
        CONFIG.manager.set_angle(self.spin_angle.value())
        qtlib.post_update(self.target_post, preview=True)

    def on_zoom(self):
        self.panel_selection.setFocus()
        CONFIG.manager.set_zoom(self.spin_zoom_x.value(), self.spin_zoom_y.value())
        qtlib.post_update(self.target_post, preview=True)

    def on_trans(self):
        self.panel_selection.setFocus()
        CONFIG.manager.set_transparency(self.spin_trans.value())
        qtlib.post_update(self.target_post, preview=True)

    def on_alias(self):
        CONFIG.manager.set_alias(self.check_alias.isChecked())
        qtlib.post_update(self.target_post, preview=True)

    def on_flip(self):
        CONFIG.manager.set_flip(self.check_flip.isChecked())
        qtlib.post_update(self.target_post, preview=True)

    def on_blend(self):
        self.panel_selection.setFocus()
        mode_blend = self.combo_blend.currentData()
        color_blend = self.ctrl_color.palette().button().color().getRgb()[:3]
        alpha_blend = self.spin_alpha.value()
        CONFIG.manager.set_blend_color(mode_blend, color_blend, alpha_blend)
        qtlib.post_update(self.target_post, preview=True)

        enable = mode_blend != const.BlendMode.NONE
        self.ctrl_color.setEnabled(enable)
        enable_alpha = mode_blend == const.BlendMode.ALPHA
        self.spin_alpha.setVisible(enable_alpha)
        self.spin_alpha.setEnabled(enable_alpha)

    def update_display(self):
        self.panel_selection.update_display()
        color_bg = const.COLOR_FILE if CONFIG.manager.selected_file else const.COLOR_PARTS
        self.setStyleSheet(f"background-color: rgb({color_bg[0]}, {color_bg[1]}, {color_bg[2]});")

        selections = CONFIG.manager.get_images_selection()
        if not selections: self.setEnabled(False)
        elif len(selections) == 1: self.setEnabled(True); self.set_properties_single(selections[0])
        else: self.setEnabled(True)

    def set_properties_single(self, selection):
        offset_x, offset_y = selection.offset
        width, height = CONFIG.manager.size
        self.spin_offset_x.setValue(offset_x); self.spin_offset_y.setValue(offset_y)
        self.spin_offset_x.setRange(-width, width); self.spin_offset_y.setRange(-height, height)

        self.spin_angle.setValue(selection.angle)
        self.spin_zoom_x.setValue(selection.zoom_x)
        self.spin_zoom_y.setValue(selection.zoom_y)
        self.spin_trans.setValue(selection.transparency)
        self.check_alias.setChecked(selection.anti_alias)
        self.check_flip.setChecked(selection.is_flip)

        self.combo_blend.setCurrentIndex(self.combo_blend.findData(selection.mode_blend))
        color = QColor(*selection.color_blend)
        self.ctrl_color.setStyleSheet(f"background-color: {color.name()};")
        self.spin_alpha.setValue(selection.alpha_blend)

        enable = selection.mode_blend != const.BlendMode.NONE
        self.ctrl_color.setEnabled(enable)
        enable_alpha = selection.mode_blend == const.BlendMode.ALPHA
        self.spin_alpha.setVisible(enable_alpha)
        self.spin_alpha.setEnabled(enable_alpha)

    def reset_icon(self):
        self.panel_selection.reset_icon()


class ThumbnailPanel(QWidget):
    MARGIN = 5
    ICON_SIZE = (100, 100)
    THUMB_SIZE = (90, 90)

    def __init__(self, parent, path, on_dialog):
        super().__init__(parent)
        self.parent_widget = parent
        self.on_dialog = on_dialog

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setMovement(QListWidget.Movement.Static)
        self.list_widget.setWordWrap(True)

        # ===== 暴力锁定布局，解决挤压和左偏 =====
        self.list_widget.setIconSize(QSize(*self.ICON_SIZE))
        self.list_widget.setGridSize(QSize(120, 140))
        self.list_widget.setSpacing(0)
        self.list_widget.setContentsMargins(5, 5, 5, 5)
        self.list_widget.setStyleSheet("QListWidget::item { padding: 0px; margin: 0px; }")
        self.list_widget.setStyleSheet("QListWidget::item { padding: 5px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_widget)

        self.list_widget.itemClicked.connect(self.on_click_left)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.on_click_right)

        self.threadpool = QThreadPool.globalInstance()
        self.show_button(path)

    def show_button(self, path):
        self.list_widget.clear()

        if path.is_dir():
            items_paths = self.get_lst_path(path)
        else:
            items_paths = [path]

        for path_image in items_paths:
            item = QListWidgetItem(QIcon(QPixmap.fromImage(const.UNSELECTED_QIMAGE)), _("加载中..."))
            item.setData(Qt.ItemDataRole.UserRole, (path_image, None))
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            self.list_widget.addItem(item)

            self._start_worker(path_image, item)

    def _tooltip_for(self, path_image) -> str:
        if not path_image.is_dir():
            return const.DIC_ALIAS.get(path_image.stem, display(path_image.stem))

        if "行" in path_image.stem or path_image.stem == "幻覚":
            lines = [_("存在するキャラクター素材:")]
            try:
                # 获取所有条目，并按名字排序
                entries = sorted([e for e in path_image.iterdir() if e.is_dir() or e.is_file()])
                # 只取前 15 个，防止 Tooltip 撑爆屏幕
                for entry in entries[:15]:
                    lines.append("    " + display(entry.stem))

                # 如果超过 15 个，加上省略号提示
                if len(entries) > 15:
                    lines.append(f"    ... 以及其他 {len(entries) - 15} 个素材")
            except OSError:
                pass

            # 【核心修复】：用 HTML 格式渲染换行，Qt 原生支持！
            html_content = "<br>".join(lines)
            return f"<html><body><p>{html_content}</p></body></html>"

        return const.DIC_ALIAS.get(path_image.stem, display(path_image.stem))

    def _start_worker(self, path_image, item):
        worker = ThumbnailWorker(path_image, self, item)
        worker.signals.finished.connect(self.on_thumb_ready)
        worker.signals.error.connect(self.on_thumb_error)
        self.threadpool.start(worker)

    @Slot(Path, QIcon, object)
    def on_thumb_ready(self, path_image, icon, item):
        if item:
            item.setIcon(icon)
            raw_text = const.DIC_ALIAS.get(path_image.stem, display(path_image.stem))
            display_text = raw_text[:8] + ".." if len(raw_text) > 8 else raw_text
            item.setText(display_text)
            item.setToolTip(self._tooltip_for(path_image))
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)

    @Slot(Path, str)
    def on_thumb_error(self, path_image, error_msg):
        print(f"Thumb Error: {path_image.name} - {error_msg}")

    def get_lst_path(self, path_folder):
        lst_path_folder = []
        lst_path_image = []
        for path in path_folder.iterdir():
            if path.is_dir():
                lst_path_folder.append(path)
            elif path.suffix.lower() in const.SUFFIXES_IMAGE:
                lst_path_image.append(path)

        folder_append = self.get_another_folder(path_folder, const.FOLDER_MATERIAL, const.FOLDER_APPEND)
        if folder_append:
            lst_folder_preset = [f.name for f in lst_path_folder]
            for path in folder_append.iterdir():
                if path.is_dir() and path.name not in lst_folder_preset:
                    lst_path_folder.append(path)
                elif path.suffix.lower() in const.SUFFIXES_IMAGE:
                    lst_path_image.append(path)

        lst_path_folder = sorted(lst_path_folder, key=lambda f: f.name)
        lst_path_image = sorted(lst_path_image, key=lambda f: f.name)
        return lst_path_folder + lst_path_image

    def get_thumb_image(self, path):
        path_icon = self.get_path_icon(path)
        im = editor.open_image(path_icon)
        if not im:
            im = editor.open_image(const.PATH_BUTTON_UNKNOWN)
            if not im:
                return None

        if path.is_dir():
            bg = const.BG_FOLDER
            size_thumb = self.ICON_SIZE
        elif getattr(im, "is_animated", False):
            bg = const.BG_ANIMATION
            size_thumb = self.THUMB_SIZE
        else:
            bg = const.BG_PHOTO
            size_thumb = self.THUMB_SIZE

        icon = editor.create_icon(im, self.ICON_SIZE, size_thumb, bg)
        return icon

    def get_path_icon(self, path):
        if path.is_dir():
            path_icon = const.FOLDER_APPEND_BUTTON / f"{path.stem}.png"
            if not path_icon.exists():
                path_icon = const.FOLDER_BUTTON / f"{path.stem}.png"
                if not path_icon.exists():
                    path_icon = const.PATH_BUTTON_UNKNOWN
        else:
            path_icon = path
        return path_icon

    def get_another_folder(self, path_folder, path_root, path_another):
        lst_parts = list(path_folder.parts)
        for parts_root in path_root.parts:
            if parts_root in lst_parts:
                lst_parts.remove(parts_root)
        child_another = "/".join(lst_parts)
        folder_another = path_another / child_another
        return folder_another if folder_another.exists() else False

    def on_click_left(self, item):
        path, frames = item.data(Qt.ItemDataRole.UserRole)
        if path.is_dir():
            qtlib.post_select(self.parent_widget, path)
        else:
            qtlib.post_append(self.window(), path_image=path, frames=frames)

    def on_click_right(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        path, frames = item.data(Qt.ItemDataRole.UserRole)
        if not path.is_dir():
            menu = menus.AppendMenu(self.parent_widget, path, frames, None)
            menu.exec(self.list_widget.mapToGlobal(pos))


class ImageAppendPanel(QWidget):
    ORDER_BTN = [
        const.ImageType.BASE, const.ImageType.COSTUME, const.ImageType.FACE,
        const.ImageType.BROWS, const.ImageType.EYES, const.ImageType.MOUTH,
        const.ImageType.ACCESSORY, const.ImageType.FREE
    ]
    FILES_DISPLAY_LIMIT = 500

    def __init__(self, parent, caption, path_init=None, on_dialog=False):
        super().__init__(parent)
        self.on_dialog = on_dialog
        path_init = path_init if path_init else const.FOLDER_MATERIAL / const.ImageType.BASE

        self.panel_thumb = ThumbnailPanel(self, path_init, on_dialog)

        group = QGroupBox(caption)
        layout = QVBoxLayout(group)

        btn_layout = QHBoxLayout()
        import_layout = QVBoxLayout()

        for parts in self.ORDER_BTN:
            icon_path = const.FOLDER_WIDGET / f"{parts}.png"
            if icon_path.exists():
                pixmap = QPixmap(str(icon_path))
                btn = QPushButton()
                btn.setIcon(QIcon(pixmap))
                btn.setIconSize(QSize(50, 50))
                btn.setToolTip(const.DIC_ALIAS.get(parts, display(parts)))
                btn.setFixedSize(54, 54)
                folder_parts = const.FOLDER_MATERIAL / parts
                btn.clicked.connect(self.on_select_btn(folder_parts))
                btn_layout.addWidget(btn)

        import_icon = const.PATH_BTN_IMPORT
        if import_icon.exists():
            pixmap = QPixmap(str(import_icon))
            btn_import = QPushButton()
            btn_import.setIcon(QIcon(pixmap))
            btn_import.setIconSize(QSize(32, 32))
            btn_import.setToolTip(_("画像取込"))
            btn_import.setFixedSize(40, 40)
            btn_import.clicked.connect(self.on_import)
            import_layout.addWidget(btn_import, alignment=Qt.AlignmentFlag.AlignRight)

        btn_layout.addLayout(import_layout)
        layout.addLayout(btn_layout)

        self.thumb_layout = QVBoxLayout()
        self.thumb_layout.addWidget(self.panel_thumb)
        layout.addLayout(self.thumb_layout)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(group)

        signals.select.connect(self.on_select_thumb)

    def on_select_btn(self, path_folder):
        def inner():
            if hasattr(self, 'panel_thumb') and self.panel_thumb:
                self.thumb_layout.removeWidget(self.panel_thumb)
                self.panel_thumb.deleteLater()
            self.panel_thumb = ThumbnailPanel(self, path_folder, self.on_dialog)
            self.thumb_layout.addWidget(self.panel_thumb)
        return inner

    def on_select_thumb(self, data):
        path = data.get('path')
        if path and path.is_dir() and self.exceeded_display_limit(path):
            qtlib.post_info(self.window(), _("選択したフォルダ直下の画像が多すぎます!\n500件以下になるよう減らしてください!"), _("読込件数オーバー"), QMessageBox.Icon.Warning)
            return

        if hasattr(self, 'panel_thumb') and self.panel_thumb:
            self.thumb_layout.removeWidget(self.panel_thumb)
            self.panel_thumb.deleteLater()
        self.panel_thumb = ThumbnailPanel(self, path, self.on_dialog)
        self.thumb_layout.addWidget(self.panel_thumb)

    def exceeded_display_limit(self, path_folder):
        counter = 0
        for _ in path_folder.iterdir():
            counter += 1
            if counter > self.FILES_DISPLAY_LIMIT:
                return True
        return False

    def on_import(self):
        wildcard = ";;".join([f"{ext.upper().replace('.', '')} files (*{ext})" for ext in const.SUFFIXES_IMAGE])
        path_image = qtlib.select_file(self, _("取り込みたい画像を選択してください。"), wildcard)
        if path_image:
            qtlib.post_append(self.window(), path_image)


class ComponentPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.target_post = parent.window() if hasattr(parent, 'window') else parent
        self.tab_widget = QTabWidget()
        self.page_file = QWidget()
        self.page_parts = QWidget()

        self.flc = FileListCtrl(self.page_file)
        file_layout = QVBoxLayout(self.page_file)
        file_layout.addWidget(self.flc)
        self.page_file.setLayout(file_layout)

        self.tree = PartsTreeCtrl(self.page_parts)
        parts_layout = QVBoxLayout(self.page_parts)
        parts_layout.addWidget(self.tree)
        self.page_parts.setLayout(parts_layout)

        self.tab_widget.tabBar().setExpanding(True)
        self.tab_widget.addTab(self.page_file, _("画像一覧"))
        self.tab_widget.addTab(self.page_parts, _("詳細構成"))

        layout = QVBoxLayout(self)
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def update_display(self):
        if CONFIG.manager.selected_file:
            self.tab_widget.setCurrentIndex(0)
        else:
            self.tab_widget.setCurrentIndex(1)

        self.flc.update_display()
        self.tree.update_display()

    def reset_icon(self):
        self.flc.reset_icon()
        self.tree.reset_icon()

    def on_tab_changed(self, index):
        selected_file = index == 0
        CONFIG.manager.switch_selected_file(selected_file)
        qtlib.post_update(self.window(), preview=True, prop=True)


class CompositePanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.target_post = parent.window() if hasattr(parent, 'window') else parent
        group = QGroupBox(_("全体プロパティ"))
        layout = QVBoxLayout(group)

        frame_layout = QHBoxLayout()
        self.check_fixed_frames = QCheckBox(_("フレーム数"))
        self.spin_num_frames = QSpinBox()
        self.spin_num_frames.setRange(1, 99)
        self.spin_num_frames.setValue(1)
        self.spin_num_frames.setEnabled(False)
        frame_layout.addWidget(self.check_fixed_frames)
        frame_layout.addWidget(self.spin_num_frames)
        frame_layout.addStretch()
        layout.addLayout(frame_layout)

        size_layout = QHBoxLayout()
        self.check_fixed_size = QCheckBox(_("画像サイズ"))
        self.spin_width = QSpinBox()
        self.spin_width.setRange(const.MIN_WIDTH, const.MAX_WIDTH)
        self.spin_width.setSingleStep(50)
        self.spin_width.setValue(const.DEFAULT_WIDTH)
        self.spin_width.setEnabled(False)
        self.spin_height = QSpinBox()
        self.spin_height.setRange(const.MIN_HEIGHT, const.MAX_HEIGHT)
        self.spin_height.setSingleStep(50)
        self.spin_height.setValue(const.DEFAULT_HEIGHT)
        self.spin_height.setEnabled(False)

        size_layout.addWidget(self.check_fixed_size)
        size_layout.addWidget(QLabel("X:"))
        size_layout.addWidget(self.spin_width)
        size_layout.addWidget(QLabel("Y:"))
        size_layout.addWidget(self.spin_height)
        size_layout.addStretch()
        layout.addLayout(size_layout)

        duration_layout = QVBoxLayout()
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(QLabel(_("表示間隔(ms)")))
        self.radio_single = QRadioButton(_("シングル"))
        self.radio_single.setChecked(True)
        self.radio_multi = QRadioButton(_("マルチ"))
        radio_layout.addWidget(self.radio_single)
        radio_layout.addWidget(self.radio_multi)
        radio_layout.addStretch()
        duration_layout.addLayout(radio_layout)

        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(20, 1000)
        self.spin_duration.setValue(100)
        duration_layout.addWidget(self.spin_duration)

        self.grid_duration = QTableWidget(1, 1)
        self.grid_duration.setHorizontalHeaderLabels([_("【F1】")])
        self.grid_duration.hide()
        self.grid_duration.setMaximumHeight(100)
        duration_layout.addWidget(self.grid_duration)

        layout.addLayout(duration_layout)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel(_("色フィルタ:")))
        self.combo_filter_color = QComboBox()
        for mode in const.FILTERS_COLOR:
            self.combo_filter_color.addItem(_(mode), mode)
        self.combo_filter_color.setCurrentIndex(self.combo_filter_color.findData(const.ColorFilter.NONE))
        filter_layout.addWidget(self.combo_filter_color)

        filter_layout.addWidget(QLabel(_("画像フィルタ:")))
        self.combo_filter_image = QComboBox()
        for mode in const.FILTERS_IMAGE:
            self.combo_filter_image.addItem(_(mode), mode)
        self.combo_filter_image.setCurrentIndex(self.combo_filter_image.findData(const.ImageFilter.NONE))
        filter_layout.addWidget(self.combo_filter_image)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        save_layout = QHBoxLayout()
        self.combo_save = QComboBox()
        for mode in const.MODES_SAVE:
            self.combo_save.addItem(_(mode), mode)
        self.combo_save.setCurrentIndex(self.combo_save.findData(const.SaveMode.GIF))
        self.btn_save = QPushButton(_("保存"))
        self.btn_clear = QPushButton(_("ALLクリア"))
        save_layout.addWidget(self.combo_save)
        save_layout.addWidget(self.btn_save)
        save_layout.addStretch()
        save_layout.addWidget(self.btn_clear)
        layout.addLayout(save_layout)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(group)
        self.setLayout(main_layout)

        self.check_fixed_frames.stateChanged.connect(self.on_check_frames)
        self.spin_num_frames.valueChanged.connect(self.on_spin_frames)
        self.check_fixed_size.stateChanged.connect(self.on_check_size)
        self.spin_width.valueChanged.connect(self.on_spin_size)
        self.spin_height.valueChanged.connect(self.on_spin_size)
        self.radio_single.toggled.connect(self.on_single)
        self.radio_multi.toggled.connect(self.on_multi)
        self.spin_duration.valueChanged.connect(self.on_duration_single)
        self.combo_filter_color.currentTextChanged.connect(self.on_filter)
        self.combo_filter_image.currentTextChanged.connect(self.on_filter)
        self.btn_save.clicked.connect(self.on_save)
        self.btn_clear.clicked.connect(self.on_clear)
        self.grid_duration.cellChanged.connect(self.on_grid_change)

        self.update_display()

    def update_display(self):
        self.check_fixed_frames.setChecked(CONFIG.manager.fixed_number_frames)
        self.spin_num_frames.setEnabled(CONFIG.manager.fixed_number_frames)
        self.spin_num_frames.setValue(CONFIG.manager.number_frames)

        self.check_fixed_size.setChecked(CONFIG.manager.fixed_size)
        self.spin_width.setEnabled(CONFIG.manager.fixed_size)
        self.spin_height.setEnabled(CONFIG.manager.fixed_size)
        width, height = CONFIG.manager.size
        self.spin_width.setValue(width)
        self.spin_height.setValue(height)

        self.spin_duration.setValue(CONFIG.manager.duration_single)

        num_frames = CONFIG.manager.number_frames
        current_cols = self.grid_duration.columnCount()
        if num_frames > current_cols:
            self.grid_duration.insertColumn(current_cols)
        elif num_frames < current_cols:
            self.grid_duration.removeColumn(current_cols - 1)

        for ix, d in enumerate(CONFIG.manager.durations_multi):
            if ix < self.grid_duration.columnCount():
                self.grid_duration.setHorizontalHeaderItem(ix, QTableWidgetItem(_("【F{num}】").format(num=ix + 1)))
                self.grid_duration.setItem(0, ix, QTableWidgetItem(str(d)))

        self.combo_filter_color.setCurrentIndex(self.combo_filter_color.findData(CONFIG.manager.filter_color))
        self.combo_filter_image.setCurrentIndex(self.combo_filter_image.findData(CONFIG.manager.filter_image))

    def on_check_frames(self):
        fixed = self.check_fixed_frames.isChecked()
        CONFIG.manager.fix_num_frames(fixed)
        self.spin_num_frames.setEnabled(fixed)
        self.spin_num_frames.setValue(CONFIG.manager.number_frames)
        qtlib.post_update(self.target_post, preview=True, component=True)

    def on_spin_frames(self):
        num_frames = self.spin_num_frames.value()
        CONFIG.manager.change_number_frames(num_frames)
        qtlib.post_update(self.target_post, preview=True, component=True)

    def on_check_size(self):
        fixed = self.check_fixed_size.isChecked()
        CONFIG.manager.fix_size(fixed)
        width, height = CONFIG.manager.size
        self.spin_width.setValue(width)
        self.spin_height.setValue(height)
        self.spin_width.setEnabled(fixed)
        self.spin_height.setEnabled(fixed)
        qtlib.post_update(self.target_post, preview=True, prop=True)

    def on_spin_size(self):
        width = self.spin_width.value()
        height = self.spin_height.value()
        CONFIG.manager.change_size((width, height))
        qtlib.post_update(self.target_post, preview=True, prop=True)

    def on_single(self, checked):
        if checked:
            self.spin_duration.show()
            self.grid_duration.hide()
            qtlib.post_layout(self.target_post)

    def on_multi(self, checked):
        if checked:
            self.spin_duration.hide()
            self.grid_duration.show()
            qtlib.post_layout(self.target_post)

    def on_duration_single(self):
        duration = self.spin_duration.value()
        CONFIG.manager.set_duration_single(duration)

    def on_grid_change(self, row, col):
        item = self.grid_duration.item(row, col)
        if item:
            try:
                duration = int(item.text())
                durations = CONFIG.manager.durations_multi.copy()
                if col < len(durations):
                    durations[col] = duration
                    CONFIG.manager.set_duration_multi(durations)
            except ValueError:
                pass

    def on_filter(self):
        filter_color = self.combo_filter_color.currentData()
        filter_image = self.combo_filter_image.currentData()
        CONFIG.manager.set_filter(filter_color, filter_image)
        qtlib.post_update(self.target_post, preview=True)

    def on_save(self):
        if not CONFIG.manager.can_save():
            qtlib.show_message(self, _("画像が表示されていません！"), _("画像未表示"), QMessageBox.Icon.Warning)
            return

        mode_save = self.combo_save.currentData()
        if mode_save == const.SaveMode.GIF:
            self.save_gif()
        elif mode_save == const.SaveMode.PNG_SEQUENCE:
            self.save_png_sequence()
        elif mode_save == const.SaveMode.PNG_ANIME:
            self.save_apng()

    def save_gif(self):
        path_save = qtlib.save_file(self, _("GIF保存"), "*.gif", _("たぬき.gif"))
        if not path_save:
            return

        qtlib.post_start_progress(self.target_post, "少しお待ちください…", _("保存中"))
        thread = threading.Thread(target=self.thread_save_gif, args=(path_save,))
        thread.start()

    def thread_save_gif(self, path_save):
        try:
            is_single = self.radio_single.isChecked()
            CONFIG.manager.save_gif(path_save, is_single)
            self.complete_save(path_save.parent)
        except Exception as e:
            qtlib.post_info(self.target_post, f"保存失败: {e}", _("错误"), QMessageBox.Icon.Critical)
        finally:
            qtlib.post_end_progress(self.target_post)

    def save_png_sequence(self):
        folder_save = qtlib.select_folder(self, _("連番PNG保存"))
        if not folder_save:
            return
        qtlib.post_start_progress(self.target_post, "少しお待ちください…", _("保存中"))
        thread = threading.Thread(target=self.thread_save_png, args=(folder_save,))
        thread.start()

    def thread_save_png(self, folder_save):
        with qtlib.progress_context(self.target_post, "保存に失敗しました…", _("保存失敗")):
            CONFIG.manager.save_png_sequence(folder_save)
            self.complete_save(folder_save)

    def save_apng(self):
        path_save = qtlib.save_file(self, _("APNG保存"), "*.png", _("Aたぬき.png"))
        if not path_save:
            return
        qtlib.post_start_progress(self.target_post, "少しお待ちください…", _("保存中"))
        thread = threading.Thread(target=self.thread_save_apng, args=(path_save,))
        thread.start()

    def thread_save_apng(self, path_save):
        with qtlib.progress_context(self.target_post, "保存に失敗しました…", _("保存失敗")):
            is_single = self.radio_single.isChecked()
            CONFIG.manager.save_apng(path_save, is_single)
            self.complete_save(path_save.parent)

    def complete_save(self, path_open):
        message = _("保存が完了しました。")
        caption = _("保存完了")
        qtlib.post_end_progress(self.target_post, message, caption, path_open=path_open)

    def on_clear(self):
        reply = qtlib.show_question(self, _("作業状況をすべてクリアしますか？"), _("ALLクリア"))
        if reply == QMessageBox.StandardButton.Yes:
            CONFIG.manager.clear()
            qtlib.post_update(self.target_post, True, True, True)
