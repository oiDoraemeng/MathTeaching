# Deep Technical Design: 统一视觉设计与信息架构（v2 头脑风暴深化版）

> 本版由 Superpowers Brainstorming 流程产出：§1 为方案探索与决策记录（ADR），每个决策点比较至少 3 个备选方案；§2 起为深化技术设计。
> 相对 v1 的两处事实修正：**WebView 为构造即加载、文档常驻**（`agent_sidebar_web.py:106`），非懒加载；**左栏 300–360px 仅为 min/max 约束、无拖拽手柄**（`algebra_panel.py:538-539`），当前不可调。

## 0. 问题陈述与设计目标

**一句话问题**：三轮独立迭代（Qt 浅蓝灰 QSS / React 深色 WebView / 已删除的紫色 Qt 聊天面板残留）使应用缺少统一的视觉语言与信息层级。

**目标用户**：讲授空间解析几何的教师（大屏投影，需清晰对比度与状态可读性）与课堂学生（跟随演示、偶用 AI 助手）。

**成功标准**：
1. 浅/深主题下所有表面（Qt 面板、悬浮层、对话框、状态栏、Agent 侧栏）呈现同一套令牌语言，文字对比度 ≥ WCAG AA 4.5:1。
2. 主题切换零重启生效、Web 侧栏首帧即正确主题（无闪烁）。
3. 左栏 260–420px、Agent 面板 360–560px 均可拖且布局完整；窗口在 1024px 最小宽度下三栏与状态栏不溢出。
4. Unicode 图标按钮全部替换为与 Web 侧一致的 SVG 图标。
5. 现有 2D/3D 渲染回归与桥接协议测试全绿。

## 1. 方案探索与决策记录（ADR）

### D1 设计令牌的源格式

| 方案 | 优点 | 缺点 |
|---|---|---|
| A. Python 模块为源，构建时 dump JSON | 类型安全、IDE 补全 | 前端构建依赖 Python 运行时；"源"偏向单一语言 |
| B. **`design/tokens.json` 为中立源**，`ui/tokens.py` 提供 typed loader | 双语言解耦；无 Python 环境也能构建前端；diff 友好 | JSON 无注释（用 `"$comment"` 字段） |
| C. QSS/CSS 各自维护，靠测试断言一致 | 零基础设施 | 双源漂移风险，治标不治本 |

**决策：B**。`design/tokens.json` 提交入库作为唯一真源；`ui/tokens.py` 加载并校验 schema（缺字段/非法值启动即报错）；`ui/agent_web/scripts/gen-theme.mjs` 读取同一 JSON 生成 `src/styles/theme.css`。Python 侧不再运行时渲染 Web 令牌（v1 的 `dump_json()` 职责移除，改为 loader）。

### D2 Web 侧栏主题注入机制

| 方案 | 优点 | 缺点 |
|---|---|---|
| A. 仅 bridge 事件（loadFinished 后发 `theme_state` 含全量 tokens） | 单通道 | **首帧闪烁**：事件晚于 CSS 解析；全量 tokens 是过度设计（构建期已有两套变量） |
| B. **URL 查询参数 + UserScript 首帧注入，事件仅传 mode** | DocumentCreation 时机先于 CSS 生效，零闪烁零竞态；payload 极小 | 两个通道各司其职，需文档说明 |
| C. 切主题时重新 `setUrl` 加载 | 实现简单 | 丢失对话滚动位置与未保存草稿；重载成本高 |

**决策：B**，两通道分工：
1. **首帧**：`setUrl("mathagent://app/index.html?theme=dark")` 携带当前有效主题；`QWebEngineScript`（`DocumentCreation` 时机）读 `location.search` 设置 `<html data-theme>`，先于任何 CSS/JS 执行。
2. **运行时切换**：`theme_state` 事件，payload 仅 `{mode: "light"|"dark"}`（v1 的全量 tokens 覆盖层删除——构建产物已含两套完整变量，运行时只需模式位；用户自定义主题是非目标）。
3. 文档常驻（构造即加载且仅隐藏不销毁），事件始终可达；`loadFinished` 前的事件缓存待发（对齐用，首帧已由 URL 保证）。

### D3 Qt QSS 生成架构

| 方案 | 优点 | 缺点 |
|---|---|---|
| A. Python f-string 内联模板 | 零文件依赖 | 数百行 QSS 嵌在 .py 中不可维护、无语法高亮 |
| B. **`ui/styles/base.qss.in` 模板文件 + `string.Template`（`$token` 语法）** | 模板可高亮可 lint；`$` 在 QSS 中无冲突；替换逻辑 5 行 | 需要打包包含模板文件（现有 `pyproject.toml` 已含数据文件机制） |
| C. 运行时 QSS 变量解释器（仿 CSS `var()`） | 灵活 | 明显过度工程 |

**决策：B**。`build_qss(theme) -> str`：读模板 → `Template.substitute` 展平令牌（令牌键形如 `color_bg_panel`，避免嵌套点号）→ 返回 QSS 字符串。主题切换 = 重渲 QSS + `setStyleSheet`，Qt 自动重算整个窗口样式树。

### D4 状态信息承载形态

| 方案 | 优点 | 缺点 |
|---|---|---|
| A. **底部状态栏（30px）** | 教学软件/CAD 惯例；被动信息（模式/状态）的正确位置；不与视口悬浮工具栏竞争右上空间 | 顶部无全局入口（本项目无菜单需求，可接受） |
| B. 顶部工具栏 | 可承载主动操作 | 与右上悬浮按钮重复；压缩视口纵向空间 |
| C. 两者都要 | 信息最全 | 超出 YAGNI；增加维护面 |

**决策：A**。教学场景注意力应在画布；状态栏只承载被动状态 + 主题切换，不做业务操作。

### D5 Qt 图标渲染

| 方案 | 优点 | 缺点 |
|---|---|---|
| A. **内嵌 lucide SVG 字符串 + `QSvgRenderer` 着色渲染** | 与 Web 侧 `lucide-react` 同名同形；无新依赖；矢量 + DPR 感知 | 需手写着色（lucide 用 `stroke="currentColor"`，`QSvgRenderer` 不解析） |
| B. QtAwesome | 开箱即用 | 新第三方依赖（与提案冲突）；字体图标与 Web 视觉不同源 |
| C. `QIcon.fromTheme` | 零成本 | Windows 无 freedesktop 主题，结果不可预测 |
| D. 预渲染多色 PNG | 简单 | 位图模糊、需多分辨率、主题切换重建 |

