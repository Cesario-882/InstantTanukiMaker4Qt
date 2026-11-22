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

"""向后兼容桥接层。实际实现已拆分至 ui/ 包，此处仅做 re-export。

新代码请直接 `from ui import ...`；本文件保留是为了不破坏既有
`from widgets import XxxPanel` 的调用点。
"""

from ui.base import (
    ThumbnailSignals,
    ThumbnailWorker,
    BitmapPanel,
    FocusDisplayPanel,
    FrameNumberDisplayPanel,
    SelectionMarkerStatusPanel,
    PlayingStatusPanel,
    HeaderPanel,
)
from ui.preview import PreviewPanel
from ui.lists import (
    FileListModel,
    FileListCtrl,
    PartsTreeCtrl,
    SelectionViewerPanel,
)
from ui.property import PropertyPanel
from ui.panels import (
    ThumbnailPanel,
    ImageAppendPanel,
    ComponentPanel,
    CompositePanel,
)

__all__ = [
    "ThumbnailSignals",
    "ThumbnailWorker",
    "BitmapPanel",
    "FocusDisplayPanel",
    "FrameNumberDisplayPanel",
    "SelectionMarkerStatusPanel",
    "PlayingStatusPanel",
    "HeaderPanel",
    "PreviewPanel",
    "FileListModel",
    "FileListCtrl",
    "PartsTreeCtrl",
    "SelectionViewerPanel",
    "PropertyPanel",
    "ThumbnailPanel",
    "ImageAppendPanel",
    "ComponentPanel",
    "CompositePanel",
]