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

"""功能面板：缩略图选择、图像追加、组件树、合成设置。"""

from pathlib import Path
import threading

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QGroupBox, QTabWidget, QMessageBox,
    QCheckBox, QSpinBox, QRadioButton, QComboBox, QTableWidget, QTableWidgetItem,
)
from PySide6.QtCore import Qt, QSize, QThreadPool, Slot
from PySide6.QtGui import QIcon, QPixmap

import const
from config import CONFIG
import editor
import qtlib
from signals import signals
from i18n import _, display
from ui.base import ThumbnailWorker
from ui.lists import FileListCtrl, PartsTreeCtrl


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
                entries = sorted([e for e in path_image.iterdir() if e.is_dir() or e.is_file()])
                for entry in entries[:15]:
                    lines.append("    " + display(entry.stem))

                if len(entries) > 15:
                    lines.append(f"    ... 以及其他 {len(entries) - 15} 个素材")
            except OSError:
                pass

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
        import menus
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