**决策：A**。着色方式：字符串替换 `currentColor` 为目标色 → `QSvgRenderer` 渲染到 `QPixmap`（按 `devicePixelRatio` 放大再缩小逻辑尺寸），缓存键 `(name, color, size, dpr)`。注意 lucide 是 stroke 型图标（stroke-width 2, 24×24 viewBox），渲染尺寸 16px 时视觉粗细与 Web 侧 16px 一致。

### D6 两侧面板宽度调节（v2.1：经用户确认，左栏同样可调）

| 方案 | 优点 | 缺点 |
|---|---|---|
| A. 三段 QSplitter（左右一次到位） | Qt 标准、单组件 | **改变 widget 父子关系**，`_ViewportResizeFilter` 依赖的原生 VTK 视口层级需重新验证；默认允许拖至 0 折叠（需逐段 `setCollapsible(False)`）；两段手柄样式与行为需分别 QSS 定制 |
| B. **两个专用 5px 拖拽手柄**（共享一个参数化 `_PanelResizeHandle` 类） | 布局树不变、`_ViewportResizeFilter` 零风险；方向/范围/默认值/QSettings 键全部参数化，两个手柄代码量与单手柄几乎相同 | 需自写 ~60 行鼠标事件处理 |
| C. 仅右栏可拖（v2 原案） | 改动最小 | 不满足用户"左栏也可调"的确认诉求 |

**决策：B**。两侧手柄均常驻可见（左栏手柄在 AlgebraPanel 与 viewportHost 之间，右栏手柄在 viewportHost 与 AgentSidebar 之间；右栏手柄随 Agent 面板显隐）。

| 参数 | 左栏（AlgebraPanel） | 右栏（AgentSidebar） |
|---|---|---|
| 范围 | **260–420px** | 360–560px |
| 默认 | 320px（现约束区间中值） | 440px（现值） |
| QSettings 键 | `ui/algebra_panel_width` | `ui/agent_panel_width` |
| 显隐 | 常驻 | 随 Agent 面板 |

- 左栏范围放宽理由：现 min 300/max 360 是"固定不可拖"时代的被动约束；可拖后下探 260（列表/公式预览仍可读）、上探 420（大屏教学舒适上限）。
- 最小窗口 1024px 校验：左 260 + 视口 ≥ 300 + 右 360 + 双手柄 2×5 + 状态栏 = 930 ≤ 1024 ✓。
- `algebra_panel.py:538-539` 的 `setMinimumWidth(300)/setMaximumWidth(360)` 改为 260/420；两面板初始 `setFixedWidth(QSettings 读取值 or 默认)`。

### D7 场景（3D/2D 画布）主题跟随

| 方案 | 优点 | 缺点 |
|---|---|---|
| A. **新增 `auto` 背景语义，默认跟随主题，显式选择视为覆盖** | 向后兼容；教学投影场景常需固定背景 | `SceneAppearance.background` 需从二值扩为三值 |
| B. 场景独立于 UI 主题 | 零改动 | 深色 UI + 浅色画布的割裂仍在 |
| C. 强制跟随（移除选择） | 一致性最强 | 破坏现有教学用法（已有用户显式依赖黑白背景切换） |

**决策：A**。现状 `scene_settings.py:38-39` 背景 combo 为 `"light"/"dark"` 二值；新增 `"auto"`（"跟随主题"）置于首位并作为新默认，旧会话存储的 light/dark 值原样视为显式覆盖。2D 网格线（`two_d_scene.py:88`）与 3D 轴色对比逻辑在 `auto` 下按有效主题选择两套预置。

### D8 字体策略

| 方案 | 优点 | 缺点 |
|---|---|---|
| A. **`QApplication.setFont` 设置平台默认 sans（Windows: "Segoe UI"），QSS 仅控字号令牌** | 中文由 Qt 自动 fallback 到雅黑；零资产成本 | 各平台字形略有差异（可接受） |
| B. 内嵌 Inter + 思源黑体 | 完全一致 | 约 10MB 字体资产、许可与打包成本，YAGNI |
| C. 不设全局字体（现状） | — | 各控件继承不确定，pt/px 混用 |

**决策：A**。字号收敛为令牌 `11/12/13/15` 全 px；删除 `LightRotationWidget.py:79-82` 的硬编码字体与 `algebra_panel.py:456-458` 的 22pt 强制字号。

## 2. 设计令牌规范

`design/tokens.json` 结构（片段）：

```json
{
  "$schema": "ui/tokens.schema.json",
  "font": { "family_default": "Segoe UI", "size": { "caption": 11, "body": 12, "subtitle": 13, "title": 15 } },
  "space": { "s1": 4, "s2": 8, "s3": 12, "s4": 16, "s5": 24, "s6": 32 },
  "radius": { "sm": 4, "md": 8, "lg": 10 },
  "motion": { "duration": { "fast": 120, "normal": 150, "slow": 200 }, "easing_out": "cubic-bezier(0.33, 1, 0.68, 1)" },
  "themes": {
    "light": {
      "bg":  { "canvas": "#eef1f4", "panel": "#ffffff", "elevated": "#f5f7f9", "overlay": "#ffffff", "scene": "#f4f6f9" },
      "text": { "primary": "#17212e", "secondary": "#3f4c5c", "muted": "#66788c", "on_accent": "#ffffff" },
      "border": { "subtle": "#eceff3", "default": "#d5dbe3", "strong": "#b8c2cd" },
      "accent": { "default": "#2f7ebd", "hover": "#3a8cd0", "pressed": "#2970ab", "soft_bg": "#e4f0f9" },
      "status": { "success": "#16825d", "warning": "#8a5a00", "error": "#b42318" },
      "shadow": { "overlay": "0 1px 3px rgba(23,33,46,.10), 0 4px 12px rgba(23,33,46,.08)",
                  "modal": "0 4px 8px rgba(23,33,46,.10), 0 12px 32px rgba(23,33,46,.14)" }
    },
    "dark": {
      "bg":  { "canvas": "#1a1b1e", "panel": "#202124", "elevated": "#26282c", "overlay": "#24262a", "scene": "#1e1f23" },
      "text": { "primary": "#e8eaed", "secondary": "#b3b8c0", "muted": "#8a9099", "on_accent": "#0b1220" },
      "border": { "subtle": "#33363b", "default": "#3c4046", "strong": "#52565e" },
      "accent": { "default": "#4c9ee8", "hover": "#5fabef", "pressed": "#418fd9", "soft_bg": "rgba(76,158,232,.16)" },
      "status": { "success": "#4ec9b0", "warning": "#cca700", "error": "#f48771" },
      "shadow": { "overlay": "0 1px 3px rgba(0,0,0,.40), 0 6px 16px rgba(0,0,0,.32)",
                  "modal": "0 4px 8px rgba(0,0,0,.44), 0 16px 40px rgba(0,0,0,.40)" }
    }
  }
}
```

