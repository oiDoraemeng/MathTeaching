# Multi-Pane Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `openspec-executing-plans` to implement this plan task-by-task and sync completed work back to OpenSpec tasks.

**Goal:** 在主工作区实现运行期间的 1–4 独立 2D/3D 窗格、焦点路由、代数 Tab、复制粘贴和教学案例隔离。

**Architecture:** 使用与 Qt 控件无关的 `ScenePaneState` 保存每个窗格状态，由 `ScenePaneManager` 统一管理布局、焦点、renderer 生命周期和全局历史。主窗口、代数面板、场景命令和 Agent 上下文全部通过 pane ID 路由；教学案例继续使用独立视图。

**Tech Stack:** Python 3、PySide6、PyVista/QtInteractor、现有场景控制器、JSON 快照协议、pytest。

**Spec:** `docs/superpowers/specs/2026-09-08-multi-pane-workspace-design.md` 及 `openspec/changes/multi-pane-workspace/` 下的 proposal、design、specs、tasks。

## Global Constraints

- 最多四个窗格，至少保留一个；启动时单窗格。
- 三窗格布局为左侧大窗格加右侧上下两个小窗格；双窗格左右布局；四窗格 2×2。
- 第一版普通窗格状态只保留当前运行期间，不写入数据库；快照增加 `panes` 并保留旧字段。
- 不保留 `self.plotter` 兼容代理；调用链直接迁移到 Pane Manager。
- 教学案例视图与普通工作区窗格隔离。
- 所有工具操作均作用于焦点窗格；Agent 请求开始时锁定目标 pane。
- 设计修订：普通 Pane 与讲义案例 Pane 不再区分类型；窗格总数可超过 4，但最多 4 个可见。
- 设计修订：点击讲义默认只显示一个案例并隐藏所有用户 Pane；Agent“全部显示”只显示当前讲义案例。
- 设计修订：所有 Pane 和代数 Tab 使用统一标题/边框/悬浮关闭行为；教程 2D 使用无限画布。

---

<!-- openspec-task: 1.1 -->
### Task 1: 建立 ScenePaneState 数据模型

**Files:**
- Create: `ui/scene_pane_state.py`
- Test: `tests/test_scene_pane_state.py`

**Interfaces:**
- Produces `ScenePaneState(pane_id: str, name: str)`、`scene_mode`、`scene_2d`、`scene_3d`、`camera_2d`、`camera_3d`、`selected_object_ids`、`algebra_model` 和可选 renderer 引用。
- Produces `to_snapshot()`/`from_snapshot()`，仅序列化 JSON-safe 数据，不序列化 Qt/PyVista 对象。

- [x] 写测试：两个状态实例修改对象、模式、相机、选择和代数数据时互不影响；快照往返保留名称和场景数据。
- [x] 运行 `pytest tests/test_scene_pane_state.py -q`，确认测试先失败。
- [x] 实现数据类、默认空场景和快照校验；拒绝空 pane ID 和非 JSON-safe 字段。
- [x] 重新运行测试并确认通过。
- [x] 提交 `git commit -m "feat: 新增场景窗格状态模型"`。

<!-- openspec-task: 1.2 -->
### Task 2: 实现 ScenePaneManager 布局与焦点

**Files:**
- Create: `ui/scene_pane_manager.py`
- Test: `tests/test_scene_pane_manager.py`

**Interfaces:**
- `set_layout(count: int) -> tuple[str, ...]`、`visible_pane_ids()`、`focus_pane(pane_id: str)`、`create_pane()`、`delete_pane(pane_id: str)`、`layout_rects(size: QSize) -> dict[str, QRect]`。
- `active_pane_id` 变更信号供主窗口和代数面板订阅；维护跨窗格 `HistoryEntry` 栈。

- [x] 写四种布局、隐藏恢复、焦点切换、不能删除最后窗格、最多四窗格和删除后布局修正测试。
- [x] 运行 manager 测试确认失败。
- [x] 实现稳定 pane ID、非对称三窗格矩形、可见集合和 active pane 规则。
- [x] 实现全局历史 `push/undo/redo` 接口并测试跨窗格顺序。
- [x] 运行测试并提交 `git commit -m "feat: 增加窗格管理器和布局模型"`。

<!-- openspec-task: 1.3 -->
### Task 3: 迁移主窗口场景访问

