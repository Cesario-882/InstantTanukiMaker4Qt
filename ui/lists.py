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

"""列表类组件：文件列表、部件树、选中项查看器。"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QScrollArea,
    QListView, QTreeView,
)
from PySide6.QtCore import (
    Qt, QSize, QModelIndex, QAbstractListModel,
)
from PySide6.QtGui import QPixmap, QIcon, QStandardItemModel, QStandardItem

import const
from config import CONFIG
import qtlib
from signals import signals
from i18n import _
from ui.base import BitmapPanel


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
        import menus
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
        import menus
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
