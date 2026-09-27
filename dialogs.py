# dialogs.py - PySide6 版本
import numpy as np
from PIL import Image, ImageDraw
import threading
from natsort import os_sorted

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QCheckBox, QComboBox, QSpinBox, QWidget,
    QScrollArea, QListWidget, QListWidgetItem,
    QSizePolicy, QDialogButtonBox, QFrame
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QPixmap, QImage, QIcon

import const
from config import CONFIG
import qtlib
import widgets
import editor
from i18n import _


class ImageSelectDialog(QDialog):
    """图像选择对话框"""
    def __init__(self, parent, caption, id_replace=None):
        super().__init__(parent)
        self.setWindowTitle(caption)
        self.setModal(True)
        self.resize(800, 600)

        self.path_image = None
        self.frames = None
        self.id_replace = id_replace

        # 主布局
        layout = QVBoxLayout(self)

        # 目标面板（如果有 id_replace）
        if self.id_replace:
            target_widget = QWidget()
            target_layout = QHBoxLayout(target_widget)

            image = CONFIG.manager.get_image(self.id_replace)
            # 创建图像显示（需要 widgets.BitmapPanel 支持 PIL Image）
            # 这里暂时用 QLabel 显示
            pixmap = self.pil_to_qpixmap(image.icon)
            label = QLabel()
            label.setPixmap(pixmap)
            label.setFixedSize(pixmap.size())

            target_layout.addWidget(QLabel(_("交换対象:")))
            target_layout.addWidget(label)
            target_layout.addWidget(QLabel(image.label))
            layout.addWidget(target_widget)

        # 图像追加面板
        self.panel_append = widgets.ImageAppendPanel(self, _("画像選択"), CONFIG.dir_dialog, True)
        layout.addWidget(self.panel_append)

        # 连接信号
        # 需要 widgets.ImageAppendPanel 发出信号
        # 暂时使用事件机制

    def pil_to_qpixmap(self, pil_image):
        """将 PIL Image 转换为 QPixmap"""
        if pil_image is None:
            return QPixmap()
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def get_select_image(self):
        return self.path_image, self.frames, self.id_replace

    def on_append(self, path_image, frames=None):
        """处理添加图像"""
        self.path_image = path_image
        self.frames = frames
        CONFIG.dir_dialog = path_image.parent
        self.accept()