**Files:**
- Modify: `ui/designer_window.py`
- Modify: `services/scene_commands.py`
- Modify: `rendering/geometry_scene.py`
- Modify: `rendering/curve_scene.py`
- Test: `tests/test_scene_command_dispatch.py`

- [x] 为点、线、函数、标注及相机命令增加显式 `pane_id` 或 manager 路由测试。
- [x] 将单例场景成员替换为 manager 管理的 pane state/controller，删除 `self.plotter` 兼容代理。
- [x] 检查所有调用点，确保没有隐式全局 renderer；无 pane 时返回明确错误。
- [x] 运行场景命令和现有 2D/3D 回归测试并提交 `git commit -m "refactor: 将场景命令迁移到窗格路由"`。

<!-- openspec-task: 2.1 -->
### Task 4: 增加右上角图标化布局工具栏

**Files:**
- Modify: `ui/designer_window.py`
- Modify: `ui/icons.py`
- Test: `tests/test_designer_window_toolbar.py`

- [x] 测试四个按钮的中文 accessible name、tooltip、选中态、点击调用 `set_layout(1..4)` 和主题重染。
- [x] 添加单窗格、双窗格、三窗格、四窗格 SVG 图标；替换旧下拉控件。
- [x] 将按钮状态绑定 manager 当前可见数量，不改变焦点内容。
- [x] 运行 Qt 测试并提交 `git commit -m "feat: 添加图标化窗格布局工具栏"`。

<!-- openspec-task: 2.2 -->
### Task 5: 接入窗格容器和生命周期

**Files:**
- Modify: `ui/designer_window.py`
- Create: `ui/scene_pane_widget.py`
- Test: `tests/test_scene_pane_widget.py`

- [x] 测试从单窗格增至多窗格时新 pane 为空，减少时只隐藏，再增加时原内容恢复。
- [x] 每个可见 pane 创建独立 `QtInteractor`，隐藏 pane 释放可视控件但保留状态。
- [x] 处理删除 pane、自动选择合法布局和 active pane 更新。
- [x] 运行测试并提交 `git commit -m "feat: 接入多窗格视口容器"`。

<!-- openspec-task: 2.3 -->
### Task 6: 焦点高亮与最小化恢复重绘

**Files:**
- Modify: `ui/scene_pane_manager.py`
- Modify: `ui/scene_pane_widget.py`
- Modify: `ui/designer_window.py`
- Test: `tests/test_scene_pane_restore.py`

- [x] 测试鼠标点击、键盘 focus-in、工具执行前均更新 active pane，并只高亮一个 pane。
- [x] 在窗口 show/resize/恢复事件中优先刷新 renderer；检测失效后按 pane state 重建并自动重试。
- [x] 运行最小化恢复和已有 WebEngine/渲染回归测试，提交 `git commit -m "fix: 修复多窗格恢复后的空白视口"`。

<!-- openspec-task: 3.1 -->
### Task 7: 代数区域 pane Tab

**Files:**
- Modify: `ui/algebra_panel.py`
- Modify: `ui/designer_window.py`
- Test: `tests/test_algebra_panel.py`

- [x] 测试 pane 与 Tab 一一对应、焦点切换自动激活、Tab 点击反向聚焦 pane、Tab 标题可编辑。
- [x] 将单模型改为按 pane ID 的模型映射；切换前提交未完成公式编辑。
- [x] 隐藏 pane 保留 Tab 模型；教学案例 Tab 保持在独立容器。
- [x] 运行测试并提交 `git commit -m "feat: 增加按窗格同步的代数标签页"`。

<!-- openspec-task: 3.2 -->
### Task 8: 工具与编辑操作焦点路由

**Files:**
- Modify: `ui/designer_window.py`
- Modify: `ui/algebra_panel.py`
- Modify: `services/scene_commands.py`
- Test: `tests/test_pane_focus_routing.py`

- [x] 为点、线、函数、标注的新增、显隐、删除和公式编辑编写“只改变焦点 pane”测试。
- [x] 将工具入口统一改为 manager 的 `active_pane()`，禁止读取全局场景对象。
- [x] 验证 2D 工具在 3D pane 上给出模式不支持结果而不污染其他 pane。
- [x] 运行测试并提交 `git commit -m "feat: 将编辑工具路由到焦点窗格"`。

### Task 13: 统一 Pane Chrome 与讲义显示集合