要点：
- 5 种遗留灰（`#d9dde3`/`#d0d7df`/`#cbd3dd`/`#dfe3e8`/`#e0e5ea`）收敛为 `border` 三档；遗留 accent `#3794ff`/`#006ab1` 废弃。
- **色阶分隔**（§11.4）：light `canvas` 从 `#f7f8fa` 加深为 `#eef1f4`，使"面板亮于画布"的层级在无边框分隔下仍可辨；新增 `bg.scene` 供 3D/2D 画布 auto 背景使用（比 canvas 略亮，利于曲面显示）。
- **圆角修订**（§11.6）：`md` 6→8（按钮/输入/卡片/工具栏），`lg` 8→10（弹层/对话框），统一现代教育工具的柔和质感；代码中 4/5/6/7/8px 混用全部收敛。
- **阴影两级**：`overlay`（工具栏/小弹层）、`modal`（对话框/大弹层）。
- **动效令牌**（§11.7）：`fast 120 / normal 150 / slow 200ms` + 统一 ease-out 曲线（近似 Qt `OutCubic`，Qt 侧动画沿用 `QEasingCurve::OutCubic`）。
- 暗色 `status` 沿用现 Web 侧栏暗色值（已验证视觉）；亮色沿用 Qt 现值。
- 对比度预算：`text.muted` on `bg.panel`——light `#66788c`/`#ffffff` ≈ 4.6:1，dark `#8a9099`/`#202124` ≈ 4.7:1，均过 AA。
- `ui/tokens.py` 启动时校验：两主题键集一致、颜色可被 `QColor` 解析、字号/时长为正整数；失败抛 `TokenError` 快速失败。

## 3. Qt QSS 模板架构

`ui/styles/base.qss.in`（片段，`$` 引用展平后的令牌键）：

```css
QMainWindow, #viewportHost { background: $bg_canvas; }
#algebraPanel, #agentSidebar { background: $bg_panel; }  /* 色阶分隔：无 1px 边框 */
#algebraTitle { color: $text_primary; font-size: ${size_title}px; font-weight: 600; }
QLineEdit, QComboBox { min-height: 30px; background: $bg_panel; color: $text_primary;
  border: 1px solid $border_default; border-radius: ${radius_sm}px; padding: 2px 7px; }
QLineEdit:focus, QComboBox:focus { border: 2px solid $accent_default; }
#appStatusBar { background: $bg_panel; border-top: 1px solid $border_default; }
#viewportToolbar, #twoDGeometryToolbar, #twoDLineFlyout,
#layerSettingsPopup, #sceneSettingsPanel { background: $bg_overlay;
  border: 1px solid $border_default; border-radius: ${radius_md}px; }
```

`build_qss(theme)` 流程：`tokens.load()` → 递归展平为 `{ "bg_panel": "#ffffff", ... }`（主题无关键直接带前缀）→ `Template(text).substitute(mapping)`。

伪态覆盖矩阵（模板内枚举，切换主题无需改逻辑）：

| 状态 | 背景 | 文字/边框 |
|---|---|---|
| hover | `accent.soft_bg` | `border.default` |
| pressed/checked | `accent.soft_bg` | `accent.default` 文字 |
| focus | 原背景 + `2px accent.default` 边框 | — |
| disabled | `bg.elevated` | `text.muted` |

删除的死选择器：`#agentPanel`、`#agentSidebar`、`#agentCollapsedBar`、`#agentCollapsedLabel`、`#agentNav*`、`#agentTitle`、`#agentStatus`、`#agentModeHint`、`#agentMessageScroll`、`#agentUserBubble`、`#agentAssistantBubble`、`#agentPlanCard`、`#agentPlanProblems`、`#agentPromptEdit`、`#agentSendButton`（`designer_window.py:3024-3039`，全部服务于已退役的 Qt 聊天面板）。

## 4. Web 主题管线

### 4.1 构建期

`ui/agent_web/scripts/gen-theme.mjs` 读取 `design/tokens.json`，生成 `src/styles/theme.css`：

```css
:root, :root[data-theme="light"] { --agent-bg: #f7f8fa; --agent-surface: #ffffff; /* … */ }
:root[data-theme="dark"] { --agent-bg: #1a1b1e; --agent-panel: #202124; /* … */ }
```

- 删除 `theme.css` 现有 `color-scheme: dark` 默认与 `@media (prefers-color-scheme: light)` 分支（`theme.css:2-18`）。
- `color-scheme` 属性由 `[data-theme]` 匹配设置（`light`/`dark`），保证原生滚动条与表单控件跟随。
- `tokens.json` 缺失/损坏时脚本使用内置浅色副本并 `console.warn`，不阻断构建。
- `layout.css` 中全部字面量颜色改语义变量：`#fff` → `var(--agent-text-on-accent)`、`rgb(0 0 0 / 30%)` 阴影 → `var(--agent-shadow-overlay)`。

### 4.2 运行时（首帧 + 切换）

**首帧（URL 参数 + UserScript）**：

```python
# agent_sidebar_web.py
def _initial_url(self) -> QUrl:
    mode = self._theme_provider()          # 回调，返回 "light" | "dark"
    return QUrl(f"mathagent://app/index.html?theme={mode}")
```

```js
// UserScript, injectionPoint: DocumentCreation, runsOnSubFrames: false
(function () {
  var m = new URLSearchParams(location.search).get("theme");
  document.documentElement.setAttribute("data-theme", m === "dark" ? "dark" : "light");
})();
```

UserScript 注册在 `defaultProfile().scripts()`（应用仅加载 mathagent:// 文档，无泄漏面）。`DocumentCreation` 早于文档任何 CSS 求值，首帧即正确主题。

**运行时切换（事件，mode-only）**：

