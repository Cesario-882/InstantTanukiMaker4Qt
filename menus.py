import threading
from PySide6.QtWidgets import (
    QMenuBar, QMenu, QWidget, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from config import CONFIG
import dialogs
import editor
import qtlib
from i18n import _


class MenuBar(QMenuBar):
    """主菜单栏"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        # 文件菜单
        menu_file = QMenu(_("ファイル"), self)

        menu_save = QAction(_("プロジェクト保存"), self)
        menu_save.setToolTip(_("現在の作業状況をpkl形式で保存します。"))
        menu_save.triggered.connect(self.on_save)
        menu_file.addAction(menu_save)

        menu_load = QAction(_("プロジェクト読込"), self)
        menu_load.setToolTip(_("pkl形式のファイルから作業状況を読み込みます。"))
        menu_load.triggered.connect(self.on_load)
        menu_file.addAction(menu_load)

        self.addMenu(menu_file)

        # 编辑菜单
        menu_edit = QMenu(_("画像加工"), self)

        menu_convert = QAction(_("アニメーションコンバータ"), self)
        menu_convert.setToolTip(_("アニメーション画像の作成、分解ができます。"))
        menu_convert.triggered.connect(self.on_convert)
        menu_edit.addAction(menu_convert)

        self.addMenu(menu_edit)

    def on_save(self):
        """保存项目"""
        path_save = qtlib.save_file(None, _("プロジェクト保存"), "*.json", _("たぬこらプロジェクト.json"))
        if not path_save:
            return

        qtlib.post_start_progress(self.parent, "少しお待ちください…", _("プロジェクト保存中"))
        thread_save = threading.Thread(target=self.save, args=(path_save,))
        thread_save.start()

    def save(self, path_save):
        """保存项目（线程）"""
        with qtlib.progress_context(self.parent, _("保存に失敗しました…"), _("プロジェクト保存失敗")):
            CONFIG.save_manager(path_save)
            message = _("保存が完了しました！")
            caption = _("プロジェクト保存完了")
            style = QMessageBox.Icon.Information
            qtlib.post_end_progress(self.parent, message, caption, style, path_save.parent)

    def on_load(self):
        """加载项目"""
        message = _("プロジェクトを読み込むと現在の作業状況は失われます！")
        caption = _("読込前の注意")
        qtlib.show_message(None, message, caption, QMessageBox.Icon.Warning)

        path_json = qtlib.select_file(None, _("プロジェクト読込"), "*.json")
        if not path_json:
            return

        qtlib.post_start_progress(self.parent, "少しお待ちください…", _("プロジェクト読込中"))
        thread_load = threading.Thread(target=self.load, args=(path_json,))
        thread_load.start()

    def load(self, path_json):
        """加载项目（线程）"""
        with qtlib.progress_context(self.parent, _("プロジェクトの読み込みに失敗しました..."), _("プロジェクト読込失敗")):
            is_completed, message = CONFIG.load_manager(path_json)
            if is_completed:
                qtlib.post_update(self.parent, True, True, True, reset=True)

            caption = "プロジェクト読込完了" if is_completed else _("プロジェクト読込失敗")
            style = QMessageBox.Icon.Information if is_completed else QMessageBox.Icon.Critical
            qtlib.post_end_progress(self.parent, message, caption, style)

    def on_convert(self):
        """打开动画转换器"""
        dialog = dialogs.AnimationConverterDialog(self.parent)
        dialog.exec()


class AppendMenu(QMenu):
    """右键菜单 - 添加图像"""
    def __init__(self, parent, path, frames, id_replace):
        super().__init__(parent)
        self.parent = parent
        self.path = path
        self.frames = frames
        self.id_replace = id_replace
        self.target_post = parent

        # 透明图像添加
        menu_transparent = QAction(_("透過画像の追加"), self)
        menu_transparent.setToolTip(_("選択した色を透過して一覧に追加します。"))
        menu_transparent.triggered.connect(self.on_transparent)
        self.addAction(menu_transparent)

        if not frames:
            self.addSeparator()

            menu_separate = QAction(_("フレーム分割"), self)
            menu_separate.setToolTip(_("フレームごとに分割して画像追加パネルに表示します。"))
            menu_separate.triggered.connect(self.on_separate)
            self.addAction(menu_separate)

            menu_costume = QAction(_("きぐるみ切り抜き"), self)
            menu_costume.setToolTip(_("きぐるみ用に顔の部分だけ切り抜いて一覧に追加します。"))
            menu_costume.triggered.connect(self.on_costume)
            self.addAction(menu_costume)

    def on_separate(self):
        """分割帧"""
        im = editor.open_image(self.path)
        if not im:
            message = _("{name}が開けません！").format(name=self.path.name)
            caption = _("ファイルアクセスエラー")
            style = QMessageBox.Icon.Critical
            qtlib.post_info(self.target_post, message, caption, style)
            return

        if not getattr(im, "is_animated", False):
            return

        qtlib.post_select(self.target_post, self.path)

    def on_transparent(self):
        """打开透明色选择对话框"""
        dialog = dialogs.SelectColorDialog(self.parent, self.path, self.frames)
        result = dialog.exec()
        if result != QDialog.DialogCode.Accepted:
            return

        colors_target, face_only = dialog.get_colors_target()
        if not colors_target:
            return

        qtlib.post_start_progress(self.target_post, _("しばらくお待ちください…"), _("透過画像作成中"))
        args = (self.path, self.frames, colors_target, face_only, self.id_replace)
        thread = threading.Thread(target=self.create_transparent, args=args)
        thread.start()

    def create_transparent(self, path_image, frames, colors_target, is_face, id_replace):
        """创建透明图像（线程）"""
        with qtlib.progress_context(self.target_post, _("透過画像の作成に失敗しました…"), _("透過画像作成失敗")):
            frames = frames if frames else editor.get_frames(path_image)
            if not frames:
                message = _("{name}が開けません!").format(name=path_image.stem)
                caption = _("ファイルアクセスエラー")
                style = QMessageBox.Icon.Critical
                qtlib.post_end_progress(self.target_post, message=message, caption=caption, style=style)
                return

            frames = editor.make_transparent(frames, colors_target, is_face)
            if frames:
                path_image = path_image.parent / f"{path_image.stem}【透過】{path_image.suffix}"
                qtlib.post_append(self.target_post, path_image, frames, id_replace)

            caption = _("透過画像作成完了") if frames else _("透過画像作成失敗")
            message = _("透過画像の作成が完了しました!") if frames else _("透過画像の作成に失敗しました…")
            style = QMessageBox.Icon.Information if frames else QMessageBox.Icon.Critical
            qtlib.post_end_progress(self.target_post, message=message, caption=caption, style=style)

    def on_costume(self):
        """开始服装裁剪"""
        qtlib.post_start_progress(self.target_post, _("しばらくお待ちください…"), _("きぐるみ顔切り抜き"))
        thread = threading.Thread(target=self.clip_for_costume,
                                  args=(self.path, self.frames, self.id_replace))
        thread.start()

    def clip_for_costume(self, path_image, frames, id_replace):
        """服装裁剪（线程）"""
        with qtlib.progress_context(self.target_post, _("切り抜きに失敗しました…"), _("切り抜き失敗")):
            frames = frames if frames else editor.get_frames(path_image)
            if not frames:
                message = _("{name}が開けません!").format(name=path_image.stem)
                caption = _("ファイルアクセスエラー")
                style = QMessageBox.Icon.Critical
                qtlib.post_end_progress(self.target_post, message=message, caption=caption, style=style)
                return

            frames = editor.clip_for_costume(path_image, frames)
            if frames:
                path_image = path_image.parent / f"{path_image.stem}【きぐるみ】{path_image.suffix}"
                qtlib.post_append(self.target_post, path_image, frames, id_replace)

            caption = _("切り抜き完了") if frames else _("切り抜き失敗")
            message = _("きぐるみ切り抜きが完了しました!") if frames else _("きぐるみ切り抜きに失敗しました…")
            style = QMessageBox.Icon.Information if frames else QMessageBox.Icon.Critical
            qtlib.post_end_progress(self.target_post, message=message, caption=caption, style=style)


class ComponentMenu(QMenu):
    """组件右键菜单"""
    def __init__(self, parent, id_image):
        super().__init__(parent)
        self.parent = parent
        self.id_image = id_image

        menu_replace = QAction(_("交換"), self)
        menu_replace.setToolTip(_("プロパティを引き継いで画像を交換する"))
        menu_replace.triggered.connect(self.on_replace)
        self.addAction(menu_replace)

        menu_clipper = QAction(_("クリッパー設定"), self)
        menu_clipper.setToolTip(_("画像と重なった部分を切り取るクリッパーを設定する。"))
        menu_clipper.triggered.connect(self.on_clipper)
        self.addAction(menu_clipper)

        if CONFIG.manager.is_file(self.id_image):
            self.addSeparator()
            menu_remove = QAction(_("削除"), self)
            menu_remove.setToolTip(_("画像を削除する"))
            menu_remove.triggered.connect(self.on_remove)
            self.addAction(menu_remove)

    def on_replace(self):
        """替换图像"""
        dialog = dialogs.ImageSelectDialog(self.parent, _("画像交換ダイアログ"), self.id_image)
        result = dialog.exec()
        if result != QDialog.DialogCode.Accepted:
            return

        path_image, frames, id_replace = dialog.get_select_image()
        qtlib.post_append(self.parent, path_image, frames, id_replace)

    def on_clipper(self):
        """打开裁剪器设置"""
        dialog = dialogs.ClipperSelectDialog(self.parent, self.id_image)
        dialog.exec()

    def on_remove(self):
        """删除图像"""
        CONFIG.manager.remove(self.id_image)
        qtlib.post_update(self.parent, True, True, True)
