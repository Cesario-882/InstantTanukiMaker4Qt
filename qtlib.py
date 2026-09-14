import pathlib
from contextlib import contextmanager
from PySide6.QtWidgets import (
    QMessageBox, QFileDialog, QProgressDialog, QWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon

import const
from signals import signals  # 假设你创建了 signals.py


# ===== 对话框函数 =====

def show_message(parent, message, caption, style=QMessageBox.Icon.Information):
    """显示消息对话框"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(caption)
    msg_box.setText(message)
    msg_box.setIcon(style)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    return msg_box.exec()


def show_question(parent, message, caption):
    """显示问答对话框（Yes/No）"""
    reply = QMessageBox.question(
        parent, caption, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    return reply


def select_file(parent, caption, wildcard, multiple=False):
    """选择文件"""
    # 转换通配符格式：*.json -> JSON files (*.json)
    if wildcard and not wildcard.startswith("*"):
        # 如果通配符是 "*.json"，转换为 "JSON files (*.json)"
        ext = wildcard.replace("*", "")
        filter_str = f"{ext.upper().replace('.', '')} files ({wildcard})"
    else:
        filter_str = wildcard or "All files (*.*)"

    if multiple:
        files, _ = QFileDialog.getOpenFileNames(
            parent, caption, "", filter_str
        )
        if files:
            return [pathlib.Path(f) for f in files]
    else:
        file, _ = QFileDialog.getOpenFileName(
            parent, caption, "", filter_str
        )
        if file:
            return pathlib.Path(file)
    return False


def select_folder(parent, message):
    """选择文件夹"""
    folder = QFileDialog.getExistingDirectory(parent, message)
    if folder:
        return pathlib.Path(folder)
    return False


def save_file(parent, caption, wildcard, name_save):
    """保存文件对话框"""
    # 转换通配符格式
    if wildcard and not wildcard.startswith("*"):
        ext = wildcard.replace("*", "")
        filter_str = f"{ext.upper().replace('.', '')} files ({wildcard})"
    else:
        filter_str = wildcard or "All files (*.*)"

    file, _ = QFileDialog.getSaveFileName(
        parent, caption, name_save, filter_str
    )
    if file:
        return pathlib.Path(file)
    return False


# ===== 事件发送函数（使用信号系统） =====

def post_update(target_post, preview=False, prop=False, component=False, reset=False):
    """发送更新信号"""
    signals.update.emit({
        'preview': preview,
        'property': prop,
        'component': component,
        'reset': reset
    })


def post_append(target_post, path_image, frames=None, id_replace=None):
    """发送添加图像信号"""
    signals.append.emit({
        'path_image': path_image,
        'frames': frames,
        'id_replace': id_replace
    })


def post_info(target_post, message, caption, style=QMessageBox.Icon.Information):
    """发送信息信号"""
    signals.info.emit({
        'message': message,
        'caption': caption,
        'style': style
    })


def post_start_progress(target_post, message, caption):
    """发送开始进度信号"""
    signals.start_progress.emit({
        'message': message,
        'caption': caption
    })


def post_end_progress(target_post, message="", caption="",
                      style=QMessageBox.Icon.Information,
                      path_open=None, need_play=False):
    """发送结束进度信号"""
    signals.end_progress.emit({
        'message': message,
        'caption': caption,
        'style': style,
        'path_open': path_open,
        'need_play': need_play
    })


def post_play(target_post):
    """发送播放信号"""
    signals.play.emit()


def post_layout(target_post):
    """发送布局更新信号"""
    signals.layout.emit()


def post_select(target_post, path):
    """发送选择信号"""
    signals.select.emit({
        'path': path
    })


# ===== 进度对话框上下文管理器 =====

@contextmanager
def progress_context(target_post, message, caption):
    """进度对话框上下文管理器"""
    try:
        yield
    except Exception as e:
        message = message + f"\n{e}"
        post_end_progress(target_post, message, caption, QMessageBox.Icon.Critical)
        raise


# ===== 进度对话框类 =====

class ProgressDialog:
    """PySide6 版本的进度对话框"""
    def __init__(self, title, message, parent=None):
        # 创建进度对话框
        self.dialog = QProgressDialog(message, None, 0, 0, parent)
        self.dialog.setWindowTitle(title)
        self.dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.dialog.setMinimumDuration(0)
        self.dialog.setAutoClose(True)
        self.dialog.setAutoReset(True)
        # 移除取消按钮（或设置为 None）
        self.dialog.setCancelButton(None)

    def Pulse(self):
        """脉冲进度（不确定进度）"""
        # 设置一个非零值显示进度条动画
        self.dialog.setValue(1)

    def Destroy(self):
        """关闭对话框"""
        self.dialog.close()
        self.dialog.deleteLater()

    def Update(self, value, new_label=None):
        """更新进度值"""
        self.dialog.setValue(value)
        if new_label:
            self.dialog.setLabelText(new_label)
        return True, value

    def Raise(self):
        """将对话框提到前面"""
        self.dialog.raise_()
        self.dialog.activateWindow()

    def Show(self):
        """显示对话框"""
        self.dialog.show()
