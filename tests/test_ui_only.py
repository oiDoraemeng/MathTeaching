"""测试 UI 组件（不启动 VTK 3D 渲染）"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QToolButton, QFrame
from PySide6.QtCore import Qt

from ui.agent_sidebar import AgentSidebar, AgentSidebarState

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Agent 侧边栏测试 - 右上角按钮控制")
        self.resize(1200, 800)

        # 创建中央容器
        central = QWidget()
        self.setCentralWidget(central)

        # 水平布局
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 左侧主内容区域（模拟视口）
        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 模拟右上角工具栏
        toolbar = QFrame()
        toolbar.setObjectName("viewportToolbar")
        toolbar_layout = QVBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        toolbar_layout.setSpacing(4)

        settings_btn = QToolButton()
        settings_btn.setText("⚙")
        settings_btn.setToolTip("场景设置")
        settings_btn.setFixedSize(38, 38)

        mode_btn = QToolButton()
        mode_btn.setText("🔄")
        mode_btn.setToolTip("切换二维和三维场景")
        mode_btn.setFixedSize(38, 38)

        self.agent_btn = QToolButton()
        self.agent_btn.setText("🤖")
        self.agent_btn.setToolTip("AI 助手")
        self.agent_btn.setFixedSize(38, 38)

        toolbar_layout.addWidget(settings_btn)
        toolbar_layout.addWidget(mode_btn)
        toolbar_layout.addWidget(self.agent_btn)
        toolbar.adjustSize()

        # 将工具栏定位到右上角
        toolbar.setParent(main_area)
        toolbar.move(1200 - 380 - 50, 12)  # 右侧留出侧边栏空间
        toolbar.raise_()

        viewport_label = QLabel("主视口区域\n\n点击右上角 AI 图标 (🤖) 展开侧边栏")
        viewport_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        viewport_label.setStyleSheet("background: #1a1a1a; color: #ffffff; font-size: 16px;")
        main_layout.addWidget(viewport_label)

        layout.addWidget(main_area, 1)

        # 右侧 AI 侧边栏
        self.agent_sidebar = AgentSidebar(self)
        layout.addWidget(self.agent_sidebar)

        # 连接右上角按钮到侧边栏切换
        self.agent_btn.clicked.connect(self.agent_sidebar.toggle)

        # 应用样式
        self.setStyleSheet("""
            QMainWindow { background: #0A0D12; }

            #viewportToolbar { background: #ffffff; border: 1px solid #d0d7df; border-radius: 6px; }
            #viewportToolbar QToolButton { font-size: 18px; font-weight: 700; min-width: 24px; min-height: 24px; color: #4a5563; border: 1px solid transparent; border-radius: 4px; }
            #viewportToolbar QToolButton:hover { background: #eef2f5; border-color: #cfd8e1; }

            #agentSidebar { background: #0F131C; }
            #agentCollapsedBar { background: #161D2B; border-left: 1px solid #2A3647; }
            #agentCollapsedLabel { color: #9CA3AF; font-size: 12px; font-weight: 500; }
            #agentIconButton { background: transparent; border: none; font-size: 20px; }
            #agentIconButton:hover { background: #1E2636; border-radius: 6px; }
            #agentStatusIndicator { color: #6B7280; font-size: 16px; }

            #agentPanel { background: #0F131C; border-left: 1px solid #2A3647; }
            #agentTitle { color: #F3F4F6; font-size: 15px; font-weight: 700; }
            #agentStatus { color: #9CA3AF; font-size: 11px; }
            #agentModeHint { color: #F59E0B; background: #451A03; border: 1px solid #78350F; border-radius: 4px; padding: 5px; }
            #agentMessageScroll { background: #0F131C; border: 1px solid #1E2636; border-radius: 5px; }
            #agentUserBubble { background: #1E3A5F; border: 1px solid #2563EB; border-radius: 7px; color: #E0E7FF; }
            #agentAssistantBubble { background: #1E2636; border: 1px solid #374151; border-radius: 7px; color: #E5E7EB; }
            #agentPlanCard { background: #2A3647; border: 1px solid #38BDF8; border-radius: 6px; }
            #agentPromptEdit { background: #1E2636; border: 1px solid #374151; border-radius: 5px; padding: 5px; color: #E5E7EB; }
            #agentPromptEdit:focus { border: 2px solid #38BDF8; }
            #agentSendButton { min-height: 34px; background: #38BDF8; color: #0F131C; border: none; font-weight: 600; }
            #agentSendButton:hover { background: #0EA5E9; }
            #agentSendButton:disabled { background: #374151; color: #6B7280; }
        """)

        # 测试状态更新
        self.agent_sidebar.set_model_status("本地演示模式", enabled=False)

        print("[OK] UI component loaded")
        print(f"[OK] Sidebar initial state: {self.agent_sidebar.state.value}")
        print("[OK] Click AI robot button (top-right) to test expand/collapse")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()

    print("\n" + "="*60)
    print("AI Agent Sidebar Test - Top-right Button Control")
    print("="*60)

    sys.exit(app.exec())
