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
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QAction
from PySide6.QtCore import Signal, QObject

import const
from config import CONFIG
import widgets
import menus
import qtlib
from signals import signals
from i18n import _


class MainWindow(QMainWindow):
    """主窗口 - PySide6 版本"""
    LIMIT_DROP = 10

    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("たぬこら"))

        # 进度相关
        self.dial_progress = None
        self.is_progress = False
        self.message = ""
        self.caption = ""
        self.style = QMessageBox.Icon.Information
        self.path_open = None
        self.need_play = False
        self._force_quit = False

        # 设置图标
        if const.PATH_ICON.exists():
            self.setWindowIcon(QIcon(str(const.PATH_ICON)))

        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 主面板
        self.panel = QWidget()
        self.panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.scroll_area.setWidget(self.panel)

        # 创建各个面板
        self.panel_component = widgets.ComponentPanel(self.panel)
        self.panel_preview = widgets.PreviewPanel(self.panel)
        self.panel_property = widgets.PropertyPanel(self.panel)
        self.panel_append = widgets.ImageAppendPanel(self.panel, _("画像追加"))
        self.panel_composite = widgets.CompositePanel(self.panel)

        # 设置布局
        self.setup_layout()

        # 设置菜单栏
        self.menu_bar = menus.MenuBar(self)
        self.setMenuBar(self.menu_bar)

        # 启用拖放
        self.setAcceptDrops(True)

        # 连接信号
        self.connect_signals()

        # 窗口居中
        self.resize(1200, 800)
        self.center_window()

        # 初始更新（显示空棋盘格）
        QTimer.singleShot(0, lambda: qtlib.post_update(self, preview=True, prop=True, component=True))

    def setup_layout(self):
        """设置布局"""
        # 中间部分：预览 + 属性
        sizer_m_inner = QVBoxLayout()
        sizer_m_inner.addWidget(self.panel_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        sizer_m_inner.addWidget(self.panel_property)

        sizer_m = QHBoxLayout()
        sizer_m.addLayout(sizer_m_inner, 1)

        # 右侧部分：追加 + 整体属性
        sizer_r = QVBoxLayout()
        sizer_r.addWidget(self.panel_append)
        sizer_r.addWidget(self.panel_composite)

        # 主布局：左 + 中 + 右
        main_layout = QHBoxLayout(self.panel)
        main_layout.addWidget(self.panel_component)
        main_layout.addStretch(1)
        main_layout.addLayout(sizer_m)
        main_layout.addStretch(1)
        main_layout.addLayout(sizer_r)

        # 将滚动区域添加到中央部件
        central_layout = QVBoxLayout(self.central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.scroll_area)

    def center_window(self):
        """窗口居中"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def connect_signals(self):
        """连接信号"""
        signals.append.connect(self.on_append)
        signals.update.connect(self.on_update)
        signals.layout.connect(self.on_layout)
        signals.info.connect(self.on_info)
        signals.start_progress.connect(self.on_start_progress)
        signals.end_progress.connect(self.on_end_progress)
        signals.play.connect(self.on_play)

    # ===== 拖放处理 =====
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖入事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    path = pathlib.Path(url.toLocalFile())
                    if path.suffix.lower() in const.SUFFIXES_IMAGE:
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """放下事件"""
        if not self.isFocusable():
            event.ignore()
            return

        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return

        file_paths = []
        for url in urls:
            if url.isLocalFile():
                file_paths.append(pathlib.Path(url.toLocalFile()))

        if not file_paths:
            event.ignore()
            return

        # 检查文件数量
        count_files = len(file_paths)
        if count_files > self.LIMIT_DROP:
            message = _("一度にドロップできるファイル数は10件までです！")
            caption = _("ファイルドロップ数オーバー")
            qtlib.post_info(self, message, caption, style=QMessageBox.Icon.Warning)
            event.ignore()
            return

        # 处理每个文件
        for path_drop in file_paths:
            if path_drop.suffix.lower() in const.SUFFIXES_IMAGE:
                qtlib.post_append(self, path_drop)
            else:
                message = _("{name}は画像追加の対象外です!\n追加できる画像の拡張子はjpg,png,gifのみです！").format(name=path_drop.name)
                caption = _("対象外ファイル")
                qtlib.post_info(self, message, caption, style=QMessageBox.Icon.Warning)

        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """拖出事件"""
        pass

    # ===== 事件处理 =====
    def on_append(self, data):
        """添加图像"""
        path_image = data.get('path_image')
        frames = data.get('frames')
        id_replace = data.get('id_replace')

        if id_replace:
            is_completed = CONFIG.manager.replace(path_image, id_replace, frames)
        else:
            is_completed = CONFIG.manager.append(path_image, frames)

        if not is_completed:
            message = _("{name}が開けません！").format(name=path_image.stem)
            caption = _("ファイルアクセスエラー")
            qtlib.show_message(None, message, caption, QMessageBox.Icon.Critical)
            return

        qtlib.post_update(self, True, True, True)

    def on_update(self, params):
        """更新界面"""
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
        """布局更新"""
        pass

    def on_info(self, data):
        """显示信息"""
        qtlib.show_message(
            self,
            data.get('message'),
            data.get('caption'),
            data.get('style', QMessageBox.Icon.Information)
        )

    def on_start_progress(self, data):
        """开始进度"""
        self.is_progress = True
        self.dial_progress = qtlib.ProgressDialog(
            data.get('caption', ''),
            data.get('message', ''),
            self
        )
        self.dial_progress.Pulse()
        if not self.is_progress:
            self.finish_progress()

    def on_end_progress(self, data):
        """结束进度"""
        self.message = data.get('message', '')
        self.caption = data.get('caption', '')
        self.style = data.get('style', QMessageBox.Icon.Information)
        self.path_open = data.get('path_open')
        self.need_play = data.get('need_play', False)
        self.is_progress = False
        self.finish_progress()

    def finish_progress(self):
        """完成进度"""
        if not self.dial_progress:
            return

        self.dial_progress.Destroy()
        self.dial_progress = None

        self.raise_()
        self.activateWindow()

        if self.message:
            qtlib.show_message(self, self.message, self.caption, self.style)

        if self.path_open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path_open)))

        if self.need_play:
            self.panel_preview.show_animation()

    def on_play(self):
        """播放预览"""
        qtlib.post_start_progress(self, _("少しお待ちください…"), _("プレビュー作成中"))
        is_single = self.panel_composite.radio_single.isChecked()
        thread_preview = threading.Thread(target=self.save_preview, args=(is_single,), daemon=True)
        thread_preview.start()

    def save_preview(self, is_single):
        """保存预览（线程）"""
        with qtlib.progress_context(self, _("プレビューの作成に失敗しました…"), _("プレビュー作成失敗")):
            CONFIG.manager.save_preview(is_single)
            qtlib.post_end_progress(self, need_play=True)

    def closeEvent(self, event):
        """关闭事件"""
        if self._force_quit:
            event.accept()
            return
        message = _("終了してよろしいですか？")
        caption = _("終了確認")
        reply = qtlib.show_question(self, message, caption)
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    """主函数"""
    import signal

    app = QApplication(sys.argv)
    app.setApplicationName(_("たぬこら"))

    const.FONT_FAMILY = const.register_fonts()

    window = MainWindow()

    # ===== 信号处理 =====
    def _on_signal(signum, frame):
        print(f"\n[signal] received {signum}, shutting down...", flush=True)
        window._force_quit = True   # ← 信号来时设 True
        window.close()              # ← 触发 closeEvent，看到 True 直接退
        app.quit()

    signal.signal(signal.SIGINT, _on_signal)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, _on_signal)

    # Qt 事件循环里的 Python 信号心跳
    signal_timer = QTimer()
    signal_timer.start(200)
    signal_timer.timeout.connect(lambda: None)

    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
