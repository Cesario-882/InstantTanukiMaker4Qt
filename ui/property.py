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

"""属性面板：偏移/角度/缩放/透明度/混合模式。"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QGroupBox, QGridLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

import const
from config import CONFIG
import qtlib
from i18n import _
from ui.lists import SelectionViewerPanel


class PropertyPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.target_post = parent.window() if hasattr(parent, 'window') else parent
        self.panel_selection = SelectionViewerPanel(self)

        self.spin_offset_x = QSpinBox(); self.spin_offset_x.setRange(-250, 250)
        self.spin_offset_y = QSpinBox(); self.spin_offset_y.setRange(-250, 250)
        self.spin_angle = QSpinBox(); self.spin_angle.setRange(-360, 360)
        self.spin_trans = QSpinBox(); self.spin_trans.setRange(0, 254)

        self.spin_zoom_x = QDoubleSpinBox(); self.spin_zoom_x.setRange(0.1, 3.0); self.spin_zoom_x.setSingleStep(0.01); self.spin_zoom_x.setValue(1.0)
        self.spin_zoom_y = QDoubleSpinBox(); self.spin_zoom_y.setRange(0.1, 3.0); self.spin_zoom_y.setSingleStep(0.01); self.spin_zoom_y.setValue(1.0)

        self.combo_blend = QComboBox()
        for mode in const.MODES_BLEND: self.combo_blend.addItem(_(mode), mode)
        self.combo_blend.setCurrentIndex(self.combo_blend.findData(const.BlendMode.NONE))

        self.ctrl_color = QPushButton(); self.ctrl_color.setStyleSheet("background-color: #ff0000;"); self.ctrl_color.setFixedSize(30, 30)
        self.ctrl_color.clicked.connect(self.on_color_picker)

        self.spin_alpha = QDoubleSpinBox(); self.spin_alpha.setRange(0.1, 1.0); self.spin_alpha.setSingleStep(0.01); self.spin_alpha.setValue(0.3)

        self.check_alias = QCheckBox(_("アンチエイリアス"))
        self.check_flip = QCheckBox(_("左右反転"))

        self.spin_offset_x.valueChanged.connect(self.on_offset)
        self.spin_offset_y.valueChanged.connect(self.on_offset)
        self.spin_angle.valueChanged.connect(self.on_angle)
        self.spin_zoom_x.valueChanged.connect(self.on_zoom)
        self.spin_zoom_y.valueChanged.connect(self.on_zoom)
        self.spin_trans.valueChanged.connect(self.on_trans)
        self.combo_blend.currentTextChanged.connect(self.on_blend)
        self.check_alias.stateChanged.connect(self.on_alias)
        self.check_flip.stateChanged.connect(self.on_flip)

        self.setup_layout()
        self.setEnabled(False)

    def setup_layout(self):
        group = QGroupBox(_("パーツプロパティ"))
        layout = QVBoxLayout(group)

        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel(_("選択中画像:")))
        select_layout.addWidget(self.panel_selection)
        layout.addLayout(select_layout)

        grid = QGridLayout()
        grid.addWidget(QLabel(_("オフセット")), 0, 0)
        ox = QHBoxLayout(); ox.addWidget(QLabel("X:")); ox.addWidget(self.spin_offset_x); grid.addLayout(ox, 0, 1)
        oy = QHBoxLayout(); oy.addWidget(QLabel("Y:")); oy.addWidget(self.spin_offset_y); grid.addLayout(oy, 0, 2)
        grid.addWidget(self.check_alias, 0, 3)

        grid.addWidget(QLabel(_("角度")), 1, 0); grid.addWidget(self.spin_angle, 1, 1); grid.addWidget(QLabel(""), 1, 2); grid.addWidget(self.check_flip, 1, 3)

        grid.addWidget(QLabel(_("拡大率")), 2, 0)
        zx = QHBoxLayout(); zx.addWidget(QLabel("X:")); zx.addWidget(self.spin_zoom_x); grid.addLayout(zx, 2, 1)
        zy = QHBoxLayout(); zy.addWidget(QLabel("Y:")); zy.addWidget(self.spin_zoom_y); grid.addLayout(zy, 2, 2)
        grid.addWidget(QLabel(""), 2, 3)

        grid.addWidget(QLabel(_("透過率")), 3, 0); grid.addWidget(self.spin_trans, 3, 1); grid.addWidget(QLabel(""), 3, 2); grid.addWidget(QLabel(""), 3, 3)

        grid.addWidget(QLabel(_("カラーブレンド")), 4, 0); grid.addWidget(self.combo_blend, 4, 1); grid.addWidget(self.ctrl_color, 4, 2); grid.addWidget(self.spin_alpha, 4, 3)

        layout.addLayout(grid)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(group)
        self.setLayout(main_layout)

        self.spin_alpha.hide()
        self.ctrl_color.setEnabled(False)

    def on_color_picker(self):
        from PySide6.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            self.ctrl_color.setStyleSheet(f"background-color: {color.name()};")
            self.on_blend()

    def on_offset(self):
        self.panel_selection.setFocus()
        CONFIG.manager.set_offset((self.spin_offset_x.value(), self.spin_offset_y.value()))
        qtlib.post_update(self.target_post, preview=True)

    def on_angle(self):
        self.panel_selection.setFocus()
        CONFIG.manager.set_angle(self.spin_angle.value())
        qtlib.post_update(self.target_post, preview=True)

    def on_zoom(self):
        self.panel_selection.setFocus()
        CONFIG.manager.set_zoom(self.spin_zoom_x.value(), self.spin_zoom_y.value())
        qtlib.post_update(self.target_post, preview=True)

    def on_trans(self):
        self.panel_selection.setFocus()
        CONFIG.manager.set_transparency(self.spin_trans.value())
        qtlib.post_update(self.target_post, preview=True)

    def on_alias(self):
        CONFIG.manager.set_alias(self.check_alias.isChecked())
        qtlib.post_update(self.target_post, preview=True)

    def on_flip(self):
        CONFIG.manager.set_flip(self.check_flip.isChecked())
        qtlib.post_update(self.target_post, preview=True)

    def on_blend(self):
        self.panel_selection.setFocus()
        mode_blend = self.combo_blend.currentData()
        color_blend = self.ctrl_color.palette().button().color().getRgb()[:3]
        alpha_blend = self.spin_alpha.value()
        CONFIG.manager.set_blend_color(mode_blend, color_blend, alpha_blend)
        qtlib.post_update(self.target_post, preview=True)

    def update_display(self):
        self.panel_selection.update_display()
        color_bg = const.COLOR_FILE if CONFIG.manager.selected_file else const.COLOR_PARTS
        self.setStyleSheet(f"background-color: rgb({color_bg[0]}, {color_bg[1]}, {color_bg[2]});")

        selections = CONFIG.manager.get_images_selection()
        if not selections: self.setEnabled(False)
        elif len(selections) == 1: self.setEnabled(True); self.set_properties_single(selections[0])
        else: self.setEnabled(True)

    def set_properties_single(self, selection):
        offset_x, offset_y = selection.offset
        width, height = CONFIG.manager.size
        self.spin_offset_x.setValue(offset_x); self.spin_offset_y.setValue(offset_y)
        self.spin_offset_x.setRange(-width, width); self.spin_offset_y.setRange(-height, height)

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

        enable = selection.mode_blend != const.BlendMode.NONE
        self.ctrl_color.setEnabled(enable)
        enable_alpha = selection.mode_blend == const.BlendMode.ALPHA
        self.spin_alpha.setVisible(enable_alpha)
        self.spin_alpha.setEnabled(enable_alpha)

    def reset_icon(self):
        self.panel_selection.reset_icon()