- `web_protocol.py`：`EVENT_MESSAGE_TYPES` 增加 `"theme_state"`；payload 校验 `mode ∈ {"light","dark"}`（复用现有 envelope 校验路径）。
- `agent_sidebar_web.py` 新增：

```python
def set_theme(self, mode: str) -> None:
    self._theme_mode = mode
    if self._loaded:
        self._emit_theme()
    # 未加载完成时无需缓存补发：URL 参数已保证首帧，下次切换事件会覆盖

def _emit_theme(self) -> None:
    self.bridge.emit_event({"protocol_version": 1, "type": "theme_state",
                            "request_id": "theme-state", "session_id": "",
                            "payload": {"mode": self._theme_mode}})
```

- React：reducer 处理 `theme_state` → `document.documentElement.setAttribute("data-theme", mode)`（与 UserScript 幂等）；根容器颜色属性加 `transition: background-color .15s, color .15s`。
- 隐藏面板切换主题：文档常驻，事件照常送达，重新展开时主题已同步（无需 v1 的"待发缓存"设计，仅 `loadFinished` 前丢弃的事件由 URL 参数兜底）。

## 5. 状态栏设计

结构（`designer_window.py` 新增 `_build_status_bar()`，插入在 rootLayout 下方——注意 rootLayout 为水平布局，状态栏改为包一层 `QVBoxLayout`：`root(v) → contentRow(h: algebra|viewport|handle|agent) + statusBar`）：

| 段 | 内容 | 数据源（现有） | 交互 |
|---|---|---|---|
| 模式 | `2D 绘图` / `3D 场景` | `self.scene_mode`（`_sync_scene_controls` 已集中同步） | 无 |
| 工具胶囊 | `● 放置点` 等 | `self._active_2d_tool` | 无（仅 2D 且有激活工具时显示） |
| 渲染 | `渲染 128ms` / 错误摘要 | `_render_scene` 现有计时 | 无 |
| Agent | 圆点 + `未配置 / 就绪 / 生成中` | `agent_sidebar.set_model_status`/`set_busy` 的既有状态 | 点击 = `_toggle_agent_panel` |
| 弹性 | — | — | — |
| 主题 | sun/moon/monitor 图标 | QSettings `ui/theme` | 点击循环 light→dark→system |

- 高 30px；`objectName="appStatusBar"`；QSS 令牌化；Agent 圆点色用 `status.*` 令牌（替代 `agent_sidebar.py:83` 的内联 `#4ADE80/#F59E0B/#6B7280`）。
- `MainWindow` 增加 `agent_status_changed = Signal(str, str)` 转发（或直接以回调注入 sidebar），避免状态栏直接耦合 Web 桥。

## 6. 两侧面板宽度手柄

单一参数化组件，两个实例分别服务左栏与右栏：

```python
class _PanelResizeHandle(QWidget):
    """5px 宽竖条，拖拽调整相邻面板宽度。`grow_direction` 指示拖动方向与增宽的关系。"""

    def __init__(self, panel: QWidget, *, settings_key: str,
                 min_width: int, default_width: int, max_width: int,
                 grow_left: bool):
        super().__init__()
        self.setFixedWidth(5)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setObjectName("panelResizeHandle")
        self._panel, self._settings_key = panel, settings_key
        self._min, self._default, self._max = min_width, default_width, max_width
        self._grow_left = grow_left   # 面板在手柄左侧（右栏）：向左拖增宽；面板在右侧（左栏）：向右拖增宽
        self._origin_x, self._origin_width = 0.0, 0

    def mousePressEvent(self, e):  # 记录起点
        self._origin_x = e.globalPosition().x(); self._origin_width = self._panel.width()

    def mouseMoveEvent(self, e):
        raw = e.globalPosition().x() - self._origin_x
        delta = -raw if self._grow_left else raw
        width = max(self._min, min(self._max, self._origin_width + int(delta)))
        self._panel.setFixedWidth(width)

    def mouseReleaseEvent(self, e):  # 持久化
        QSettings(...).setValue(self._settings_key, self._panel.width())

    def mouseDoubleClickEvent(self, e):  # 双击恢复默认
        self._panel.setFixedWidth(self._default)
```

实例化（`designer_window.py`）：

```python
# 左栏手柄：面板在手柄右侧，向右拖增宽；常驻
self.algebra_handle = _PanelResizeHandle(self.algebra_panel, settings_key="ui/algebra_panel_width",
    min_width=260, default_width=320, max_width=420, grow_left=False)
root_layout.insertWidget(1, self.algebra_handle)          # algebraPanel(0) | handle(1) | viewportHost(2)
# 右栏手柄：面板在手柄左侧，向左拖增宽；随 Agent 面板显隐
self.agent_handle = _PanelResizeHandle(self.agent_sidebar, settings_key="ui/agent_panel_width",
    min_width=360, default_width=440, max_width=560, grow_left=True)
root_layout.insertWidget(3, self.agent_handle)            # viewportHost(2) | handle(3) | agentSidebar(4)
```

- `_toggle_agent_panel` 展开时 `agent_handle.show()`、收起时 `agent_handle.hide()`；左栏手柄常驻。
- `AgentSidebar.expand()`（`agent_sidebar.py:292`）从 `setFixedWidth(440)` 改为 `setFixedWidth(存储宽度 or 440)`；三处 `setFixedWidth(440)`（`designer_window.py:359`、`agent_sidebar.py:142/292/304`）统一走常量。
- `algebra_panel.py:538-539` 的 `setMinimumWidth(300)/setMaximumWidth(360)` 改为 260/420，并在 `designer_window` 装配时以 `setFixedWidth(QSettings 读取 or 320)` 初始化。
- 与 `_ViewportResizeFilter` 相容性：手柄是普通 QWidget，viewportHost 父子关系与布局项不变，原生 VTK 视口 resize 事件流不受影响（相比 QSplitter 方案的关键优势）。
- `AgentCollapsedBar`（40px 死类，`agent_sidebar.py:34-72`）删除；`AgentSidebarState` 注释与常量统一为 `MIN 360 / DEFAULT 440 / MAX 560`。
- 手柄视觉：QSS `#panelResizeHandle { background: transparent; }` + `:hover { background: $accent_soft_bg; }`（5px 命中区偏窄，实际实现将 `setFixedWidth(9)` 且绘制 5px 视觉线，兼顾命中与美观——若保留 5px 则接受较小命中区，实现时二选一并记录）。

## 7. 图标模块

`ui/icons.py`：

