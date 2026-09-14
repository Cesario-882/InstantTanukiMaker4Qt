import numpy as np
import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QRadioButton,
    QTabWidget, QListWidget, QListWidgetItem, QTreeWidget,
    QTreeWidgetItem, QScrollArea, QFrame, QSizePolicy,
    QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QButtonGroup, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QPoint, QSize, Signal, Slot
from PySide6.QtGui import QPixmap, QImage, QFont, QColor, QKeyEvent, QMouseEvent, QWheelEvent, QIcon

import const
from config import CONFIG
import editor
import menus
import qtlib
from signals import signals
from i18n import _


# ===== 图像显示组件 =====
class BitmapPanel(QWidget):
    """图像显示组件 - PySide6 版本"""
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
        """设置 QPixmap"""
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
        """从 PIL Image 设置图像"""
        self.pil_image = pil_image
        if pil_image is None:
            return
        pixmap = self.pil_to_qpixmap(pil_image)
        self.set_pixmap(pixmap)

    def set_qimage(self, qimage):
        """从 QImage 设置图像"""
        if qimage is None or qimage.isNull():
            empty = QPixmap(1, 1)
            empty.fill(Qt.GlobalColor.transparent)
            self.set_pixmap(empty)
            return
        pixmap = QPixmap.fromImage(qimage)
        self.set_pixmap(pixmap)

    def load_file(self, path_file: Path):
        """从文件加载图像"""
        try:
            from PIL import Image
            pil_image = Image.open(path_file).convert("RGBA")
            self.set_pil_image(pil_image)
        except Exception as e:
            print(f"Failed to load image: {e}")
            empty = QPixmap(1, 1)
            empty.fill(Qt.GlobalColor.transparent)
            self.set_pixmap(empty)

    def pil_to_qpixmap(self, pil_image):
        """将 PIL Image 转换为 QPixmap"""
        if pil_image is None:
            return QPixmap()
        # 检查是否是 PIL Image
        if hasattr(pil_image, 'mode'):
            if pil_image.mode != 'RGBA':
                pil_image = pil_image.convert('RGBA')
            data = pil_image.tobytes("raw", "RGBA")
            qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
            return QPixmap.fromImage(qimage)
        # 如果已经是 QImage，直接转换
        elif isinstance(pil_image, QImage):
            return QPixmap.fromImage(pil_image)
        return QPixmap()

    def get_pixmap(self) -> QPixmap:
        return self.current_pixmap

    def mousePressEvent(self, event):
        """鼠标点击事件 - 用于子类重写"""
        pass


# ===== 焦点显示面板 =====
class FocusDisplayPanel(BitmapPanel):
    """焦点状态显示"""
    def __init__(self, parent):
        super().__init__(parent)

        im_focus_on = editor.open_image(const.PATH_FOCUS_ON).convert("RGBA")
        im_focus_off = editor.open_image(const.PATH_FOCUS_OFF).convert("RGBA")
        self.pil_focus_on = im_focus_on
        self.pil_focus_off = im_focus_off

        self.set_pil_image(self.pil_focus_off)
        self.label.setToolTip(_("キー受付"))
        self.label.mousePressEvent = self.on_click

    def on_click(self, event):
        """点击切换焦点"""
        # 找到预览面板并设置焦点
        parent = self.parent()
        while parent:
            if hasattr(parent, 'sbmp_preview') and parent.sbmp_preview:
                parent.sbmp_preview.setFocus()
                break
            parent = parent.parent()

    def set_focus(self, is_focused):
        """设置焦点状态"""
        pil_img = self.pil_focus_on if is_focused else self.pil_focus_off
        self.set_pil_image(pil_img)


# ===== 帧号显示面板 =====
class FrameNumberDisplayPanel(BitmapPanel):
    """帧号显示"""
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
        size_font = (const.DISPLAY_FONT_DOUBLE_SIZE if num_frame >= 10 else
                     const.DISPLAY_FONT_SINGLE_SIZE)
        im_draw = editor.draw_text(self.im_display, text_display, size_font,
                                   const.PATH_FONT_GENEI, (0, 0, 0), const.DISPLAY_BBOX)
        self.set_pil_image(im_draw)

    def on_click(self, event):
        """点击切换帧"""
        if event.button() == Qt.MouseButton.LeftButton:
            ix_delta = -1
        elif event.button() == Qt.MouseButton.RightButton:
            ix_delta = 1
        else:
            return

        CONFIG.manager.shift_ix_frame(ix_delta)
        qtlib.post_update(self.window(), True, True, True)


