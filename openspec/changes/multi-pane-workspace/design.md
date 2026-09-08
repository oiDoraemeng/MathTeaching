## Context

当前 `MainWindow` 将 `plotter`、`geometry_controller`、`curve_controller`、代数面板图层列表和撤销栈作为单例状态；右上角布局控件仍是面向教学案例的下拉按钮。现有 `TeachingCasePaneGrid` 使用案例 plan 创建专用视口，不适合作为普通绘图工作区。详见 `proposal.md` 的问题范围。

## Goals / Non-Goals

**Goals:**

- 建立与教学案例无关的 `ScenePaneState` 和 `ScenePaneManager`。
- 每个窗格拥有独立的 2D/3D 场景模型、相机、渲染控制器、选择状态和历史栈。
- 用 1×1、1×2、1×3、2×2 统一表达 1–4 窗格布局；布局变化只改变可见性和网格位置。
- 让焦点窗格成为所有代数面板和绘图工具的唯一操作目标。
- 以稳定窗格 ID 保存内容，使减少窗格后再增加可以恢复原状态。
- 为复制/粘贴建立经过校验的场景对象序列化边界。

**Non-Goals:**

- 不改变线性代数教学 artifact、案例内容或 Agent 会话协议的语义。
- 不在本变更中实现跨窗格联动绘制、同步相机或实时协作。
- 不把多个窗格合并为一个 PyVista renderer，也不依赖截图复制场景。

## Decisions

### 1. 独立窗格状态而非共享 renderer

新增 `ScenePaneState`，保存 pane ID、scene mode、2D/3D model、camera state、controllers、selection 和 history；`ScenePaneManager` 负责创建最多四个状态、布局和焦点。每个窗格使用自己的 `QtInteractor`，避免 actor、相机和输入事件互相污染。

替代方案：在一个 plotter 中按 alias 分组绘制。拒绝，因为无法满足独立编辑、独立缩放和焦点路由。

### 2. 主窗口保留兼容代理，渐进迁移调用链

先把现有 `self.plotter`、`self.geometry_controller` 等访问收敛到“当前焦点窗格代理”，再迁移绘图入口和场景快照。这样旧的场景命令、Agent 和 2D 工具可以逐步接入，不需要一次性重写全部业务逻辑。

替代方案：复制四份 `MainWindow` 场景代码。拒绝，因为状态容易分叉、维护成本高且无法保证协议一致。

### 3. 代数 Tab 由窗格 ID 驱动

代数面板改为 `QTabWidget` 或等价的 Tab 容器，Tab 与 pane ID 一一对应。每个 Tab 绑定该窗格的图层模型；焦点事件只更新当前 Tab，不复制或重置数据。切换布局隐藏 Tab 的同时保留其模型，新增 pane 创建空模型。

### 4. 焦点路由优先于显式选择

每个 interactor 在鼠标按下、键盘焦点和 Tab 切换时通知 manager；工具事件通过 `active_pane_id` 路由。右上角四个布局按钮只改变布局，不改变焦点，除非当前焦点窗格被隐藏，此时选择第一个可见窗格。

### 5. 复制/粘贴使用 JSON-safe 对象快照

复制只读取当前窗格选中对象或选区，生成有版本号、有大小限制的对象快照；粘贴只写入当前焦点窗格并重新生成对象 ID，避免 alias/id 冲突。剪贴板不包含 renderer、Qt 对象或任意代码。

### 6. 教学案例继续使用独立通道

`TeachingCasePaneGrid` 和 `linear-algebra-case-tabs` 继续负责案例展示；通用 `ScenePaneManager` 不接受案例 plan。案例 Tab 可以在 Agent 侧显示，但不得覆盖普通窗格的代数 Tab 或焦点状态。

## Risks / Trade-offs

- [Risk] 最多四个 `QtInteractor` 增加 GPU/内存占用 → 懒创建窗格，隐藏窗格保留轻量状态；关闭工作区时统一释放 renderer。
- [Risk] 旧方法直接访问单例 `self.plotter` → 先引入当前窗格代理并增加断言，逐步迁移调用点。
- [Risk] 窄窗口下四窗格难以操作 → 保留布局按钮可切换回单窗格，并为窗格设置最小尺寸和焦点高亮。
- [Risk] 复制粘贴破坏历史或产生 ID 冲突 → 粘贴作为一次原子场景操作，失败时回滚并不改变剪贴板。
- [Risk] 多个 Web/Qt 子表面恢复时重绘失败 → 统一由 pane manager 处理 show/resize/render 生命周期，并覆盖最小化恢复测试。

## Migration Plan

1. 新增窗格状态、布局和焦点模型，先以空白窗格替代案例专用布局按钮。
2. 迁移 2D 点、线、函数、标注及代数 Tab；补齐复制/粘贴和历史隔离。
3. 迁移 3D 图层、相机和场景命令代理；保持 Agent 默认操作当前焦点窗格。
4. 更新右上角图标控件、主题、无障碍名称和最小化恢复重绘。
5. 最后接入教学案例显示适配和回归测试；失败时可回退到单窗格模式。

## Open Questions

- 复制对象的默认粘贴偏移量（保持原坐标还是自动平移）可在实现阶段根据现有 2D 编辑习惯确定，不改变窗格契约。