**Files:**
- Modify: `ui/scene_pane_manager.py`
- Modify: `ui/scene_pane_widget.py`
- Modify: `ui/teaching_case_panes.py`
- Modify: `ui/designer_window.py`
- Modify: `ui/algebra_panel.py`
- Test: `tests/test_unified_pane_chrome.py`

- [ ] 将案例 Pane 注册到统一 manager；点击讲义保存用户可见集合，只显示一个案例；Agent“全部显示”只显示案例集合，最多四个。
- [ ] 为 Pane 增加标题栏、边框、隐藏、全屏、悬浮关闭按钮；关闭后删除并修正布局。
- [ ] 为代数 Tab 增加悬浮关闭按钮；Tab 超宽时启用无滚动条横向滚动。
- [ ] 增加统一样式和显示集合回归测试。

### Task 14: 无限画布与教程视口边界修复

**Files:**
- Modify: `rendering/two_d_scene.py`
- Modify: `ui/teaching_case_panes.py`
- Test: `tests/test_infinite_2d_canvas.py`

- [ ] 移除教程视口世界边界绘制，保留屏幕裁剪。
- [ ] 验证缩放围绕焦点、平移和最小化恢复不出现边界矩形。
- [ ] 运行 2D 场景和教程恢复回归测试。

<!-- openspec-task: 3.3 -->
### Task 9: 多选与 JSON 复制粘贴

**Files:**
- Create: `services/scene_clipboard.py`
- Modify: `ui/scene_pane_widget.py`
- Modify: `ui/designer_window.py`
- Test: `tests/test_scene_clipboard.py`

- [ ] 测试矩形多选和单对象选择生成点、线、函数、标注快照；验证版本、大小上限和字段白名单。
- [ ] 实现跨 pane 粘贴原坐标、同 pane 粘贴按一个网格单位偏移，并重新生成对象 ID。
- [ ] 将粘贴作为单个全局历史操作，失败时回滚且不改变剪贴板。
- [ ] 运行测试并提交 `git commit -m "feat: 支持窗格对象多选复制粘贴"`。

<!-- openspec-task: 4.1 -->
### Task 10: 隔离教学案例视图

**Files:**
- Modify: `ui/teaching_case_panes.py`
- Modify: `ui/designer_window.py`
- Modify: `ui/agent_sidebar_web.py`
- Test: `tests/test_teaching_case_panes.py`

- [ ] 测试已有普通 pane 时打开向量加法不会创建、替换或删除普通 pane，也不会改变普通代数 Tab。
- [ ] 保持 `TeachingCasePaneGrid` 独立 renderer/生命周期和 Agent 案例 Tab；普通 pane manager 不接受 case plan。
- [ ] 运行案例回归测试并提交 `git commit -m "refactor: 隔离教学案例与普通工作区窗格"`。

<!-- openspec-task: 4.2 -->
### Task 11: 更新快照、Agent 上下文和协议

**Files:**
- Modify: `agent/scene_snapshot.py`
- Modify: `agent/capabilities/scene_tools.py`
- Modify: `agent/web_protocol.py`
- Test: `tests/test_agent_scene_snapshot_adapter.py`
- Test: `tests/test_scene_snapshot.py`

- [ ] 测试 `panes` 快照包含所有 pane、active pane 和模式/相机/代数数据，同时旧字段仍可读取。
- [ ] 在 Agent 请求开始时锁定 pane A，焦点变化后继续写入 A；恢复回合重建完整多窗格状态。
- [ ] 校验协议事件中的 pane ID，拒绝不存在或被删除的 pane，并保持教学案例事件独立。
- [ ] 运行 Agent 和协议测试并提交 `git commit -m "feat: 扩展多窗格场景快照协议"`。

<!-- openspec-task: 4.3 -->
### Task 12: 完整验证与手动走查

**Files:**
- Modify: `openspec/changes/multi-pane-workspace/tasks.md`（仅同步完成勾选）

- [ ] 运行 `pytest -q`，确认 Python 测试通过。
- [ ] 运行 `ui/agent_web` 的测试和生产构建，确认前端无回归。
- [ ] 手动走查 2D/3D 单、双、三、四窗格；验证焦点、Tab、删除、复制粘贴、全局撤销和最小化恢复。
- [ ] 将验证结果记录到变更日志，按 OpenSpec 规则勾选已完成任务并提交 `git commit -m "test: 完成多窗格工作区回归验证"`。
