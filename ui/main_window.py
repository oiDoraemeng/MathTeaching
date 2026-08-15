"""解析几何课程的 PySide6 主窗口。"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QSlider, QVBoxLayout, QWidget,
)
from pyvistaqt import QtInteractor

from models.parameters import HyperboloidParameters
from rendering.scene import build_scene


class ParameterControl(QWidget):
    """带精确读数的滑块行。

    UI 控件说明：
    - 滑块内部范围：1 ~ 300（对应 0.01 ~ 3.0），拖动步长 0.01
    - 显示/参数精度：0.01（支持精确输入/显示）
    - `value` 属性返回实际的浮点值，用于构造 `HyperboloidParameters`。
    """

    def __init__(self, name: str, value: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        # 滑块范围：1 ~ 300（对应 0.01 ~ 3.0），拖动步长 0.01
        self.slider.setRange(1, 300) 
        # 设置初始值（四舍五入到 0.01 精度）
        self.slider.setValue(round(value * 100))
        # 将界面滑块的整数值映射到浮点参数（除以 100）。
        self.value_label = QLabel()
        self.value_label.setMinimumWidth(42)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.name = name
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.value_label)
        self.slider.valueChanged.connect(self._update_label)
        self._update_label(self.slider.value())

    @property
    def value(self) -> float:
        """返回滑块对应的浮点参数值（例如 145 -> 1.45）。"""
        return self.slider.value() / 100.0

    def _update_label(self, raw: int) -> None:
        self.value_label.setText(f"{raw / 100:.2f}")


class MainWindow(QMainWindow):
    """主窗口：包含侧边栏控制与 PyVista 渲染区的组合窗口。"""
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Math3D Teaching | 双叶双曲面")
        self.resize(1320, 820)
        self._build_ui()
        self._render_scene()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())

        self.plotter = QtInteractor(root)
        self.plotter.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.plotter.interactor, 1)
        self.setCentralWidget(root)

    def _build_sidebar(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("sidebar")
        panel.setFixedWidth(294)
        panel.setStyleSheet("""
            #sidebar { background: #ffffff; border-right: 1px solid #dde1e8; }
            QLabel { color: #29313d; font-size: 13px; }
            QPushButton { background: #f0ecfb; color: #4d397e; border: 1px solid #d6cdef; border-radius: 5px; padding: 9px; font-weight: 600; }
            QPushButton:hover { background: #e5ddf8; }
            QPushButton:checked { background: #8363c4; color: white; border-color: #8363c4; }
            QSlider::groove:horizontal { height: 5px; background: #e2e5eb; border-radius: 2px; }
            QSlider::handle:horizontal { width: 15px; margin: -5px 0; border-radius: 7px; background: #8264c4; }
            QSlider::sub-page:horizontal { background: #b9a5e3; border-radius: 2px; }
        """)
        column = QVBoxLayout(panel)
        column.setContentsMargins(24, 28, 24, 24)
        column.setSpacing(14)
        title = QLabel("空间解析几何")
        title.setStyleSheet("font-size: 21px; font-weight: 700;")
        column.addWidget(title)
        subtitle = QLabel("双叶双曲面")
        subtitle.setStyleSheet("color: #7457af; font-size: 15px; font-weight: 600;")
        column.addWidget(subtitle)
        formula = QLabel("x²/a² + y²/b² − z²/c² = −1")
        formula.setWordWrap(True)
        formula.setStyleSheet("background: #f7f6fb; border: 1px solid #e6e2f0; padding: 10px; font-size: 14px;")
        column.addWidget(formula)
        column.addSpacing(8)
        heading = QLabel("曲面参数")
        heading.setStyleSheet("font-weight: 700; font-size: 14px;")
        column.addWidget(heading)
        form = QFormLayout()
        form.setSpacing(14)

        # 默认参数（与 models/parameters.py 中默认值一致），通过滑块可交互修改
        self.control_a = ParameterControl("a", 0.2)
        self.control_b = ParameterControl("b", 0.2)
        self.control_c = ParameterControl("c", 1)
        # 逐个添加到表单
        form.addRow(QLabel("a"), self.control_a)
        form.addRow(QLabel("b"), self.control_b)
        form.addRow(QLabel("c"), self.control_c)
        # 逐个绑定信号
        self.control_a.slider.valueChanged.connect(self._render_scene)
        self.control_b.slider.valueChanged.connect(self._render_scene)
        self.control_c.slider.valueChanged.connect(self._render_scene)

        column.addLayout(form)
        column.addSpacing(8)
        self.axes_button = self._toggle_button("显示坐标轴", True)
        self.helpers_button = self._toggle_button("显示辅助线", True)
        self.axes_button.toggled.connect(self._render_scene)
        self.helpers_button.toggled.connect(self._render_scene)
        column.addWidget(self.axes_button)
        column.addWidget(self.helpers_button)
        regenerate = QPushButton("重新生成曲面")
        regenerate.clicked.connect(self._render_scene)
        column.addWidget(regenerate)
        save = QPushButton("保存图片")
        save.clicked.connect(self._save_screenshot)
        column.addWidget(save)
        column.addStretch(1)
        hint = QLabel("拖动旋转 · 滚轮缩放 · Shift+拖动平移")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #737a87; font-size: 11px;")
        column.addWidget(hint)
        return panel

    @staticmethod
    def _toggle_button(text: str, checked: bool) -> QPushButton:
        button = QPushButton(text)
        button.setCheckable(True)
        button.setChecked(checked)
        return button

    def _parameters(self) -> HyperboloidParameters:
        """从当前 UI 控件读取并返回 `HyperboloidParameters` 实例。"""
        return HyperboloidParameters(self.control_a.value, self.control_b.value, self.control_c.value)

    def _render_scene(self) -> None:
        if not hasattr(self, "plotter"):
            return
        # 触发场景重建：读取当前参数并传入 build_scene
        build_scene(self.plotter, self._parameters(), self.axes_button.isChecked(), self.helpers_button.isChecked())
        self.plotter.render()

    def _save_screenshot(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "保存场景", str(Path.home() / "hyperboloid.png"), "PNG Images (*.png)")
        if not filename:
            return
        params = self._parameters()
        show_axes = self.axes_button.isChecked()
        show_helpers = self.helpers_button.isChecked()
        # 导出时临时采用 SSAA 获得清晰图像，完成后恢复速度更快的 MSAA 渲染路径。
        build_scene(self.plotter, params, show_axes, show_helpers, high_quality=True)
        self.plotter.screenshot(filename)
        build_scene(self.plotter, params, show_axes, show_helpers, high_quality=False)
        self.plotter.render()
