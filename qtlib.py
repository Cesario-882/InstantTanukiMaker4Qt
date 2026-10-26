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

import os
import sys
import pathlib
import subprocess
from contextlib import contextmanager

from PySide6.QtWidgets import QMessageBox, QFileDialog, QProgressDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

import const
from i18n import _
from signals import signals


# ===== 对话框函数 =====

def show_message(parent, message, caption, style=QMessageBox.Icon.Information):
    """显示消息对话框"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(caption)
    msg_box.setText(message)
    msg_box.setIcon(style)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    return msg_box.exec()


def show_question(parent, message, caption) -> bool:
    """显示问答对话框，明确返回 True/False"""
    reply = QMessageBox.question(
        parent, caption, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes


def _to_filter(wildcard) -> str:
    """将各种格式的通配符转为 Qt 标准 filter 字符串"""
    if not wildcard:
        return "All files (*.*)"
    if isinstance(wildcard, (list, tuple)):
        # 列表格式：[".jpg", ".png"]
        patterns = [w if w.startswith("*") else f"*{w}" for w in wildcard]
        return f"Files ({' '.join(patterns)});;All files (*.*)"
    if isinstance(wildcard, str):
        if "(" in wildcard:
            # 已经是合法的 Qt filter 格式
            return wildcard
        # 字符串格式："*.json;*.txt" 或 "*.json"
        exts = [w.strip() for w in wildcard.split(";") if w.strip()]
        labels = ";".join(e.upper().replace("*", "").replace(".", "") for e in exts)
        return f"{labels} files ({wildcard});;All files (*.*)"
    return "All files (*.*)"


def select_file(parent, caption, wildcard, multiple=False) -> pathlib.Path | list | None:
    """选择文件，统一返回 Path、Path 列表 或 None"""
    filter_str = _to_filter(wildcard)
    default_dir = str(const.FOLDER_MATERIAL) if const.FOLDER_MATERIAL.exists() else ""

    if multiple:
        files, _ = QFileDialog.getOpenFileNames(parent, caption, default_dir, filter_str)
        if files:
            return [pathlib.Path(f) for f in files]
    else:
        file, _ = QFileDialog.getOpenFileName(parent, caption, default_dir, filter_str)
        if file:
            return pathlib.Path(file)
    return None


def select_folder(parent, message) -> pathlib.Path | None:
    """选择文件夹"""
    folder = QFileDialog.getExistingDirectory(parent, message)
    if folder:
        return pathlib.Path(folder)
    return None


def save_file(parent, caption, wildcard, name_save) -> pathlib.Path | None:
    """保存文件对话框"""
    filter_str = _to_filter(wildcard)
    file, _ = QFileDialog.getSaveFileName(parent, caption, name_save, filter_str)
    if file:
        return pathlib.Path(file)
    return None


# ===== 事件发送函数 =====

def post_update(target_post, preview=False, prop=False, component=False, reset=False):
    signals.update.emit({
        'preview': preview, 'property': prop, 'component': component, 'reset': reset
    })


def post_append(target_post, path_image, frames=None, id_replace=None):
    signals.append.emit({'path_image': path_image, 'frames': frames, 'id_replace': id_replace})


def post_info(target_post, message, caption, style=QMessageBox.Icon.Information):
    signals.info.emit({'message': message, 'caption': caption, 'style': style})


def post_start_progress(target_post, message, caption):
    signals.start_progress.emit({'message': message, 'caption': caption})


def post_end_progress(target_post, message="", caption="",
                      style=QMessageBox.Icon.Information,
                      path_open=None, need_play=False):
    signals.end_progress.emit({
        'message': message, 'caption': caption, 'style': style,
        'path_open': path_open, 'need_play': need_play
    })


def post_play(target_post):
    signals.play.emit()


def post_layout(target_post):
    signals.layout.emit()


def post_select(target_post, path):
    signals.select.emit({'path': path})


# ===== 进度对话框生命周期 =====

@contextmanager
def progress_context(target_post, message, caption):
    """进度对话框生命周期管理器：自动处理开始、异常、结束"""
    post_start_progress(target_post, message, caption)
    try:
        yield
    except Exception as e:
        post_end_progress(target_post, f"{message}\n{e}", caption, QMessageBox.Icon.Critical)
        raise
    else:
        post_end_progress(target_post, message, caption)


class ProgressDialog:
    """进度对话框封装"""
    def __init__(self, title, message, parent=None):
        self.dialog = QProgressDialog(message, None, 0, 0, parent)
        self.dialog.setWindowTitle(title)
        self.dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.dialog.setMinimumDuration(0)
        self.dialog.setAutoClose(True)
        self.dialog.setAutoReset(True)
        self.dialog.setCancelButton(None)

    def pulse(self):
        """无实际作用（0,0 本身就是忙状态），留作语义兼容"""
        pass

    def destroy(self):
        """彻底销毁对话框，防止悬空指针"""
        if self.dialog is not None:
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None

    def show(self):
        if self.dialog is not None:
            self.dialog.show()
            self.dialog.raise_()
            self.dialog.activateWindow()


# ===== 系统文件管理器调用 =====

def open_folder(path):
    """调用系统默认文件管理器打开指定路径，净化环境变量"""
    path = pathlib.Path(path)
    if not path.exists():
        return

    try:
        if sys.platform == "win32":
            os.startfile(path)
        else:
            # 复制环境变量，剥离 Python 注入的 Qt 路径，防止子进程加载错误库
            clean_env = os.environ.copy()
            for var in ["LD_LIBRARY_PATH", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"]:
                clean_env.pop(var, None)

            subprocess.Popen(
                ["xdg-open", str(path)],
                env=clean_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
    except Exception as e:
        error_msg = _("ファイルマネージャを開けませんでした。\n{err}").format(err=str(e))
        show_message(None, error_msg, _("エラー"), QMessageBox.Icon.Warning)