class SelectionColorPanel(QScrollArea):
    """颜色选择面板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.lst_icon = []
        self.colors_target = []

        container = QWidget()
        self.layout = QHBoxLayout(container)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        self.setWidget(container)

        width, height = const.ICON_SIZE
        self.setMinimumSize(width + 20, height + 20)
        self.setStyleSheet("background-color: white;")

    def append_color(self, color):
        """添加颜色"""
        color_hsv = editor.convert_rgb2hsv_full(color)
        if color_hsv not in set(self.colors_target):
            self.colors_target.append(color_hsv)
            self.add_icon(color)

    def add_icon(self, color):
        """添加颜色图标"""
        im = Image.new("RGBA", const.ICON_SIZE, color)
        right, bottom = im.size
        ImageDraw.Draw(im).rectangle((0, 0, right - 1, bottom - 1), outline=(0, 0, 0), width=1)

        pixmap = self.pil_to_qpixmap(im)
        label = QLabel()
        label.setPixmap(pixmap)
        label.setFixedSize(pixmap.size())
        label.setStyleSheet("border: 1px solid gray;")
        label.mousePressEvent = lambda e: self.on_remove(label)

        self.layout.addWidget(label)
        self.lst_icon.append(label)

    def pil_to_qpixmap(self, pil_image):
        """将 PIL Image 转换为 QPixmap"""
        if pil_image is None:
            return QPixmap()
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def on_remove(self, label):
        """移除颜色"""
        if label in self.lst_icon:
            ix = self.lst_icon.index(label)
            self.lst_icon.remove(label)
            self.colors_target.pop(ix)
            label.deleteLater()


class SelectColorDialog(QDialog):
    """选择颜色对话框"""
    def __init__(self, parent, path_image, frames):
        super().__init__(parent)
        self.setWindowTitle(_("透過色指定ダイアログ"))
        self.setModal(True)
        self.resize(800, 700)

        self.parent = parent

        # 加载目标图像
        self.im_target = (editor.open_image(path_image).convert("RGBA") if not frames else
                          frames[0].convert("RGBA"))

        if self.im_target.width < const.DEFAULT_WIDTH or self.im_target.height < const.DEFAULT_HEIGHT:
            width = const.DEFAULT_WIDTH if self.im_target.width < const.DEFAULT_WIDTH else self.im_target.width
            height = const.DEFAULT_HEIGHT if self.im_target.height < const.DEFAULT_HEIGHT else self.im_target.height
            size = (width, height)
            im_campus = Image.new("RGBA", size, (0, 0, 0, 0))
            offset = np.array(size) // 2 - np.array(self.im_target.size) // 2
            im_campus.paste(self.im_target, tuple(offset))
            self.im_target = im_campus

        # 主布局
        layout = QVBoxLayout(self)

        # 说明文字
        caption_text = _("色を利用して輪郭の内側を透過します。\n"
                        "画像をクリックして色を選択、選択解除は一覧のアイコンをクリック")
        layout.addWidget(QLabel(caption_text))

        # 图像显示
        self.chess_board = editor.create_chess_board(self.im_target.size, True)
        campus_edit = Image.alpha_composite(self.chess_board.convert("RGBA"), self.im_target)
        pixmap = self.pil_to_qpixmap(campus_edit)

        self.image_label = QLabel()
        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(pixmap.size())
        self.image_label.setStyleSheet("border: 1px solid gray;")
        self.image_label.mousePressEvent = self.on_click
        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 颜色选择区域
        self.panel_selection = SelectionColorPanel()
        layout.addWidget(self.panel_selection)

        # 复选框和按钮
        self.check_face = QCheckBox(_("顔だけ透過"))
        layout.addWidget(self.check_face)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def pil_to_qpixmap(self, pil_image):
        """将 PIL Image 转换为 QPixmap"""
        if pil_image is None:
            return QPixmap()
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def on_click(self, event):
        """点击图像选择颜色"""
        pos = event.position().toPoint()
        x, y = pos.x(), pos.y()
        width, height = self.im_target.size
        if not (0 <= x < width and 0 <= y < height):
            return

        pixel = self.im_target.getpixel((x, y))
        color, alpha = pixel[:-1], pixel[-1]
        if not alpha:
            return

        self.panel_selection.append_color(color)

    def get_colors_target(self):
        """获取选择的颜色"""
        colors_target = self.panel_selection.colors_target
        face_only = self.check_face.isChecked()
        return colors_target, face_only


class ClipperSelectDialog(QDialog):
    """裁剪器选择对话框"""
    def __init__(self, parent, id_image):
        super().__init__(parent)
        self.setWindowTitle(_("クリッパー設定ダイアログ"))
        self.setModal(True)
        self.resize(800, 700)

        self.id_image = id_image
        self.is_file = CONFIG.manager.is_file(id_image)

        # 主布局
        layout = QVBoxLayout(self)

        # 目标图像信息
        image_target = CONFIG.manager.get_image(id_image)
        info_layout = QHBoxLayout()
        pixmap = self.pil_to_qpixmap(image_target.icon)
        label = QLabel()
        label.setPixmap(pixmap)
        label.setFixedSize(pixmap.size())
        info_layout.addWidget(label)
        info_layout.addWidget(QLabel(image_target.label))
        layout.addLayout(info_layout)

        # 列表
        list_layout = QHBoxLayout()

        self.lc_unclipper = QListWidget()
        self.lc_clipper = QListWidget()

        self.lc_unclipper.itemClicked.connect(lambda item: self.on_click(item, self.lc_unclipper))
        self.lc_clipper.itemClicked.connect(lambda item: self.on_click(item, self.lc_clipper))

        list_layout.addWidget(QLabel(_("画像一覧")))
        list_layout.addWidget(self.lc_unclipper)
        list_layout.addWidget(QLabel("⇔"))
        list_layout.addWidget(self.lc_clipper)

        layout.addLayout(list_layout)

        # OK按钮
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok, alignment=Qt.AlignmentFlag.AlignRight)

        self.update_display()

    def pil_to_qpixmap(self, pil_image):
        """将 PIL Image 转换为 QPixmap"""
        if pil_image is None:
            return QPixmap()
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def update_display(self):
        """更新显示"""
        self.lc_unclipper.clear()
        self.lc_clipper.clear()

        image_target = CONFIG.manager.get_image(self.id_image)
        self.lst_clipper = image_target.clippers_id.copy()

        # 获取所有图像
        if self.is_file:
            self.lst_image = CONFIG.manager.get_order_file_display()
        else:
            self.lst_image = CONFIG.manager.get_order_parts_display(self.id_image)

        self.lst_image.remove(image_target)

        lst_id = [image.id_file if self.is_file else image.id_parts for image in self.lst_image]
        self.lst_unclipper = sorted(set(lst_id) - set(self.lst_clipper), key=lst_id.index)

        # 显示未裁剪的图像
        for id_image in self.lst_unclipper:
            image = CONFIG.manager.get_image(id_image)
            item = QListWidgetItem(image.label)
            item.setData(Qt.ItemDataRole.UserRole, id_image)
            self.lc_unclipper.addItem(item)

        # 显示已裁剪的图像
        for id_clipper in self.lst_clipper:
            clipper = CONFIG.manager.get_image(id_clipper)
            item = QListWidgetItem(clipper.label)
            item.setData(Qt.ItemDataRole.UserRole, id_clipper)
            self.lc_clipper.addItem(item)

    def on_click(self, item, list_widget):
        """点击列表项"""
        id_image = item.data(Qt.ItemDataRole.UserRole)

        if list_widget == self.lc_unclipper:
            # 添加到裁剪器
            CONFIG.manager.add_clipper(self.id_image, id_image)
        else:
            # 从裁剪器移除
            CONFIG.manager.remove_clipper(self.id_image, id_image)

        qtlib.post_update(self.parent(), preview=True)
        self.update_display()


class AnimationConverterDialog(QDialog):
    """动画转换对话框"""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(_("アニメーションコンバータ"))
        self.setModal(True)
        self.resize(600, 400)
        self.parent = parent

        # 主布局
        layout = QVBoxLayout(self)

        # 标签页
        from PySide6.QtWidgets import QTabWidget
        self.tab_widget = QTabWidget()

        # 结合标签页
        self.panel_connect = QWidget()
        connect_layout = QVBoxLayout(self.panel_connect)

        connect_layout.addWidget(QLabel(_("選択したフォルダ内のPNGを名前順に結合してアニメーション画像を作成します。")))

        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel(_("表示間隔(ms)")))
        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(20, 1000)
        self.spin_duration.setValue(100)
        duration_layout.addWidget(self.spin_duration)
        connect_layout.addLayout(duration_layout)

        self.combo_connect = QComboBox()
        self.combo_connect.addItems([const.SaveMode.GIF, const.SaveMode.PNG_ANIME])
        connect_layout.addWidget(self.combo_connect)

        self.btn_connect = QPushButton(_("フォルダ選択"))
        self.btn_connect.clicked.connect(self.on_connect)
        connect_layout.addWidget(self.btn_connect)

        self.tab_widget.addTab(self.panel_connect, _("結合"))

        # 分解标签页
        self.panel_separate = QWidget()
        separate_layout = QVBoxLayout(self.panel_separate)

        separate_layout.addWidget(QLabel(_("選択したアニメーション画像をフレーム毎に分解します。\n加えて画像の輪郭毎に分割することもできます。")))

        self.check_parts = QCheckBox(_("輪郭毎に分割"))
        self.check_trim = QCheckBox(_("余白をトリミング"))
        self.check_trim.setEnabled(False)

        omit_layout = QHBoxLayout()
        omit_layout.addWidget(QLabel(_("最低検出サイズ")))
        self.spin_omit = QSpinBox()
        self.spin_omit.setRange(0, 1000)
        self.spin_omit.setValue(10)
        self.spin_omit.setEnabled(False)
        omit_layout.addWidget(self.spin_omit)

        self.check_parts.toggled.connect(self.on_check_parts)

        separate_layout.addWidget(self.check_parts)
        separate_layout.addWidget(self.check_trim)
        separate_layout.addLayout(omit_layout)

        self.btn_separate = QPushButton(_("画像選択"))
        self.btn_separate.clicked.connect(self.on_separate)
        separate_layout.addWidget(self.btn_separate)

        self.tab_widget.addTab(self.panel_separate, _("分解"))

        layout.addWidget(self.tab_widget)

    def on_check_parts(self, checked):
        """切换部件分割选项"""
        self.check_trim.setEnabled(checked)
        self.spin_omit.setEnabled(checked)

    def on_connect(self):
        """连接动画"""
        message = _("結合したい画像が入ったフォルダを選択")
        folder_target = qtlib.select_folder(self, message)
        if not folder_target:
            return

        lst_path = [path_png for path_png in folder_target.glob("*.png")]
        if not lst_path:
            qtlib.show_message(self, _("フォルダ内に画像が見つかりません！"), _("画像未発見エラー"))
            return

        lst_path = os_sorted(lst_path)
        frames = []
        for path_png in lst_path:
            frame = editor.open_image(path_png)
            if not frame:
                message = _("{name}が開けません！").format(name=path_png.name)
                caption = _("ファイルアクセスエラー")
                qtlib.show_message(self, message, caption)
                return
            frames.append(frame.convert("RGBA"))

        mode_save = self.combo_connect.currentText()
        suffix = ".gif" if mode_save == const.SaveMode.GIF else ".png"
        name_file = f"{folder_target.stem}{suffix}"
        wildcard = f"*{suffix}"
        message = _("画像の保存先")
        path_save = qtlib.save_file(self, message, wildcard, name_file)
        if not path_save:
            return

        duration = self.spin_duration.value()
        qtlib.post_start_progress(self.parent, "しばらくお待ちください…", _("アニメーション画像作成中"))
        thread_connect = threading.Thread(target=self.connect_animation,
                                          args=(frames, path_save, duration))
        thread_connect.start()

    def connect_animation(self, frames, path_save, duration):
        """连接动画（线程）"""
        with qtlib.progress_context(self.parent, _("アニメーション画像の作成に失敗しました…"), _("作成失敗")):
            if path_save.suffix == ".gif":
                editor.save_gif(path_save, frames, duration)
            else:
                editor.save_apng(path_save, frames, duration)

            caption = _("作成完了") if frames else _("フォルダ内画像なし")
            message = _("アニメーション画像の作成が完了しました！") if frames else _("フォルダ内に画像がありません！")
            style = QMessageBox.Icon.Information if frames else QMessageBox.Icon.Warning
            qtlib.post_end_progress(self.parent, message, caption, style,
                                    path_open=path_save.parent)

    def on_separate(self):
        """分解动画"""
        message = _("分解したい画像を選択")
        wildcard = "*.gif *.png"
        path_image = qtlib.select_file(self, message, wildcard)
        if not path_image:
            return

        frames = editor.get_frames(path_image)
        if not frames:
            message = _("{name}が開けません！").format(name=path_image.name)
            caption = _("ファイルアクセスエラー")
            qtlib.show_message(self, message, caption)
            return

        folder_save = qtlib.save_file(self, _("分割画像保存"), _("保存先フォルダ|"), path_image.stem)

        sep_parts = self.check_parts.isChecked()
        trim = self.check_trim.isChecked()
        area_omit = self.spin_omit.value()

        qtlib.post_start_progress(self.parent, "しばらくお待ちください…", _("画像分割中"))
        thread_separate = threading.Thread(target=self.separate_animation,
                                           args=(folder_save, frames, sep_parts, trim, area_omit))
        thread_separate.start()

    def separate_animation(self, folder_save, frames, sep_parts, trim, area_omit):
        """分解动画（线程）"""
        with qtlib.progress_context(self.parent, _("画像の分割に失敗しました…"), _("分割失敗")):
            if sep_parts:
                editor.save_png_sequence_contour(folder_save, frames, trim, area_omit)
            else:
                editor.save_png_sequence(folder_save, frames)

            message = _("画像の分割が完了しました！")
            caption = _("分割完了")
            qtlib.post_end_progress(self.parent, message, caption, path_open=folder_save)
