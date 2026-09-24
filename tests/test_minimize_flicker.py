"""测试窗口最小化恢复后的闪烁问题修复效果。

改进重点：
1. 减少重试次数（3次 → 1次）
2. 增加初始延迟（300ms → 150ms + 600ms）
3. 温和的表面重建（优先 WA_Mapped，避免 hide/show）
"""

import sys
from datetime import datetime
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView


class FlickerTestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("最小化闪烁测试 - 优化版")
        self.resize(800, 600)

        self.rebuild_count = 0
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 状态标签
        self.status_label = QLabel("窗口正常显示")
        self.status_label.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(self.status_label)

        # 重建计数标签
        self.rebuild_label = QLabel("表面重建次数: 0")
        self.rebuild_label.setStyleSheet("font-size: 12px; padding: 5px; color: #666;")
        layout.addWidget(self.rebuild_label)

        # WebEngine 视图
        self.web_view = QWebEngineView()
        self.web_view.setHtml("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    margin: 0;
                    padding: 40px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    font-family: Arial, sans-serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                }
                #clock {
                    font-size: 48px;
                    font-weight: bold;
                    margin: 20px 0;
                }
                #info {
                    font-size: 18px;
                    opacity: 0.9;
                }
            </style>
        </head>
        <body>
            <h1>WebEngine 内容测试</h1>
            <div id="clock"></div>
            <div id="info">如果看到此内容且时钟在更新，说明 WebEngine 正常工作</div>
            <script>
                function updateClock() {
                    document.getElementById('clock').textContent =
                        new Date().toLocaleTimeString('zh-CN');
                }
                setInterval(updateClock, 1000);
                updateClock();
            </script>
        </body>
        </html>
        """)
        layout.addWidget(self.web_view)

        # 控制按钮
        btn_layout = QVBoxLayout()

        self.minimize_btn = QPushButton("最小化窗口")
        self.minimize_btn.clicked.connect(self.showMinimized)
        btn_layout.addWidget(self.minimize_btn)

        self.rebuild_btn = QPushButton("手动触发表面重建")
        self.rebuild_btn.clicked.connect(self.manual_rebuild)
        btn_layout.addWidget(self.rebuild_btn)

        self.check_btn = QPushButton("检查 WA_Mapped 状态")
        self.check_btn.clicked.connect(self.check_mapped_state)
        btn_layout.addWidget(self.check_btn)

        layout.addLayout(btn_layout)

    def showEvent(self, event):
        """重写 showEvent 设置 WA_Mapped（模拟主窗口的修复）。"""
        self.setAttribute(Qt.WidgetAttribute.WA_Mapped)
        super().showEvent(event)
        self.status_label.setText(f"showEvent 触发 - WA_Mapped 已设置 [{datetime.now().strftime('%H:%M:%S')}]")

    def changeEvent(self, event):
        """监控窗口状态变化。"""
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                self.status_label.setText("窗口已最小化")
                self.rebuild_count = 0  # 重置计数
                self.rebuild_label.setText("表面重建次数: 0")
            elif self.windowState() == Qt.WindowState.WindowNoState:
                self.status_label.setText(f"窗口已恢复 - WA_Mapped 已设置 [{datetime.now().strftime('%H:%M:%S')}]")
                self.setAttribute(Qt.WidgetAttribute.WA_Mapped)
                # 模拟优化后的重建策略
                QTimer.singleShot(150, self.simulate_optimized_rebuild)

    def simulate_optimized_rebuild(self):
        """模拟优化后的表面重建策略（只在必要时执行1次）。"""
        if not self.isMinimized():
            self.rebuild_count += 1
            self.rebuild_label.setText(f"表面重建次数: {self.rebuild_count}")
            # 温和的重建：只设置 WA_Mapped 和 update
            self.web_view.setAttribute(Qt.WidgetAttribute.WA_Mapped)
            self.web_view.update()
            self.status_label.setText(
                f"执行温和重建 (#{self.rebuild_count}) [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]"
            )

            # 只做1次兜底重试（600ms 后）
            QTimer.singleShot(600, self.final_rebuild_check)

    def final_rebuild_check(self):
        """最后的兜底检查（模拟 _retry_web_render_surfaces）。"""
        if not self.isMinimized():
            self.rebuild_count += 1
            self.rebuild_label.setText(f"表面重建次数: {self.rebuild_count}")
            self.web_view.setAttribute(Qt.WidgetAttribute.WA_Mapped)
            self.web_view.update()
            self.status_label.setText(
                f"兜底检查完成 (#{self.rebuild_count}) [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]"
            )

    def manual_rebuild(self):
        """手动触发表面重建用于测试。"""
        from ui.web_surface import rebuild_web_surface
        result = rebuild_web_surface(self.web_view)
        self.rebuild_count += 1
        self.rebuild_label.setText(f"表面重建次数: {self.rebuild_count} (手动)")
        self.status_label.setText(
            f"手动重建 {'成功' if result else '失败'} [{datetime.now().strftime('%H:%M:%S')}]"
        )

    def check_mapped_state(self):
        """检查 WA_Mapped 状态。"""
        main_mapped = self.testAttribute(Qt.WidgetAttribute.WA_Mapped)
        web_mapped = self.web_view.testAttribute(Qt.WidgetAttribute.WA_Mapped)
        self.status_label.setText(
            f"主窗口 WA_Mapped: {main_mapped} | WebView WA_Mapped: {web_mapped}"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = FlickerTestWindow()
    window.show()

    print("=" * 60)
    print("窗口最小化闪烁测试 - 优化版")
    print("=" * 60)
    print("\n测试步骤：")
    print("1. 观察 WebEngine 内容正常显示（紫色渐变 + 时钟）")
    print("2. 点击'最小化窗口'按钮或使用系统最小化")
    print("3. 从任务栏恢复窗口")
    print("4. 观察是否有闪烁，以及'表面重建次数'")
    print("\n预期结果：")
    print("- 闪烁次数：0-2 次（之前是 4-5 次）")
    print("- 表面重建次数：1-2 次（之前是 4 次以上）")
    print("- WebEngine 内容立即可见且时钟继续更新")
    print("=" * 60)

    sys.exit(app.exec())