```python
_SVGS: dict[str, str] = {  # 内嵌 lucide 24x24 stroke SVG（stroke="currentColor"）
    "settings-2": '<svg xmlns="..." stroke="currentColor" ...>...</svg>',
    "sparkles": "...", "sun": "...", "moon": "...", "monitor": "...",
    "play": "...", "circle-dot": "...", "slash": "...", "type": "...",
    "undo-2": "...", "redo-2": "...", "ellipsis": "...",
}

def icon(name: str, color: str, size: int = 16) -> QIcon:
    key = (name, color, size, _dpr())
    if key in _CACHE: return _CACHE[key]
    svg = _SVGS[name].replace("currentColor", color)
    renderer = QSvgRenderer(svg.encode("utf-8"))
    dpr = _dpr()
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr); pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm); renderer.render(painter, QRectF(0, 0, size, size)); painter.end()
    _CACHE[key] = QIcon(pm); return _CACHE[key]
```

替换映射（现 Unicode → lucide 名）：

| 位置 | 现 | 新 |
|---|---|---|
| 视口主工具栏 | ⚙ | `settings-2` |
| 视口主工具栏 | ✦ | `sparkles` |
| 视口主工具栏 | `2D`/`3D` 文字 | 保留文字（语义清晰，不强换图标） |
| 2D 工具栏 | ➤ ● ╱ `#` ↶ ↷ | `play` / `circle-dot` / `slash` / `type` / `undo-2` / `redo-2` |
| 左面板工具行 | `+` / `⋮` | `plus` / `ellipsis` |
| 状态栏主题 | — | `sun` / `moon` / `monitor`（按模式） |
| 状态栏 Agent | 🤖/圆点 | 纯色圆点（`QRadialGradient` 或 8px `circle` SVG） |

图标颜色：默认 `text.secondary`，hover `text.primary`，激活 `accent.default`；由按钮状态在 `enterEvent/leaveEvent` 或 QSS 无法驱动 QIcon 换色，统一采用"工具栏按钮按 checked/hover 重取 icon"（`_install_viewport_toolbar` 内绑定）。按钮规格统一 **36×36、图标 16px**（自 38×38 收敛为统一规格；教学投影场景保留足够命中区，详见 §11.5）；图层行内小按钮（可见性）28×28。

## 8. 场景背景 auto 语义迁移

- `models/scene_mode.py`：`SceneAppearance.background` 值域 `"light" | "dark"` → `"auto" | "light" | "dark"`，默认 `auto`；序列化兼容（旧值原样读入，语义为显式覆盖）。
- `scene_settings.py:38-39`：combo 增加 `("跟随主题", "auto")` 置首；`set_values` 的 `findData` 回退逻辑天然兼容。
- `rendering/scene.py` 背景 & `rendering/two_d_scene.py:88` 网格色：`auto` → 查询有效主题令牌（背景取 `bg.scene`，网格暗亮两档）；显式值走原逻辑。
- 主题切换时：遍历 `self.scene_appearances`，含 `auto` 的模式触发一次视口重渲（单次 `render()` 成本可接受）。

## 9. 时序与竞态分析

| 场景 | 序列 | 结果 |
|---|---|---|
| 冷启动（dark） | QSettings 解析 → `build_qss(dark)` → `window.show()`；WebView 构造即 `setUrl(...?theme=dark)` → UserScript(DocumentCreation) 设 `data-theme` | 首帧即深色，无闪烁 |
| 运行中切换 | 状态栏点击 → QSettings 写入三态 → 重算有效主题 → `setStyleSheet(重渲)` → `set_theme(mode)` → 事件 → React 切 `data-theme`（.15s 过渡）→ `auto` 场景重渲 | Qt/Web/画布同帧级同步（百毫秒内） |
| 面板隐藏时切换 | 同上，事件照发（文档常驻） | 重新展开即正确主题 |
| `system` 模式下 OS 切换 | `QStyleHints.colorSchemeChanged` → 同"运行中切换" | 无需重启 |
| `loadFinished` 前发生切换 | 事件可能丢失 | URL 参数已定首帧；下一次切换事件覆盖；无错误状态 |
| WebView 加载失败（dist 缺失） | 现有 `show_error` 流程 | 主题功能随 Web UI 一同降级，Qt 侧不受影响 |
| `theme_state` 与快照并发 | 正交状态，reducer 独立分派 | 无顺序依赖 |
| 窗口最小宽度 1024px | 左 MIN 260 + Agent MIN 360 + 视口 ≥ 300 + 双手柄 2×5 + 状态栏不换行 | 布局成立（合计 930）；状态栏文字省略号截断 |

## 10. 测试矩阵

**Python（pytest）**
- `tokens`：两主题键集一致、`build_qss` 输出不含 `$` 残留、QSS 含关键选择器（`#appStatusBar`）、不含死选择器（`#agentPanel` 等）；令牌 JSON schema 校验失败即 `TokenError`。
- 主题：三态→有效主题解析、QSettings 往返、`colorSchemeChanged` 联动（`qtbot` 模拟）。
- 协议：`theme_state` envelope 序列化（mode 校验、非法值拒收、无凭据字段）；`set_theme` 在 `_loaded=False` 时不抛错。
- 手柄：参数化双实例——左栏钳制 [260, 420]/默认 320/`ui/algebra_panel_width`，右栏钳制 [360, 560]/默认 440/`ui/agent_panel_width`；双击复位、QSettings 持久化往返、拖动方向语义（左栏向右拖增宽、右栏向左拖增宽）。
- 场景：`background="auto"` 解析与旧值兼容（`light/dark` 视为覆盖）；auto 时主题切换触发重渲计数。
- 布局：删除死文件后 `test_main_window_layout` 断言仅存活部件。

**React（vitest）**
- `theme_state` 事件 → `documentElement.dataset.theme` 断言；无 `prefers-color-scheme` 匹配（源码 grep 断言）。
- 生成 CSS：两主题变量完整性、无字面量颜色（lint 规则）。
- 360/440/560 三宽度布局（沿用现有 320/440 边界测试模式）。

**集成**
- Qt↔Web：`set_theme("dark")` 后（等 `loadFinished`）断言 `runJavaScript("document.documentElement.dataset.theme") === "dark"`。
- 首帧：URL 参数含 `theme=dark` 时 UserScript 注入断言（`DocumentCreation` 后立即求值）。
- 回归：现有 2D/3D 渲染、桥接协议、会话流程测试全绿；`openspec validate --strict`。

