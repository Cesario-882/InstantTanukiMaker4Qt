#!/usr/bin/env python
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

import sys
import os
import pathlib
import threading
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QStatusBar, QMessageBox, QProgressDialog,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QUrl, QMimeData, QSocketNotifier
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QAction, QDesktopServices

import const
from config import CONFIG
import widgets
import menus
import qtlib
from signals import signals
from i18n import _


class MainWindow(QMainWindow):
    LIMIT_DROP = 10

    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("たぬこら"))

        self.dial_progress = None
        self.is_progress = False
        self.message = ""
        self.caption = ""
        self.style = QMessageBox.Icon.Information
        self.path_open = None
        self.need_play = False
        self._force_quit = False

        if const.PATH_ICON.exists():
            self.setWindowIcon(QIcon(str(const.PATH_ICON)))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.panel = QWidget()
        self.panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.scroll_area.setWidget(self.panel)

        self.panel_component = widgets.ComponentPanel(self.panel)
        self.panel_preview = widgets.PreviewPanel(self.panel)
        self.panel_property = widgets.PropertyPanel(self.panel)
        self.panel_append = widgets.ImageAppendPanel(self.panel, _("画像追加"))
        self.panel_composite = widgets.CompositePanel(self.panel)

        self.setup_layout()

        self.menu_bar = menus.MenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.setAcceptDrops(True)
        self.connect_signals()

        self.resize(1200, 800)
        self.center_window()

        QTimer.singleShot(0, lambda: qtlib.post_update(self, preview=True, prop=True, component=True))

    def setup_layout(self):
        sizer_m_inner = QVBoxLayout()
        sizer_m_inner.addWidget(self.panel_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        sizer_m_inner.addWidget(self.panel_property)

        sizer_m = QHBoxLayout()
        sizer_m.addLayout(sizer_m_inner, 1)

        sizer_r = QVBoxLayout()
        sizer_r.addWidget(self.panel_append)
        sizer_r.addWidget(self.panel_composite)

        main_layout = QHBoxLayout(self.panel)
        main_layout.addWidget(self.panel_component)
        main_layout.addStretch(1)
        main_layout.addLayout(sizer_m)
        main_layout.addStretch(1)
        main_layout.addLayout(sizer_r)

        central_layout = QVBoxLayout(self.central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.scroll_area)

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def connect_signals(self):
        signals.append.connect(self.on_append)
        signals.update.connect(self.on_update)
        signals.layout.connect(self.on_layout)
        signals.info.connect(self.on_info)
        signals.start_progress.connect(self.on_start_progress)
        signals.end_progress.connect(self.on_end_progress)
        signals.play.connect(self.on_play)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and pathlib.Path(url.toLocalFile()).suffix.lower() in const.SUFFIXES_IMAGE:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if not self.isFocusable():
            event.ignore()
            return
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return

        file_paths = [pathlib.Path(url.toLocalFile()) for url in urls if url.isLocalFile()]
        if not file_paths:
            event.ignore()
            return

        if len(file_paths) > self.LIMIT_DROP:
            qtlib.post_info(self, _("一度にドロップできるファイル数は10件までです！"), _("ファイルドロップ数オーバー"), style=QMessageBox.Icon.Warning)
            event.ignore()
            return

        for path_drop in file_paths:
            if path_drop.suffix.lower() in const.SUFFIXES_IMAGE:
                qtlib.post_append(self, path_drop)
            else:
                message = _("{name}は画像追加の対象外です!\n追加できる画像の拡張子はjpg,png,gifのみです！").format(name=path_drop.name)
                qtlib.post_info(self, message, _("対象外ファイル"), style=QMessageBox.Icon.Warning)

        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        pass

    def on_append(self, data):
        path_image = data.get('path_image')
        frames = data.get('frames')
        id_replace = data.get('id_replace')

        if id_replace:
            is_completed = CONFIG.manager.replace(path_image, id_replace, frames)
        else:
            is_completed = CONFIG.manager.append(path_image, frames)

        if not is_completed:
            qtlib.show_message(None, _("{name}が開けません！").format(name=path_image.stem), _("ファイルアクセスエラー"), QMessageBox.Icon.Critical)
            return
        qtlib.post_update(self, True, True, True)

    def on_update(self, params):
        if params.get('reset'):
            self.panel_component.reset_icon()
            self.panel_property.reset_icon()
        if params.get('preview'):
            self.panel_preview.update_display()
        if params.get('property'):
            self.panel_property.update_display()
        if params.get('component'):
            self.panel_component.update_display()
            self.panel_composite.update_display()

    def on_layout(self):
        pass

    def on_info(self, data):
        qtlib.show_message(self, data.get('message'), data.get('caption'), data.get('style', QMessageBox.Icon.Information))

    def on_start_progress(self, data):
        self.is_progress = True
        self.dial_progress = qtlib.ProgressDialog(data.get('caption', ''), data.get('message', ''), self)
        self.dial_progress.show()
        if not self.is_progress:
            self.finish_progress()

    def on_end_progress(self, data):
        self.message = data.get('message', '')
        self.caption = data.get('caption', '')
        self.style = data.get('style', QMessageBox.Icon.Information)
        self.path_open = data.get('path_open')
        self.need_play = data.get('need_play', False)
        self.is_progress = False
        self.finish_progress()

    def finish_progress(self):
        if not self.dial_progress:
            return
        self.dial_progress.destroy()
        self.dial_progress = None
        self.raise_()
        self.activateWindow()

        if self.message:
            qtlib.show_message(self, self.message, self.caption, self.style)
            self.message = ""
        if self.path_open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path_open)))
            self.path_open = None
        if self.need_play:
            self.panel_preview.show_animation()
            self.need_play = False

    def on_play(self):
        qtlib.post_start_progress(self, _("少しお待ちください…"), _("プレビュー作成中"))
        is_single = self.panel_composite.radio_single.isChecked()
        threading.Thread(target=self.save_preview, args=(is_single,), daemon=True).start()

    def save_preview(self, is_single):
        try:
            CONFIG.manager.save_preview(is_single)
            qtlib.post_end_progress(self, need_play=True)
        except Exception as e:
            qtlib.post_end_progress(self, message=str(e), style=QMessageBox.Icon.Critical)

    def request_force_quit(self):
        self._force_quit = True
        self.close()
        QApplication.instance().quit()

    def closeEvent(self, event):
        if self._force_quit:
            event.accept()
            return
        if qtlib.show_question(self, _("終了してよろしいですか？"), _("終了確認")):
            event.accept()
        else:
            event.ignore()


def main():
    import signal
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(_("たぬこら"))

    import i18n
    i18n.load_language()
    const.FONT_FAMILY = const.register_fonts()

    window = MainWindow()

    def _on_signal(signum, frame):
        print(f"\n[signal] received {signum}, shutting down...", flush=True)
        window.request_force_quit()
        app.quit()
        os._exit(1)

    def _excepthook(exc_type, exc_value, exc_traceback):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        print("\n[unhandled exception] Force quitting...", flush=True)
        _on_signal(-1, None)

    sys.excepthook = _excepthook
    signal.signal(signal.SIGINT, _on_signal)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, _on_signal)

    signal_timer = QTimer()
    signal_timer.start(200)
    signal_timer.timeout.connect(lambda: None)

    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
