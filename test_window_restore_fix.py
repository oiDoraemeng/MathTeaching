"""验证窗口恢复后 WebEngine 表面重建的改进方案。

这个脚本测试了针对 Windows 最小化恢复后内容空白问题的修复：
1. 核心修复：在 showEvent 中设置 Qt::WA_Mapped 属性（参考 CSDN 文章方案）
2. 改进的 rebuild_web_surface 函数使用 hide/show + processEvents 确保表面重建
3. 多次重试机制（400ms、800ms、1200ms）应对 Windows 动画时序不确定性

原理：
Qt 内部的 WA_Mapped 状态标记窗口是否已被"映射到屏幕"。在 Windows 从最小化
恢复时，操作系统通知 Qt 窗口即将显示，但 Qt 可能未正确设置 WA_Mapped 标志，
导致其认为窗口仍处于"未映射"状态，从而跳过绘制流程，造成界面空白。

通过在 Show 事件和 WindowStateChange 事件中显式设置 WA_Mapped，确保 Qt 的
窗口映射状态与操作系统实际状态同步。
"""

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
import sys


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("窗口恢复测试 - 最小化后内容应正常显示")
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # 说明标签
        info = QLabel(
            "测试步骤：\n"
            "1. 点击下方的 WebView 应显示内容\n"
            "2. 点击最小化按钮将窗口最小化\n"
            "3. 再次点击任务栏图标恢复窗口\n"
            "4. WebView 应该正常显示内容（不应空白或卡死）\n"
            "5. 可拖动窗口边缘测试响应性\n"
            "6. 点击 [检查 WA_Mapped 状态] 按钮查看修复效果"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # WebEngine 视图
        self.web_view = QWebEngineView()
        self.web_view.setHtml("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {
                        font-family: sans-serif;
                        padding: 20px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        margin: 0;
                    }
                    .box {
                        background: rgba(255, 255, 255, 0.1);
                        padding: 20px;
                        border-radius: 10px;
                        margin: 10px 0;
                        backdrop-filter: blur(10px);
                    }
                    h1 { margin: 0 0 10px 0; }
                    .time { font-size: 2em; font-weight: bold; }
                </style>
            </head>
            <body>
                <div class="box">
                    <h1>✓ WebEngine 渲染正常</h1>
                    <p>如果你能看到这段文字，说明 WebEngine 已成功初始化。</p>
                </div>
                <div class="box">
                    <h2>实时时钟</h2>
                    <div class="time" id="clock"></div>
                </div>
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

        # 测试按钮
        btn_layout = QVBoxLayout()

        minimize_btn = QPushButton("最小化窗口")
        minimize_btn.clicked.connect(self.showMinimized)
        btn_layout.addWidget(minimize_btn)

        rebuild_btn = QPushButton("手动触发表面重建")
        rebuild_btn.clicked.connect(self.manual_rebuild)
        btn_layout.addWidget(rebuild_btn)

        check_btn = QPushButton("检查 WA_Mapped 状态")
        check_btn.clicked.connect(self.check_wa_mapped)
        btn_layout.addWidget(check_btn)

        layout.addLayout(btn_layout)

        # 监控窗口状态
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QWindowStateChangeEvent

        # 🔑 核心修复：在 Show 事件时设置 WA_Mapped 属性
        if obj is self and event.type() == QEvent.Type.Show:
            print("✓ Show 事件触发，设置 WA_Mapped 属性...")
            self.setAttribute(Qt.WidgetAttribute.WA_Mapped)
            print(f"  -> WA_Mapped 已设置: {self.testAttribute(Qt.WidgetAttribute.WA_Mapped)}")

        if obj is self and event.type() == QEvent.Type.WindowStateChange:
            if isinstance(event, QWindowStateChangeEvent):
                was_minimized = bool(event.oldState() & Qt.WindowState.WindowMinimized)
                is_normal = not self.isMinimized()

                if was_minimized and is_normal:
                    print("✓ 检测到窗口恢复，设置 WA_Mapped 并开始重建表面...")
                    # 确保在恢复时也设置 WA_Mapped
                    self.setAttribute(Qt.WidgetAttribute.WA_Mapped)
                    print(f"  -> WA_Mapped 状态: {self.testAttribute(Qt.WidgetAttribute.WA_Mapped)}")
                    QTimer.singleShot(300, self.rebuild_surfaces)

        return super().eventFilter(obj, event)

    def rebuild_surfaces(self):
        """模拟 MainWindow._restore_render_surfaces 的逻辑"""
        from ui.web_surface import rebuild_web_surface

        print("执行第1次表面重建...")
        result = rebuild_web_surface(self.web_view)
        print(f"  -> rebuild_web_surface 返回: {result}")

        # 多次重试，延迟递增
        for i in range(1, 4):
            delay = 400 * i
            QTimer.singleShot(delay, lambda n=i: self.retry_rebuild(n))

    def retry_rebuild(self, retry_num):
        from ui.web_surface import rebuild_web_surface
        print(f"执行第{retry_num+1}次表面重建...")
        result = rebuild_web_surface(self.web_view)
        print(f"  -> rebuild_web_surface 返回: {result}")

    def manual_rebuild(self):
        """手动测试按钮"""
        from ui.web_surface import rebuild_web_surface
        print("手动触发表面重建...")
        result = rebuild_web_surface(self.web_view)
        print(f"  -> rebuild_web_surface 返回: {result}")
        self.web_view.update()
        self.web_view.repaint()

    def check_wa_mapped(self):
        """检查窗口的 WA_Mapped 状态"""
        is_mapped = self.testAttribute(Qt.WidgetAttribute.WA_Mapped)
        is_visible = self.isVisible()
        is_minimized = self.isMinimized()

        print("=" * 60)
        print("窗口状态检查：")
        print(f"  WA_Mapped:   {is_mapped}")
        print(f"  isVisible(): {is_visible}")
        print(f"  isMinimized(): {is_minimized}")
        print("=" * 60)

        if is_visible and not is_minimized and not is_mapped:
            print("⚠️ 警告：窗口可见但 WA_Mapped 未设置！正在修复...")
            self.setAttribute(Qt.WidgetAttribute.WA_Mapped)
            print(f"  -> 修复后 WA_Mapped: {self.testAttribute(Qt.WidgetAttribute.WA_Mapped)}")
        elif is_mapped:
            print("✓ WA_Mapped 状态正常")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    print("=" * 60)
    print("窗口恢复修复测试 - 结合 WA_Mapped 方案")
    print("=" * 60)
    print()
    print("改进内容：")
    print("1. ✅ 在 Show 事件中设置 Qt::WA_Mapped 属性（核心修复）")
    print("2. ✅ 在窗口状态恢复时确保 WA_Mapped 被设置")
    print("3. ✅ rebuild_web_surface 使用 hide/show + processEvents")
    print("4. ✅ 多次重试机制（400ms、800ms、1200ms）")
    print()
    print("原理：确保 Qt 内部窗口映射状态与操作系统状态同步")
    print()

    window = TestWindow()
    window.show()

    sys.exit(app.exec())