## 11. 视觉设计方向（UI 美学层，头脑风暴 v3）

> 本节回答"软件应该长什么样"：在令牌/主题/布局机制（§1–§10）之上，定义风格方向、布局构图、组件质感与动效节奏。

### 11.1 美学诊断——"不好看"的具体归因

| # | 问题 | 代码证据 | 视觉后果 |
|---|---|---|---|
| 1 | 边框泛滥：面板分隔、图层行、按钮、弹层、工具栏全部 1px 边框 | `_apply_style` 中 20+ 处 `border:` | 界面被网格线切碎，嘈杂 |
| 2 | 层次平面化：无阴影体系，弹层与背景几乎无层级差 | 弹层仅 `1px #d0d7df` 边框 | 浮层"贴"在画布上，无悬浮感 |
| 3 | 圆角随机：4/5/6/7/8px 混用 | `border-radius: 4/5/6/7/8px` 并存 | 组件质感不统一 |
| 4 | 控件规格混乱：38px（工具栏）/ 40×40（图层设置钮）/ 28×28（可见性）/ 30px（输入） | `designer_window.py`、`algebra_panel.py:448/459` | 无网格感，对齐失效 |
| 5 | 元素拥挤：图层行 6px 内边距、工具栏 4px 内距贴边 | `algebra_panel.py:443` | 呼吸感缺失，显"旧" |
| 6 | 无动效语言：hover 瞬时变色、弹层直出直入（仅场景设置面板有 180ms 动画） | QSS 无 transition 等价物 | 交互生硬 |
| 7 | 后实装的案例组件未纳入规范：`MathCaseView` 卡片 5px 圆角 + 1px 边框；`LinearAlgebraCasePopup` 无 QSS 覆盖（裸弹窗）；案例标签 `.session-tab-case` 无类型区分样式 | `layout.css`（math-case-*）、`algebra_panel.py:426-517` | 新功能沿用旧视觉，与美学方向脱节 |

### 11.2 风格方向探索（3 方案）

| 方案 | 特征 | 代表 | 适配度 |
|---|---|---|---|
| A. 专业工具风 | 高信息密度、小圆角（4px）、暗边框、紧凑 | VS Code / Figma | 教学投影场景显冷，学生亲和度低；Agent 侧栏已是此风格，会形成"双人格" |
| **B. 现代教育工具风（推荐）** | 色阶分隔、卡片化对象、柔和圆角（8px）、充足留白、克制用色 | GeoGebra × Linear/Notion 融合 | 匹配软件混合身份：GeoGebra 式教学亲和力 + Linear 式现代精致感；投影可读性强 |
| C. 学术教科书风 | 衬线字体、分栏排版、装饰性元素 | 电子教材 | 不适合交互工具；装饰与功能竞争注意力 |

**决策：B**。设计关键词：**画布中心、安静、有序、可触摸**。

### 11.3 五条设计原则

1. **画布中心**：数学对象（曲面、曲线）是唯一主角；UI 装饰（边框、阴影、色彩）全部退后，中性灰阶承载界面，品牌蓝只出现在"动作"与"激活"上。
2. **色阶分隔**：区域之间用背景色阶（`panel` 亮于 `scene` 亮于 `canvas`）表达层级，不再画 1px 分隔线；边框只保留给"控件"（输入、卡片、弹层）。
3. **卡片化对象**：公式与图层是内容卡片（elevated 底、8px 圆角、柔和 hover），工具控件是附着在卡片上的辅助元素，而非喧宾夺主的按钮墙。
4. **克制用色**：每屏彩色面积 < 5%；图层色仅以色条/圆点形式出现；语义色（成功/警告/错误）只用于状态。
5. **节奏感**：所有间距取自 4px 倍数阶梯（4/8/12/16/24/32），控件高度取自 28/32/36 三档，拒绝随机数值。

### 11.4 布局构图

**整体（1320×820 默认，最小 1024px）**：

```
┌────────────┬─┬──────────────────────────────┬─┬──────────────┐
│ Algebra    │▐│                              │▐│ MathAgent    │
│ Panel      │▐│        3D/2D 画布            │▐│ Sidebar      │
│ 260–420    │▐│   ┌──────────┐               │▐│ 360–560      │
│ (默认 320) │▐│   │ ⚙ 2D ✦  │ ← 右上悬浮工具栏│▐│ (默认 440)   │
│            │▐│   └──────────┘               │▐│              │
│            │▐│                    ┌───┐     │▐│              │
│            │▐│                    │2D │ ← 右侧居中悬浮工具  │▐│              │
│            │▐│                    └───┘     │▐│              │
├────────────┴─┴──────────────────────────────┴─┴──────────────┤
│ 2D绘图 ●放置点 · 渲染128ms · ●就绪        · · ·    ☀/☾ 主题 │ ← 30px 状态栏
└──────────────────────────────────────────────────────────────┘
  ▐ = 5px 拖拽手柄（左栏手柄常驻，右栏手柄随面板显隐）
  面板与画布之间：无边框，色阶分隔（panel 亮 / scene 中 / canvas 沉）
```

**左栏内部（重设计后）**：

```
┌─ AlgebraPanel ────────────────┐
│  空间解析几何                  │  15px/600（title）
│  Math3D Teaching              │  11px/muted（副标题）
│                               │
│  ╭──────────────────────────╮ │
│  │ x²/a² + y²/b² − z²/c² = −1 │ │  公式卡：elevated 底、8px 圆角、12px 内距
│  ╰──────────────────────────╯ │
│                               │
│  [＋ 新增公式]  [ƒ 函数]       │  32px 高主按钮（accent soft）+ 次按钮
│                               │
│  图层                          │  节标题：11px/500/muted/字距 0.06em
│  ╭──────────────────────────╮ │
│  │ ▌ 👁  sin(x)·cos(y)     ⋯ │ │  图层行 ×N（§11.5）
│  ╰──────────────────────────╯ │
└───────────────────────────────┘
```

### 11.5 组件设计规范

**图层行 LayerRow**（现状：`algebra_panel.py:425-463`，48px 高 + 灰底 1px 边框 + 40×40/22pt 设置钮）：