# ===== 选择标记状态面板 =====
class SelectionMarkerStatusPanel(BitmapPanel):
    """选择标记状态"""
    def __init__(self, parent):
        super().__init__(parent)

        im_mark_on = editor.open_image(const.PATH_MARK_ON).convert("RGBA")
        im_mark_off = editor.open_image(const.PATH_MARK_OFF).convert("RGBA")
        self.pil_mark_on = im_mark_on
        self.pil_mark_off = im_mark_off

        self.set_pil_image(self.pil_mark_off)
        self.label.setToolTip(_("マーカー表示"))
        self.label.mousePressEvent = self.on_left

    def update_display(self):
        marked = CONFIG.manager.marked_selection
        pil_img = self.pil_mark_on if marked else self.pil_mark_off
        tooltip = _("マーカー非表示") if marked else _("マーカー表示")
        self.label.setToolTip(tooltip)
        self.set_pil_image(pil_img)

    def on_left(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if CONFIG.manager.can_marking():
                CONFIG.manager.switch_marking()
                qtlib.post_update(self.window(), preview=True)


# ===== 播放状态面板 =====
class PlayingStatusPanel(QWidget):
    """播放/暂停控制"""
    def __init__(self, parent):
        super().__init__(parent)
        self.is_playing = False

        self.panel_pause = BitmapPanel(self, path_file=const.PATH_PAUSE)
        self.panel_pause.label.setToolTip(_("再生"))
        self.panel_pause.label.mousePressEvent = self.on_play

        # 动画标签（用于GIF播放）
        self.anim_label = QLabel()
        self.anim_label.setToolTip(_("停止"))
        self.anim_label.hide()
        self.anim_label.mousePressEvent = self.on_pause

        layout = QHBoxLayout(self)
        layout.addWidget(self.panel_pause)
        layout.addWidget(self.anim_label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def on_play(self, event):
        if not CONFIG.manager.can_save():
            message = _("画像が表示されていません！")
            caption = _("画像未表示")
            style = QMessageBox.Icon.Warning
            qtlib.post_info(self.window(), message, caption, style)
            return
        qtlib.post_play(self.window())

    def on_pause(self, event):
        qtlib.post_update(self.window(), preview=True)

    def play(self):
        self.panel_pause.hide()
        self.anim_label.show()
        # TODO: 加载并播放GIF动画
        # self.movie = QMovie(str(const.PATH_PLAYING))
        # self.anim_label.setMovie(self.movie)
        # self.movie.start()

    def pause(self):
        self.anim_label.hide()
        self.panel_pause.show()
        # if hasattr(self, 'movie') and self.movie:
        #     self.movie.stop()


# ===== 头部面板 =====
class HeaderPanel(QWidget):
    """头部控制面板"""
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
        self.panel_playing.pause()

    def play(self):
        self.panel_playing.play()

    def set_focus(self, is_focused):
        self.panel_focus.set_focus(is_focused)

# ===== 预览面板 =====
class PreviewPanel(QWidget):
    """预览显示面板"""
    DELAY_UPDATE = 10
    frame_loaded = Signal(object)

    def __init__(self, parent):
        super().__init__(parent)

        self.panel_header = HeaderPanel(self)

        # 预览标签
        self.sbmp_preview = QLabel()
        self.sbmp_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sbmp_preview.setStyleSheet("border: 1px solid gray;")
        self.sbmp_preview.setMinimumSize(*const.DEFAULT_SIZE)

        # 动画标签
        self.anime_preview = QLabel()
        self.anime_preview.hide()

        layout = QVBoxLayout(self)
        layout.addWidget(self.panel_header, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sbmp_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.anime_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        self.pos_start = QPoint(0, 0)
        self.is_dragging = False
        self.thread_loading = None
        self.delay_update = QTimer()
        self.delay_update.setSingleShot(True)
        self.delay_update.timeout.connect(self.start_loading)
        self.is_loading = False

        # 信号连接
        self.frame_loaded.connect(self.show_frame)

        # 鼠标事件
        self.sbmp_preview.mousePressEvent = self.on_left
        self.sbmp_preview.mouseDoubleClickEvent = self.on_left
        self.sbmp_preview.mouseReleaseEvent = self.on_up
        self.sbmp_preview.mouseMoveEvent = self.on_motion
        self.sbmp_preview.setMouseTracking(True)
        self.sbmp_preview.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 键盘事件
        self.sbmp_preview.keyPressEvent = self.on_press

        # 滚轮事件
        self.sbmp_preview.wheelEvent = self.on_wheel

    def update_display(self):
        """更新显示"""
        self.delay_update.start(self.DELAY_UPDATE)
        self.panel_header.update_display()

    def start_loading(self):
        """开始加载"""
        self.thread_loading = threading.Thread(target=self.load_frame, daemon=True)
        self.thread_loading.start()

    def load_frame(self):
        """加载帧（线程）"""
        image_preview = CONFIG.manager.get_preview()
        print(f"[load_frame] image_preview: {image_preview is not None}, size: {image_preview.size if image_preview else None}")
        self.frame_loaded.emit(image_preview)

    def show_frame(self, image_preview):
        """显示帧（主线程）"""
        print(f"[show_frame] image_preview: {image_preview is not None}, size: {image_preview.size if image_preview else None}")
        if image_preview is None:
            return
        pixmap = self.pil_to_qpixmap(image_preview)
        print(f"[show_frame] pixmap is null: {pixmap.isNull()}, size: {pixmap.size()}")
        self.sbmp_preview.setPixmap(pixmap)
        self.sbmp_preview.setFixedSize(pixmap.size())
        self.sbmp_preview.show()
        self.anime_preview.hide()
        qtlib.post_layout(self.window())

    def pil_to_qpixmap(self, pil_image):
        """PIL 转 QPixmap"""
        if pil_image is None:
            return QPixmap()
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888).copy()
        return QPixmap.fromImage(qimage)

    def on_left(self, event):
        """鼠标左键点击"""
        pos = event.position().toPoint()
        pos_np = np.array([pos.x(), pos.y()])
        is_collide = CONFIG.manager.select_by_pos(pos_np, event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if is_collide:
            self.is_dragging = True
            self.pos_start = pos
        qtlib.post_update(self.window(), preview=True, prop=True)

    def on_motion(self, event):
        """鼠标移动"""
        self.sbmp_preview.setFocus()
        if not self.is_dragging:
            return

        pos_cur = event.position().toPoint()
        offset = pos_cur - self.pos_start
        self.pos_start = pos_cur
        CONFIG.manager.add_offset(np.array([offset.x(), offset.y()]))
        qtlib.post_update(self.window(), preview=True, prop=True)

    def on_up(self, event):
        """鼠标释放"""
        self.is_dragging = False

    def on_press(self, event):
        """键盘按键"""
        key = event.key()

        if key == Qt.Key.Key_Tab:
            ix_delta = -1 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            CONFIG.manager.shift_ix_frame(ix_delta)
            qtlib.post_update(self.window(), True, True, True)
            return

        elif key == Qt.Key.Key_Escape:
            CONFIG.manager.switch_marking()
            qtlib.post_update(self.window(), True, True, True)
            return

        if not CONFIG.manager.is_selected():
            return

        # 方向键移动
        direction = {
            Qt.Key.Key_Up: np.array((0, -1)),
            Qt.Key.Key_W: np.array((0, -1)),
            Qt.Key.Key_Down: np.array((0, 1)),
            Qt.Key.Key_S: np.array((0, 1)),
            Qt.Key.Key_Left: np.array((-1, 0)),
            Qt.Key.Key_A: np.array((-1, 0)),
            Qt.Key.Key_Right: np.array((1, 0)),
            Qt.Key.Key_D: np.array((1, 0)),
        }.get(key)

        if direction is None:
            return

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            direction = direction * 5
        CONFIG.manager.add_offset(direction)
        qtlib.post_update(self.window(), preview=True, prop=True)

    def on_wheel(self, event):
        """滚轮事件"""
        if not CONFIG.manager.is_selected():
            return

        delta = event.angleDelta().y()
        rate_angle = 10 if event.modifiers() & Qt.KeyboardModifier.ControlModifier else 1
        angle_delta = -1 if delta < 0 else 1
        CONFIG.manager.add_angle(angle_delta * rate_angle)
        qtlib.post_update(self.window(), preview=True, prop=True)


# ===== 文件列表控件 =====
class FileListCtrl(QListWidget):
    """图像文件列表 - 完整 PySide6 版本"""
    def __init__(self, parent):
        super().__init__(parent)
        self.setIconSize(QSize(48, 48))
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setWordWrap(False)
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)

        self.target_post = parent.window() if hasattr(parent, 'window') else parent
        self.lst_data = []
        self.order_il = []
        self.accept_check = True
        self.dragging = False
        self.ix_from = -1

        self.itemClicked.connect(self.on_item_clicked)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.model().rowsMoved.connect(self.on_rows_moved)
        self.itemChanged.connect(self.on_item_changed)

        self.update_display()

    def update_display(self):
        """更新显示"""
        self.clear()
        self.lst_data = []
        self.order_il = []

        order_file = CONFIG.manager.get_order_file_display()

        for file in order_file:
            self.order_il.append(file.id_file)
            pixmap = self.pil_to_qpixmap(file.icon)
            icon = QIcon(pixmap)

            item = QListWidgetItem(icon, file.label)
            item.setData(Qt.ItemDataRole.UserRole, file.id_file)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if file.visible else Qt.CheckState.Unchecked)

            self.addItem(item)
            self.lst_data.append(file.id_file)

    def pil_to_qpixmap(self, pil_image):
        """PIL 转 QPixmap"""
        if pil_image is None:
            return QPixmap()
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def on_item_clicked(self, item):
        """点击列表项"""
        id_file = item.data(Qt.ItemDataRole.UserRole)
        if id_file:
            CONFIG.manager.select(None, id_file, False)
            qtlib.post_update(self.window(), preview=True, prop=True)

    def on_item_double_clicked(self, item):
        """双击编辑标签"""
        self.editItem(item)

    def on_item_changed(self, item):
        """复选框状态变化"""
        if not self.accept_check:
            return

        id_file = item.data(Qt.ItemDataRole.UserRole)
        if id_file:
            visible = item.checkState() == Qt.CheckState.Checked
            CONFIG.manager.set_file_visible(id_file, visible)
            qtlib.post_update(self.window(), preview=True, component=True)

    def on_rows_moved(self, parent, start, end, destination, row):
        """拖放排序"""
        if start == row:
            return

        id_from = self.lst_data[start]
        id_to = self.lst_data[row]
        CONFIG.manager.sort_file(id_from, id_to)
        qtlib.post_update(self.window(), True, True, True)

    def reset_icon(self):
        """重置图标"""
        self.clear()
        self.lst_data = []
        self.order_il = []

    def contextMenuEvent(self, event):
        """右键菜单"""
        item = self.itemAt(event.pos())
        if not item:
            return

        id_file = item.data(Qt.ItemDataRole.UserRole)
        if id_file:
            menu = menus.ComponentMenu(self.target_post, id_file)
            menu.exec(event.globalPos())

    def keyPressEvent(self, event):
        """键盘事件 - 删除键删除"""
        if event.key() == Qt.Key.Key_Delete:
            item = self.currentItem()
            if item:
                id_file = item.data(Qt.ItemDataRole.UserRole)
                if id_file:
                    CONFIG.manager.remove(id_file)
                    qtlib.post_update(self.window(), True, True, True)
        super().keyPressEvent(event)


# ===== 部件树形控件 =====
class PartsTreeCtrl(QTreeWidget):
    """部件树形结构 - 完整 PySide6 版本"""
    def __init__(self, parent):
        super().__init__(parent)
        self.setHeaderLabel(_("詳細構成"))
        self.setIconSize(QSize(24, 24))
        self.setStyleSheet("QTreeWidget::item { height: 28px; }")
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)

        self.target_post = parent.window() if hasattr(parent, 'window') else parent
        self.order_il = []
        self.item_from = None
        self.accept_label = False
        self.label_prev = ""

        self.itemClicked.connect(self.on_item_clicked)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.itemChanged.connect(self.on_item_changed)

        self.update_display()

    def update_display(self):
        """更新显示"""
        self.clear()
        self.order_il = []

        order_frame = CONFIG.manager.get_order_frame()
        ix_selection = CONFIG.manager.ix_frame
        item_selection = None

        for ix, frame in enumerate(order_frame):
            # 创建帧节点
            frame_item = QTreeWidgetItem(self)
            frame_item.setText(0, _("フレーム【{num}】").format(num=ix + 1))
            frame_item.setData(0, Qt.ItemDataRole.UserRole, ix)
            frame_item.setFlags(frame_item.flags() | Qt.ItemFlag.ItemIsDropEnabled)

            # 添加部件节点
            for parts in frame.get_order_parts_display():
                self.order_il.append(parts.id_parts)

                parts_item = QTreeWidgetItem(frame_item)
                label = parts.label + "　" * (15 - len(parts.label))
                parts_item.setText(0, label)
                parts_item.setData(0, Qt.ItemDataRole.UserRole, parts.id_parts)
                parts_item.setFlags(parts_item.flags() |
                                   Qt.ItemFlag.ItemIsUserCheckable |
                                   Qt.ItemFlag.ItemIsDragEnabled)

                # 设置图标
                pixmap = self.pil_to_qpixmap(parts.icon)
                parts_item.setIcon(0, QIcon(pixmap))

                # 复选框
                parts_item.setCheckState(0, Qt.CheckState.Checked if parts.visible else Qt.CheckState.Unchecked)

            # 展开当前帧
            if ix_selection == ix:
                self.expandItem(frame_item)
                item_selection = frame_item

        # 展开根节点
        self.expandToDepth(0)

        # 选择当前项
        if item_selection:
            self.setCurrentItem(item_selection)

    def pil_to_qpixmap(self, pil_image):
        """PIL 转 QPixmap"""
        if pil_image is None:
            return QPixmap()
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def on_item_clicked(self, item, column):
        """点击树形项"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            return

        # 如果是帧（int类型）
        if isinstance(data, int):
            ix_frame = data
            CONFIG.manager.select(ix_frame, None, False)
        else:
            # 如果是部件
            id_parts = data
            parent = item.parent()
            if parent:
                ix_frame = parent.data(0, Qt.ItemDataRole.UserRole)
                if ix_frame is not None:
                    CONFIG.manager.select(ix_frame, id_parts, False)

        qtlib.post_update(self.window(), preview=True, prop=True)

    def on_item_double_clicked(self, item, column):
        """双击编辑标签"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is None or isinstance(data, int):
            return

        self.accept_label = True
        self.label_prev = item.text(0)
        self.editItem(item, column)

    def on_item_changed(self, item, column):
        """复选框状态变化"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is None or isinstance(data, int):
            return

        id_parts = data
        parent = item.parent()
        if parent:
            ix_frame = parent.data(0, Qt.ItemDataRole.UserRole)
            visible = item.checkState(0) == Qt.CheckState.Checked
            CONFIG.manager.set_parts_visible(id_parts, visible)
            CONFIG.manager.select(ix_frame, id_parts, False)
            qtlib.post_update(self.window(), preview=True, prop=True)

    def dropEvent(self, event):
        """拖放排序"""
        source_item = self.currentItem()
        if not source_item:
            event.ignore()
            return

        # 获取目标位置
        target_item = self.itemAt(event.position().toPoint())
        if not target_item:
            event.ignore()
            return

        source_data = source_item.data(0, Qt.ItemDataRole.UserRole)
        target_data = target_item.data(0, Qt.ItemDataRole.UserRole)

        # 只允许同层级拖放
        if source_item.parent() != target_item.parent():
            event.ignore()
            return

        # 只允许部件拖放（不是帧）
        if isinstance(source_data, int) and isinstance(target_data, int):
            # 获取帧索引
            parent = source_item.parent()
            if parent:
                num_frame = parent.data(0, Qt.ItemDataRole.UserRole)
                if num_frame is not None:
                    CONFIG.manager.sort_parts(num_frame, source_data, target_data)
                    qtlib.post_update(self.window(), True, True, True)
                    event.accept()
                    return

        event.ignore()

    def contextMenuEvent(self, event):
        """右键菜单"""
        item = self.itemAt(event.pos())
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is None or isinstance(data, int):
            return

        id_parts = data
        menu = menus.ComponentMenu(self.target_post, id_parts)
        menu.exec(event.globalPos())

    def keyPressEvent(self, event):
        """键盘事件 - 删除键删除"""
        if event.key() == Qt.Key.Key_Delete:
            item = self.currentItem()
            if item:
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data and not isinstance(data, int):
                    CONFIG.manager.remove(data)
                    qtlib.post_update(self.window(), True, True, True)
        super().keyPressEvent(event)

    def reset_icon(self):
        """重置图标"""
        self.clear()
        self.order_il = []


# ===== 选择查看器面板 =====
class SelectionViewerPanel(QScrollArea):
    """选择图像查看器"""
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
        """更新显示"""
        lst_id_selection = CONFIG.manager.get_selections_id()
        count_selection = len(lst_id_selection)

        if count_selection == 0:
            self.text_selected.show()
            self.text_selected.setText(_("未選択"))
            lst_id_selection.append(None)
        elif count_selection == 1:
            label = CONFIG.manager.get_image(lst_id_selection[0]).label
            self.text_selected.show()
            self.text_selected.setText(label)
        else:
            self.text_selected.hide()

        if set(self.lst_id) == set(lst_id_selection):
            return

        # 更新图标
        for icon, id_exist, id_selection in zip(self.lst_icon, self.lst_id, lst_id_selection):
            if id_exist == id_selection:
                continue

            if id_selection is None:
                icon.set_pil_image(const.BG_UNSELECTED)
                continue

            selection = CONFIG.manager.get_image(id_selection)
            icon.set_pil_image(selection.icon)

        # 添加或删除图标
        num_selection = len(lst_id_selection)
        num_exists = len(self.lst_id)

        if num_selection > num_exists:
            images_selection = CONFIG.manager.get_images_selection()
            for im in images_selection[num_exists:]:
                self.create_icon(im.icon)
        elif num_selection < num_exists:
            for panel in self.lst_icon[num_selection:]:
                panel.deleteLater()
            self.lst_icon = self.lst_icon[:num_selection]

        self.lst_id = lst_id_selection

    def create_icon(self, pil_image):
        """创建图标"""
        panel_bmp = BitmapPanel(self, pil_image=pil_image)
        self.lst_icon.append(panel_bmp)
        self.layout.insertWidget(len(self.lst_icon) - 1, panel_bmp)

    def reset_icon(self):
        """重置图标"""
        for icon in self.lst_icon[1:]:
            icon.deleteLater()
        self.lst_icon = self.lst_icon[:1]
        self.lst_icon[0].set_pil_image(const.BG_UNSELECTED)
        self.lst_id = [None]


# ===== 属性面板 =====
class PropertyPanel(QWidget):
    """属性面板 - 显示和编辑选中图像的属性"""
    def __init__(self, parent):
        super().__init__(parent)
        self.target_post = parent.window() if hasattr(parent, 'window') else parent

        # 创建控件
        self.panel_selection = SelectionViewerPanel(self)

        self.spin_offset_x = QSpinBox()
        self.spin_offset_x.setRange(-250, 250)
        self.spin_offset_x.setValue(0)

        self.spin_offset_y = QSpinBox()
        self.spin_offset_y.setRange(-250, 250)
        self.spin_offset_y.setValue(0)

        self.spin_angle = QSpinBox()
        self.spin_angle.setRange(-360, 360)
        self.spin_angle.setValue(0)

        self.spin_trans = QSpinBox()
        self.spin_trans.setRange(0, 254)
        self.spin_trans.setValue(0)

        self.spin_zoom_x = QDoubleSpinBox()
        self.spin_zoom_x.setRange(0.1, 3.0)
        self.spin_zoom_x.setSingleStep(0.01)
        self.spin_zoom_x.setValue(1.0)

        self.spin_zoom_y = QDoubleSpinBox()
        self.spin_zoom_y.setRange(0.1, 3.0)
        self.spin_zoom_y.setSingleStep(0.01)
        self.spin_zoom_y.setValue(1.0)

        self.combo_blend = QComboBox()
        for mode in const.MODES_BLEND:
            self.combo_blend.addItem(_(mode), mode)
        self.combo_blend.setCurrentIndex(self.combo_blend.findData(const.BlendMode.NONE))


        self.ctrl_color = QPushButton()
        self.ctrl_color.setStyleSheet("background-color: #ff0000;")
        self.ctrl_color.setFixedSize(30, 30)
        self.ctrl_color.clicked.connect(self.on_color_picker)

        self.spin_alpha = QDoubleSpinBox()
        self.spin_alpha.setRange(0.1, 1.0)
        self.spin_alpha.setSingleStep(0.01)
        self.spin_alpha.setValue(0.3)

        self.check_alias = QCheckBox(_("アンチエイリアス"))
        self.check_alias.setTristate(False)

        self.check_flip = QCheckBox(_("左右反転"))
        self.check_flip.setTristate(False)

        # 信号连接
        self.spin_offset_x.valueChanged.connect(lambda: self.on_offset())
        self.spin_offset_y.valueChanged.connect(lambda: self.on_offset())
        self.spin_angle.valueChanged.connect(self.on_angle)
        self.spin_zoom_x.valueChanged.connect(self.on_zoom)
        self.spin_zoom_y.valueChanged.connect(self.on_zoom)
        self.spin_trans.valueChanged.connect(self.on_trans)
        self.combo_blend.currentTextChanged.connect(self.on_blend)
        self.check_alias.stateChanged.connect(self.on_alias)
        self.check_flip.stateChanged.connect(self.on_flip)

        # 布局
        self.setup_layout()
        self.setEnabled(False)

    def setup_layout(self):
        """设置布局"""
        group = QGroupBox(_("パーツプロパティ"))
        layout = QVBoxLayout(group)

        # 选择图像
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel(_("選択中画像:")))
        select_layout.addWidget(self.panel_selection)
        layout.addLayout(select_layout)

        # 属性网格
        grid = QGridLayout()

        # 偏移
        grid.addWidget(QLabel(_("オフセット")), 0, 0)
        offset_x_layout = QHBoxLayout()
        offset_x_layout.addWidget(QLabel("X:"))
        offset_x_layout.addWidget(self.spin_offset_x)
        grid.addLayout(offset_x_layout, 0, 1)
        offset_y_layout = QHBoxLayout()
        offset_y_layout.addWidget(QLabel("Y:"))
        offset_y_layout.addWidget(self.spin_offset_y)
        grid.addLayout(offset_y_layout, 0, 2)
        grid.addWidget(self.check_alias, 0, 3)

        # 角度
        grid.addWidget(QLabel(_("角度")), 1, 0)
        grid.addWidget(self.spin_angle, 1, 1)
        grid.addWidget(QLabel(""), 1, 2)
        grid.addWidget(self.check_flip, 1, 3)

        # 缩放
        grid.addWidget(QLabel(_("拡大率")), 2, 0)
        zoom_x_layout = QHBoxLayout()
        zoom_x_layout.addWidget(QLabel("X:"))
        zoom_x_layout.addWidget(self.spin_zoom_x)
        grid.addLayout(zoom_x_layout, 2, 1)
        zoom_y_layout = QHBoxLayout()
        zoom_y_layout.addWidget(QLabel("Y:"))
        zoom_y_layout.addWidget(self.spin_zoom_y)
        grid.addLayout(zoom_y_layout, 2, 2)
        grid.addWidget(QLabel(""), 2, 3)

        # 透明度
        grid.addWidget(QLabel(_("透過率")), 3, 0)
        grid.addWidget(self.spin_trans, 3, 1)
        grid.addWidget(QLabel(""), 3, 2)
        grid.addWidget(QLabel(""), 3, 3)

        # 颜色混合
        grid.addWidget(QLabel(_("カラーブレンド")), 4, 0)
        grid.addWidget(self.combo_blend, 4, 1)
        grid.addWidget(self.ctrl_color, 4, 2)
        grid.addWidget(self.spin_alpha, 4, 3)

        layout.addLayout(grid)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(group)
        self.setLayout(main_layout)

        # 初始状态
        self.spin_alpha.hide()
        self.ctrl_color.setEnabled(False)

    def on_color_picker(self):
        """颜色选择器"""
        from PySide6.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            self.ctrl_color.setStyleSheet(f"background-color: {color.name()};")
            self.on_blend()

    def on_offset(self):
        """偏移变化"""
        self.panel_selection.setFocus()
        offset = (self.spin_offset_x.value(), self.spin_offset_y.value())
        CONFIG.manager.set_offset(offset)
        qtlib.post_update(self.target_post, preview=True)

    def on_angle(self):
        """角度变化"""
        self.panel_selection.setFocus()
        angle = self.spin_angle.value()
        CONFIG.manager.set_angle(angle)
        qtlib.post_update(self.target_post, preview=True)

    def on_zoom(self):
        """缩放变化"""
        self.panel_selection.setFocus()
        zoom_x = self.spin_zoom_x.value()
        zoom_y = self.spin_zoom_y.value()
        CONFIG.manager.set_zoom(zoom_x, zoom_y)
        qtlib.post_update(self.target_post, preview=True)

    def on_trans(self):
        """透明度变化"""
        self.panel_selection.setFocus()
        transparency = self.spin_trans.value()
        CONFIG.manager.set_transparency(transparency)
        qtlib.post_update(self.target_post, preview=True)

    def on_alias(self):
        """抗锯齿变化"""
        anti_alias = self.check_alias.isChecked()
        CONFIG.manager.set_alias(anti_alias)
        qtlib.post_update(self.target_post, preview=True)

    def on_flip(self):
        """翻转变化"""
        is_flip = self.check_flip.isChecked()
        CONFIG.manager.set_flip(is_flip)
        qtlib.post_update(self.target_post, preview=True)

    def on_blend(self):
        """混合模式变化"""
        self.panel_selection.setFocus()

        mode_blend = self.combo_blend.currentData()
        color_blend = self.ctrl_color.palette().button().color().getRgb()[:3]
        alpha_blend = self.spin_alpha.value()

        CONFIG.manager.set_blend_color(mode_blend, color_blend, alpha_blend)
        qtlib.post_update(self.target_post, preview=True)

        # 更新可见性
        enable = mode_blend != const.BlendMode.NONE
        self.ctrl_color.setEnabled(enable)

        enable_alpha = mode_blend == const.BlendMode.ALPHA
        self.spin_alpha.setVisible(enable_alpha)
        self.spin_alpha.setEnabled(enable_alpha)

    def update_display(self):
        """更新显示"""
        self.panel_selection.update_display()

        # 设置背景颜色
        color_bg = const.COLOR_FILE if CONFIG.manager.selected_file else const.COLOR_PARTS
        self.setStyleSheet(f"background-color: rgb({color_bg[0]}, {color_bg[1]}, {color_bg[2]});")

        selections = CONFIG.manager.get_images_selection()
        if not selections:
            self.setEnabled(False)
        elif len(selections) == 1:
            self.setEnabled(True)
            self.set_properties_single(selections[0])
        else:
            self.setEnabled(True)

    def set_properties_single(self, selection):
        """设置单个属性"""
        offset_x, offset_y = selection.offset
        width, height = CONFIG.manager.size

        self.spin_offset_x.setValue(offset_x)
        self.spin_offset_y.setValue(offset_y)
        self.spin_offset_x.setRange(-width, width)
        self.spin_offset_y.setRange(-height, height)

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

        # 更新可见性
        enable = selection.mode_blend != const.BlendMode.NONE
        self.ctrl_color.setEnabled(enable)

        enable_alpha = selection.mode_blend == const.BlendMode.ALPHA
        self.spin_alpha.setVisible(enable_alpha)
        self.spin_alpha.setEnabled(enable_alpha)

    def reset_icon(self):
        """重置图标"""
        self.panel_selection.reset_icon()


# ===== 缩略图面板 =====
class ThumbnailPanel(QScrollArea):
    """素材缩略图显示面板 - 动态列数"""
    MARGIN = 5
    THUMB_SIZE = (80, 80)
    ICON_SIZE = (100, 100)
    ICON_WIDTH, ICON_HEIGHT = ICON_SIZE
    CAPTION_HEIGHT = 26
    CAPTION_SIZE = (ICON_WIDTH, CAPTION_HEIGHT)
    CELL_WIDTH = ICON_WIDTH + MARGIN * 2
    CELL_HEIGHT = ICON_HEIGHT + CAPTION_HEIGHT + MARGIN * 2

    def __init__(self, parent, path, on_dialog):
        super().__init__(parent)
        self.parent = parent
        self.path = path
        self.on_dialog = on_dialog
        self.errors = []

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.container = QWidget()
        self.container.setStyleSheet("background-color: white;")
        self.setWidget(self.container)

        self.layout = QGridLayout(self.container)
        self.layout.setSpacing(self.MARGIN)
        self.layout.setContentsMargins(self.MARGIN, self.MARGIN, self.MARGIN, self.MARGIN)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._items = []
        self._cols = 4

        self.show_button(path)

    # ===== 数据收集 =====

    def show_button(self, path):
        """收集所有素材，存到 self._items，然后重新布局"""
        if path.is_dir():
            self._items = self._collect_dir(path)
        else:
            self._items = self._collect_frames(path)

        self._cols = self._recalc_cols()
        self._relayout()

    def _collect_dir(self, path_folder):
        lst_path = self.get_lst_path(path_folder)
        items = []
        lst_path_sep = []

        for path in lst_path:
            if self.is_target_separate(path):
                lst_path_sep.append(path)
            else:
                pil_img = self.get_thumb_image(path)
                if pil_img is None:
                    continue
                items.append((path, pil_img, None))

        for path in lst_path_sep:
            for im_sep, path_sep in editor.separate_sprite_sheet(path):
                icon = editor.create_icon(im_sep, self.ICON_SIZE, self.THUMB_SIZE, const.BG_PHOTO)
                frames = [im_sep]
                items.append((path_sep, icon, frames))

        return items

    def _collect_frames(self, path_image):
        frames = editor.get_frames(path_image)
        if not frames:
            message = _("{name}が開けません！").format(name=path_image.name)
            caption = _("ファイルアクセスエラー")
            qtlib.post_info(self.window(), message, caption, QMessageBox.Icon.Critical)
            return []

        items = []
        for ix, frame in enumerate(frames):
            path_frame = path_image.parent / f"{path_image.stem}【{ix + 1}】"
            images_frame = [frame.convert("RGBA")]
            icon = editor.create_icon(images_frame[0], self.ICON_SIZE, self.THUMB_SIZE, const.BG_PHOTO)
            items.append((path_frame, icon, images_frame))
        return items

    # ===== 动态布局 =====

    def _recalc_cols(self):
        """根据 viewport 宽度算列数"""
        width = self.viewport().width()
        if width <= 0:
            return self._cols
        cols = max(1, (width - self.MARGIN) // self.CELL_WIDTH)
        return cols

    def _relayout(self):
        """按当前列数重新布局"""
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = self._cols
        for ix, (path_image, pil_image, frames) in enumerate(self._items):
            row = ix // cols
            col = ix % cols
            widget = self._create_item_widget(path_image, pil_image, frames)
            self.layout.addWidget(widget, row, col)

    def _create_item_widget(self, path_image, pil_image, frames):
        widget = QWidget()
        widget.setFixedSize(self.CELL_WIDTH, self.CELL_HEIGHT)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        btn = QPushButton()
        pixmap = self.pil_to_qpixmap(pil_image)
        btn.setIcon(QIcon(pixmap))
        btn.setIconSize(QSize(*self.ICON_SIZE))
        btn.setToolTip(_(path_image.stem))
        btn.setFixedSize(*self.ICON_SIZE)
        btn.clicked.connect(self.on_click_left(path_image, frames))

        if not path_image.is_dir():
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(self.on_click_right(path_image, frames))

        label = QLabel(_(path_image.stem))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedSize(*self.CAPTION_SIZE)
        label.setWordWrap(True)

        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

        return widget

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._items:
            return
        new_cols = self._recalc_cols()
        if new_cols != self._cols:
            self._cols = new_cols
            self._relayout()

    # ===== 以下不变 =====

    def pil_to_qpixmap(self, pil_image):
        if pil_image is None:
            return QPixmap()
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888).copy()
        return QPixmap.fromImage(qimage)

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

    def is_target_separate(self, path):
        is_collage = path.parent.stem == const.ImageType.COLLAGE
        is_sep = any(word in path.stem for word in const.KEYWORDS_SEPARATE)
        return is_collage and is_sep

    def on_click_left(self, path, frames=None):
        def inner():
            if path.is_dir():
                qtlib.post_select(self.parent, path)
                return
            qtlib.post_append(self.window(), path_image=path, frames=frames)
        return inner

    def on_click_right(self, path, frames):
        def inner(pos):
            menu = menus.AppendMenu(self.parent, path, frames, None)
            menu.exec(self.mapToGlobal(pos))
        return inner


# ===== 图像追加面板 =====
class ImageAppendPanel(QWidget):
    """图像追加面板"""
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

        # 缩略图面板
        self.panel_thumb = ThumbnailPanel(self, path_init, on_dialog)

        # 主布局
        group = QGroupBox(caption)
        layout = QVBoxLayout(group)

        # 按钮行
        btn_layout = QHBoxLayout()
        import_layout = QVBoxLayout()

        # 分类按钮
        for parts in self.ORDER_BTN:
            icon_path = const.FOLDER_WIDGET / f"{parts}.png"
            if icon_path.exists():
                pixmap = QPixmap(str(icon_path))
                btn = QPushButton()
                btn.setIcon(QIcon(pixmap))
                btn.setIconSize(QSize(50, 50))
                btn.setToolTip(parts)
                btn.setFixedSize(54, 54)
                folder_parts = const.FOLDER_MATERIAL / parts
                btn.clicked.connect(self.on_select_btn(folder_parts))
                btn_layout.addWidget(btn)

        # 导入按钮
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

        # 缩略图
        self.thumb_layout = QVBoxLayout()
        self.thumb_layout.addWidget(self.panel_thumb)
        layout.addLayout(self.thumb_layout)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(group)

        # 连接选择信号
        # 使用信号系统
        signals.select.connect(self.on_select_thumb)

    def on_select_btn(self, path_folder):
        """选择分类按钮"""
        def inner():
            self.panel_thumb.deleteLater()
            self.panel_thumb = ThumbnailPanel(self, path_folder, self.on_dialog)
            # 替换缩略图
            for i in reversed(range(self.thumb_layout.count())):
                self.thumb_layout.itemAt(i).widget().deleteLater()
            self.thumb_layout.addWidget(self.panel_thumb)
        return inner

    def on_select_thumb(self, data):
        """选择缩略图"""
        path = data.get('path')
        if path and path.is_dir() and self.exceeded_display_limit(path):
            message = _("選択したフォルダ直下の画像が多すぎます!\n500件以下になるよう減らしてください!")
            caption = _("読込件数オーバー")
            qtlib.post_info(self.window(), message, caption, QMessageBox.Icon.Warning)
            return

        self.panel_thumb.deleteLater()
        self.panel_thumb = ThumbnailPanel(self, path, self.on_dialog)
        for i in reversed(range(self.thumb_layout.count())):
            self.thumb_layout.itemAt(i).widget().deleteLater()
        self.thumb_layout.addWidget(self.panel_thumb)

    def exceeded_display_limit(self, path_folder):
        """检查是否超过显示限制"""
        counter = 0
        for _ in path_folder.iterdir():
            counter += 1
            if counter > self.FILES_DISPLAY_LIMIT:
                return True
        return False

    def on_import(self):
        """导入图像"""
        wildcard = ";;".join([f"{ext.upper().replace('.', '')} files (*{ext})" for ext in const.SUFFIXES_IMAGE])
        path_image = qtlib.select_file(self, _("取り込みたい画像を選択してください。"), wildcard)
        if path_image:
            qtlib.post_append(self.window(), path_image)


# ===== 组件面板 =====
class ComponentPanel(QWidget):
    """组件面板 - 包含文件列表和树形结构"""
    def __init__(self, parent):
        super().__init__(parent)
        self.target_post = parent.window() if hasattr(parent, 'window') else parent

        # 创建标签页
        self.tab_widget = QTabWidget()
        self.page_file = QWidget()
        self.page_parts = QWidget()

        # 文件列表
        self.flc = FileListCtrl(self.page_file)
        file_layout = QVBoxLayout(self.page_file)
        file_layout.addWidget(self.flc)
        self.page_file.setLayout(file_layout)

        # 树形结构
        self.tree = PartsTreeCtrl(self.page_parts)
        parts_layout = QVBoxLayout(self.page_parts)
        parts_layout.addWidget(self.tree)
        self.page_parts.setLayout(parts_layout)

        # 添加到标签页
        self.tab_widget.tabBar().setExpanding(True)
        self.tab_widget.addTab(self.page_file, _("画像一覧"))
        self.tab_widget.addTab(self.page_parts, _("詳細構成"))

        # 主布局
        layout = QVBoxLayout(self)
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

        # 连接标签页切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def update_display(self):
        """更新显示"""
        # 根据选择状态切换标签页
        if CONFIG.manager.selected_file:
            self.tab_widget.setCurrentIndex(0)
        else:
            self.tab_widget.setCurrentIndex(1)

        self.flc.update_display()
        self.tree.update_display()

    def reset_icon(self):
        """重置图标"""
        self.flc.reset_icon()
        self.tree.reset_icon()

    def on_tab_changed(self, index):
        """标签页切换"""
        selected_file = index == 0
        CONFIG.manager.switch_selected_file(selected_file)
        qtlib.post_update(self.window(), preview=True, prop=True)


# ===== 整体属性面板 =====
class CompositePanel(QWidget):
    """整体属性面板 - 控制帧数、大小、滤镜、保存等"""
    def __init__(self, parent):
        super().__init__(parent)
        self.target_post = parent.window() if hasattr(parent, 'window') else parent

        # 创建主组
        group = QGroupBox(_("全体プロパティ"))
        layout = QVBoxLayout(group)

        # ---- 帧数 ----
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

        # ---- 图像大小 ----
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

        # ---- 显示间隔 ----
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

        # 多帧网格
        self.grid_duration = QTableWidget(1, 1)
        self.grid_duration.setHorizontalHeaderLabels([_("【F1】")])
        self.grid_duration.hide()
        self.grid_duration.setMaximumHeight(100)
        duration_layout.addWidget(self.grid_duration)

        layout.addLayout(duration_layout)

        # ---- 滤镜 ----
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

        # ---- 保存 ----
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

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(group)
        self.setLayout(main_layout)

        # ---- 信号连接 ----
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
        """更新显示"""
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

        # 更新网格
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

        # 更新滤镜
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
        with qtlib.progress_context(self.target_post, "保存に失敗しました…", _("保存失敗")):
            is_single = self.radio_single.isChecked()
            CONFIG.manager.save_gif(path_save, is_single)
            self.complete_save(path_save.parent)

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