```
默认态：                          hover / 选中态：
╭──────────────────────────╮      ╭──────────────────────────╮
│▌👁  x²/a² + y²/b² = 1   ⋯│      │▌👁  x²/a² + y²/b² = 1   ⋯│
╰──────────────────────────╯      ╰──────────────────────────╯
 elevated 底，无边框               hover: border.default 出现
 4px 左色条（图层色）              选中: accent 边框 + soft_bg 底
```

- 规格：高 48px（保持）；`bg.elevated` 底、`radius.md` 8px 圆角、**默认无边框**、hover 时出现 `border.default`、选中时 `accent.default` 边框 + `accent.soft_bg` 底。
- 左侧 4px 色条渲染图层颜色（替换弹层内颜色按钮的主标识职责；颜色编辑仍在设置弹层）。
- 可见性按钮 28×28，`eye`/`eye-off` 图标替代字符勾选态；设置按钮从 40×40/22pt ⋮ 收敛为 28×28 `ellipsis` 图标。
- 行间距 6px（列表内节奏），行内边距 8px。

**视口悬浮工具栏**：

```
╭────┬────┬────╮
│ ⚙  │ 2D │ ✦  │   36×36 按钮，16px 图标
╰────┴────┴────╯   bg.overlay 底、radius.md、border.subtle + shadow.overlay
```

- 按钮命中区 36×36（教学投影友好；v2 的 32px 修订为 36px），组间 4px 间距 + 1px `border.subtle` 分隔线（多组时）。
- 浮层底 `bg.overlay` + `border.subtle` 1px + `shadow.overlay`；**不再用纯白实底**（dark 主题下白底会刺眼）。
- 出现/消失：150ms 透明度 + 4px 位移动画。

**控件高度三档**：图标按钮 36px（工具栏/工具行）、表单控件 32px（输入/下拉/主按钮，自 30px 修订）、行内小按钮 28px（图层行内）。

**弹层与对话框**：`radius.lg` 10px + `border.default` 1px + 阴影（小弹层 `shadow.overlay`、对话框 `shadow.modal`）；无边框方案被否决——3D 画布内容复杂时无边框浮层边界会丢失，边框降级为 `subtle/default` 而非取消。

**状态栏**：30px 高、`bg.panel` 底 + 1px `border.default` 上边框（状态栏是"栏"，保留分隔线）；各段 11px `text.muted` 文字、段间 12px 间距 + `·` 分隔符；可点击段（Agent/主题）hover 时 `bg.elevated` + 4px 圆角；主题按钮 24×24。

**节标题**（"图层"/"函数目录"等分组标签）：11px / 500 / `text.muted` / 字距 0.06em（中文无 uppercase 模式，用字距表达层级）。

**焦点环**：键盘焦点 `2px accent.default` 外描边 + 2px offset（QSS `outline` 不支持 offset，用 `border: 2px solid $accent_default; padding: 0` 组合实现）；鼠标点击不显示焦点环（`:focus` 仅限键盘，Qt 侧以 `focusPolicy` + 事件过滤近似 `:focus-visible`）。

### 11.6 圆角与阴影使用规则

| 档位 | 值 | 用途 |
|---|---|---|
| `radius.sm` | 4px | checkbox、小标签、色条 |
| `radius.md` | 8px | 按钮、输入、卡片、图层行、工具栏浮层 |
| `radius.lg` | 10px | 弹层、对话框、场景设置面板 |

| 阴影 | 用途 |
|---|---|
| `shadow.overlay` | 悬浮工具栏、小弹层、下拉 |
| `shadow.modal` | 对话框（LightingDialog 等）、大型弹层 |

### 11.7 动效规范

| 场景 | 时长 | 曲线 | 实现 |
|---|---|---|---|
| hover 颜色/背景过渡 | 120ms | ease-out | Web: CSS transition；Qt: 无内建 transition，采用 `QVariantAnimation` 或直接瞬时（hover 瞬时在本规范内可接受，Qt 侧不做颜色动画） |
| 弹层/浮层出现 | 150ms | ease-out | 透明度 + 4px 位移 |
| 面板展开/收起 | 200ms | `OutCubic` | 沿用场景设置面板现有 `QPropertyAnimation` 模式（现 180ms → 统一 200ms） |
| 主题切换 | 150ms | ease-out | Web CSS 变量过渡（已定）；Qt 侧 `setStyleSheet` 瞬时（可接受） |

- Qt 侧动画时长常量化到 `ui/tokens.py`（`MOTION_FAST/NORMAL/SLOW`），便于未来全局减速/关闭。
- Web 侧 `@media (prefers-reduced-motion: reduce)` 将所有 transition 归零；Qt 侧暂不提供开关（列为后续增强）。

### 11.8 深色主题视觉要点

- 层级方向与浅色一致：`panel`(#202124) 亮于 `scene`(#1e1f23) 亮于 `canvas`(#1a1b1e)，保证"色阶分隔"在暗色下同样成立。
- 暗色阴影更深（`shadow.overlay/modal` 已按 40%+ 不透明度定义）；`accent.soft_bg` 用 rgba 16% 而非实色，避免暗底上的色块感。
- 图层行 elevated `#26282c` 与 panel `#202124` 保持一档色阶差；hover 边框用 `border.strong`（暗色下 `default` 对比不足）。
- 画布 `#1e1f23` 略亮于窗口底——3D 曲面的暗色描边与网格（`#3d4650`/`#4a545f`）在其上保持可读。

### 11.9 本节对前版的修订汇总

1. light `canvas` `#f7f8fa` → `#eef1f4`；新增 `bg.scene`（§2 令牌表已同步）。
2. `radius.md` 6→8、`radius.lg` 8→10；新增 `shadow.modal` 与 `motion` 令牌（§2 已同步）。
3. 面板分隔从 1px 边框改为色阶分隔（§3 模板已同步去 `border-right`）。
4. 工具栏按钮规格 32px → **36px**（§7 已同步）；表单控件 30px → 32px。
5. 3D/2D auto 背景取 `bg.scene` 而非 `bg.canvas`（§8 已同步）。
6. 新增图层行卡片化、节标题模式、焦点环、动效规范——对应 specs/tasks 新增条目。

## 12. 代数案例 UI 设计（对齐后续实装代码）

> 背景：本 spec 初稿之后，`natural-language-plotting-agent` 相关工作已实装代数案例功能（Qt 案例弹窗 + 侧栏案例标签页 + `math_case` 桥接事件）。本节将这些实装的 UI 纳入设计体系，修正其与 §11 美学规范的偏差。

### 12.1 实装现状（代码事实）

| 层 | 组件 | 位置 |
|---|---|---|
| 数据 | `LinearAlgebraCase`（id/category/name/formula/steps/conclusion/summary/plan） | `models/linear_algebra_cases.py` |
| Qt 入口 | `LinearAlgebraCasePopup`（分组弹窗）+ `LinearAlgebraCaseRow`（标题+摘要两行卡片）+ 工具栏"线性代数"按钮 | `algebra_panel.py:426-517, 645-655` |
| 交互流 | 选案例 → `scene.clear(all)` + 案例 plan → 自动展开 Agent 面板 → `show_math_case()` | `designer_window.py:1899-1924` |
| 桥接 | `math_case` 事件（payload 有界：case_id≤128、steps≤12×512 等；未加载完时 `_pending_math_case` 缓存，loadFinished 后 replay） | `agent_sidebar_web.py:150-190`、`web_protocol.py:80/204` |
| Web 状态 | `CaseProjection` + reducer：收到事件 upsert 并激活 `activeTab=case:<id>`；`close_case` 回退当前会话 | `reducer.ts:218-225, 283-287` |
| Web 视图 | `MathCaseView`（分类 eyebrow → h1 → summary → 公式卡 → 编号步骤 → 结论卡）；`SessionTabs` 双类型标签 | `MathCaseView.tsx`、`SessionTabs.tsx` |

### 12.2 设计决策

**D9 案例标签的类型区分**

| 方案 | 优点 | 缺点 |
|---|---|---|
| A. **标签内 12px `book-open` 图标 + 名称** | 一眼区分内容类型；与会话标签同构 | 标签宽度略增 |
| B. 前缀色点 | 极简 | 语义弱（与状态圆点混淆） |
| C. 不区分（现状） | 零成本 | 会话与案例混排无法辨认 |

**决策：A**。`.session-tab-case` 增加 `book-open` 图标（`text.muted` 色，激活时 `accent.default`）；案例标签**总是可关闭**（现状保持），关闭回退当前会话标签（reducer 已实现）。

**D10 案例标签的持久性**

| 方案 | 决策 |
|---|---|
| A. **瞬态**（现状）：案例标签仅存于 reducer 内存，WebView 重载即失；案例内容可由 Qt 弹窗随时重新推送 | ✅ 采用——案例是"教学内容卡片"，不是工作产物；`math_case` 重发幂等（同 id upsert） |
| B. 持久化到会话存储 | 否决——引入存储迁移与过期语义，超出案例定位 |

**D11 阅读页排版层级**

| 方案 | 决策 |
|---|---|
| A. **文档排版独立于界面 chrome**：阅读页 h1 用 20px/600（内容标题），界面面板标题仍 15px（chrome） | ✅ 采用——案例页是"教科书页"而非"面板"，阅读场景需要更强层级 |
| B. 统一 15px | 否决——阅读页标题与 UI 标题同档会显平 |

### 12.3 案例阅读页版式规范（MathCaseView 令牌化）

```
┌─ math-case-view（620px 阅读列居中）─────────────────┐
│  向量                          ← eyebrow：11px accent/500
│  向量加法                       ← h1：20px/600 text.primary
│  用平行四边形法则演示向量加法     ← summary：12px muted
│
│  ╭──────────────────────────╮
│  │      a + b = (3, 3)      │   ← 公式卡：KaTeX 块级居中，elevated 底，
│  ╰──────────────────────────╯     radius.md 8px，默认无边框（§11 卡片规范）
│
│  1. 从原点 O 画出向量 a=(2,1)…   ← 编号步骤：13px/1.7 行高，Markdown 内联公式
│  2. 将 b 平移到 a 的终点…          序号用 accent 色（list-style 定制）
│  3. 从 O 指向对角点 C…
│
│  ╭──────────────────────────╮
│  │ 结论                      │   ← 结论卡：同公式卡规范 + h2 13px/600
│  │ 向量加法可用平行四边形法则…  │
│  ╰──────────────────────────╯
└────────────────────────────────────────────┘
```

- 现状 CSS 的 `border-radius: 5px` + `border: 1px solid var(--agent-border)` → 改为 `radius.md` + 默认无边框（hover 不加边框——阅读卡非交互元素，保持安静）。
- 步骤间距 12px（现 10px→12px，对齐 4px 阶梯）；`li::marker` 用 `accent.default`。
- 两主题对比度与 §11 一致（math-case 全部字面量进语义变量）。

### 12.4 案例弹窗规范（LinearAlgebraCasePopup 入 QSS 模板）

- 弹层样式按 §11.5：`#linearAlgebraCasePopup { background: $bg_overlay; border: 1px solid $border_default; border-radius: ${radius_lg}px; }` + `shadow.overlay`；出现动画 150ms 淡入 + 4px 下移（现直出直入）。
- `LinearAlgebraCaseRow`：padding 8/12px（现 9/7 → 对齐阶梯）、`radius.md`、hover `accent.soft_bg` + 左 3px accent 指示条；标题 13px/600，摘要 11px `text.muted` 最多两行省略。
- 分类标签复用节标题模式（11px/muted/字距，现复用 `#catalogCategory` 样式，随模板统一）。
- 工具栏三按钮：`+` 改 `plus` 图标按钮（36px）、`函数`/`线性代数` 文字按钮统一 32px 高（§11 控件规格），宽度按内容（现 44/72 固定宽保留语义，但高度/圆角/hover 入令牌）。

### 12.5 交互流语义

1. 用户在代数面板打开案例弹窗 → 选案例 → 弹窗关闭。
2. 场景执行 `scene.clear(all)` + 案例 plan（2D 重建）。
3. Agent 面板自动展开（若隐藏），案例以新标签页打开并激活；若同 id 案例已打开，复用标签（upsert）。
4. 案例页与会话标签并存，互不干扰；运行中的回合不受案例加载影响（案例是场景操作，非 Agent 回合）。
5. WebView 未加载完时案例缓存 replay（现状机制保留）；主题切换时案例页随 `data-theme` 即时换肤。

### 12.6 协议扩展策略（spec 化现状模式）

后续新增 Python→JS 事件（如 `math_case`）遵循：`EVENT_MESSAGE_TYPES` 白名单注册 + payload 必填字段类型校验 + 字段长度上界 + 无凭据字段；`theme_state` 与之并存互不冲突。JS 侧未知事件类型静默忽略（前向兼容）。
