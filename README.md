# Math3D Teaching

Math3D Teaching 是一个基于 PySide6、PyVista 和 SymPy 的交互式数学可视化项目，用于展示三维曲面、二维函数和空间几何关系。当前版本已扩展为一个更通用的数学教学场景：支持 2D/3D 视图切换、曲面与曲线图层管理、符号表达式输入、交线计算以及可视化参数调节。

## 项目定位

这个项目不仅限于双叶双曲面，它现在已经发展为一个数学教学和可视化工具，适合：

- 解析几何教学
- 二维/三维函数可视化
- 曲线与曲面关系展示
- 代数表达式与几何图形的对应学习
- 数学实验和课堂演示

## 功能概览

- 3D 场景与 2D 场景双模式切换
- 交互式拖拽、缩放、平移和视角控制
- 支持显式、隐式、参数式曲面输入
- 支持曲线和曲面图层的独立显示、颜色、透明度和范围控制
- 可生成和显示交线
- 内置常见二次曲面库
- 支持高级光照、材质和背景设置
- 提供数学公式输入控件与可视化层管理
- 2D 场景提供点、直线、线段、射线、向量和曲线图层
- 2D 几何支持撤销/重做、网格吸附和交互式编辑

## AI 教学助手

项目正在采用“内置助手 + 本地场景命令服务”的架构，让 AI agent 能够根据自然语言生成可验证的数学图形。AI 不直接操作鼠标，也不执行任意 Python；它只返回版本化的白名单命令计划，由本地程序负责数学计算、校验、渲染和撤销。

```text
自然语言
  -> Math Teacher Agent
  -> Skill / Prompt / Memory
  -> CommandPlan
  -> 命令校验与数学验证
  -> 用户预览/确认
  -> SceneCommandService
  -> 2D/3D 场景模型 + SymPy
  -> PyVista 渲染
```

右上角视口工具栏的 `✦` AI 图标打开右侧固定 Sidebar。Sidebar 默认保持 40px 折叠态，展开后显示 `Agent`、`Skills`、`Memory`、`Rules` 四个入口；关闭按钮或 `Esc` 会回到折叠态，聊天记录保留在当前会话中。2D 和 3D 模式都可以生成与执行对应场景的计划。

当前默认使用不依赖网络的本地数学 Agent。设置中可选择 OpenAI-compatible、DeepSeek 或本地 Provider；Base URL、API Key、模型名、Provider 和超时保存在本地 `QSettings`。连接测试在工作线程中进行，失败信息会掩码 API Key。`agent/providers/` 保留统一的 `ModelProvider` 工厂，其他兼容 `/chat/completions` 的服务可复用 OpenAI provider。

`Skills` 页面展示 geometry、calculus、linear_algebra；`Memory` 保存学习水平、图形偏好、语言和最近主题；`Rules` 编辑 `agent/instructions/math_teacher.md` 对应的用户规则。规则和记忆都通过 QSettings 保存，不使用数据库。

模型返回纯文本时会作为普通聊天回复显示，只有在明显尝试给出结构化计划却格式非法时才报协议错误。请求失败的那一轮不会写入对话历史，重试不会重复发送同一条提问。聊天消息支持 Markdown 和常用 LaTeX（如 `$\\frac{1}{2}a^2$`）显示。等待模型响应期间输入框内容不会被清空，`发送` 在输入为空或请求进行中保持禁用。计划未通过本地校验、或场景模式不匹配时，“执行计划”按钮保持禁用并说明原因；执行失败时计划会保留，便于修正后重试。

### 向量加法示例

在 2D 场景中输入：

```text
生成向量 a=(2,1) 和 b=(1,3)，从原点出发，用平行四边形法画 a+b，并显示三角形法
```

本地命令服务会确定性计算：

```text
O=(0,0), A=(2,1), B=(1,3), C=A+B=(3,4)
```

并生成以下教学对象：

- 从原点出发的向量 `a` 和 `b`
- `A -> C`、`B -> C` 两条虚线构造边
- 从 `O -> C` 的结果向量，标注 `a+b=(3,4)`
- 首尾相接的三角形法向量，以及“平行四边形法 = 三角形法”标注

执行前会在聊天消息中显示可展开的 JSON 命令计划；确认后作为一个事务应用，失败时自动回滚，成功后可撤回整组对象。模型不能调用 Qt 控件、执行任意 Python 或绕过 `SceneCommandService.validate()`；模型计算出的坐标、平行关系、曲面表达式和对象类型都由本地确定性代码校验。

### 命令接口

命令服务位于 `services/scene_commands.py`，目前支持：

- `scene.set_mode`、`scene.clear`
- `curve.create/update/delete`
- `point.upsert/point3d.upsert/delete`
- `linear.upsert/delete`
- `teach.vector_addition`
- `annotation.upsert/delete`
- `surface.create/update/delete`
- `calculus.derivative/integral_area/tangent`
- `linear_algebra.matrix_transform/determinant_area`
- `area.fill`、`geometry.intersection`
- `view.fit`、`scene.export_png`

`teach.vector_addition`、行列式面积、导数、切线和积分面积都是教学级宏命令，数学计算和展开由本地 SymPy/确定性代码完成，不依赖语言模型的数值推理。3D 曲面通过现有 `LayerSceneController` 进入 PyVista；3D 点、交线和 2D 积分填充也由宿主渲染。命令校验会拒绝未知操作、跨场景操作、非法对象类型、非有限坐标和不安全的函数类型。

### AI 功能状态

| 能力 | 状态 |
| --- | --- |
| 2D 点线/向量命令模型 | 已实现 |
| 向量加法教学宏（平行四边形法、三角形法） | 已实现 |
| 右侧 AI 抽屉、多轮聊天、计划预览和确认 | 已实现 |
| 显式/隐式/参数曲线命令协议 | 已实现 |
| OpenAI-compatible、DeepSeek、本地 Provider | 已实现 |
| Math3D MCP 本地工具层与 stdio JSON-RPC | 已实现 |
| 3D 曲面、三维点和交线计划 | 已实现 |
| Skills、Instructions、Memory、Prompt Templates | 已实现 |

## 技术栈

- Python 3.11+
- PySide6（`>=6.8,<6.9`）
- PyVista
- PyVistaQt
- SymPy
- NumPy
- SciPy
- antlr4-python3-runtime（LaTeX 公式解析）

## 项目结构

```text
Math3DTeaching/
├─ main.py                     # 程序入口，启动应用窗口
├─ pyproject.toml             # Python 项目配置与依赖声明
├─ requirements.txt           # 依赖列表
├─ README.md                  # 项目说明文档
├─ MathInputWidget/           # 可复用的 MathLive 公式输入控件包
│  ├─ __init__.py
│  ├─ api.py                  # 公式可视化接口（解析 LaTeX 并构建网格）
│  ├─ latex_converter.py      # LaTeX 与表达式转换
│  ├─ widget.py               # QWebEngineView 宿主组件
│  ├─ formula_list.py         # 公式列表面板
│  ├─ formula_popup.py        # 公式弹窗
│  ├─ inline_formula_overlay.py # 行内公式悬浮层
│  ├─ mathlive.js             # 本地 MathLive 运行时与字体
│  └─ README.md               # 组件使用说明
├─ widgets/                   # 自定义 Qt 控件
│  ├─ __init__.py
│  └─ LightRotationWidget.py  # 灯光方位角圆环控件
├─ geometry/                  # 几何计算与数学表达式处理
│  ├─ __init__.py
│  ├─ cas_curve.py            # 曲线 CAS 解析
│  ├─ cas_surface.py          # 曲面 CAS 解析与网格构造
│  ├─ hyperboloid.py          # 双叶双曲面等主要几何体实现
│  ├─ intersection.py         # 曲面网格交线计算
│  ├─ standard_surfaces.py    # 内置标准二次曲面定义
│  └─ ...
├─ models/                    # 数据模型
│  ├─ __init__.py
│  ├─ curve_layer.py          # 曲线图层数据结构
│  ├─ function_catalog.py     # 函数目录与表达式列表
│  ├─ geometry_2d.py          # 二维交互几何对象（点、线、向量、标注）
│  ├─ parameters.py           # 参数模型
│  ├─ scene_mode.py           # 2D/3D 场景模式定义
│  ├─ surface_layer.py        # 曲面图层数据结构
│  └─ ...
├─ services/                  # AI provider 与受限场景命令服务
│  ├─ scene_commands.py       # CommandPlan、校验、事务命令和教学宏
│  ├─ agent_provider.py       # Agent 数据契约、本地/HTTP provider
│  ├─ agent_worker.py         # Qt 工作线程中的 Agent 调用
│  └─ ...
├─ agent/                     # Math Teacher Agent 运行时
│  ├─ runtime.py              # 统一响应/校验/执行门面
│  ├─ agent.py                # Math Teacher Agent
│  ├─ skill_manager.py        # Skill 发现与计划生成
│  ├─ memory.py               # QSettings JSON 学习记忆
│  ├─ instruction.py          # 用户规则存储
│  ├─ prompt_manager.py       # teach/visualize/prove 模板
│  ├─ mcp_server.py           # 本地 Math3D MCP（stdio JSON-RPC）
│  ├─ providers/              # OpenAI、DeepSeek、本地 Provider
│  ├─ instructions/           # math_teacher.md 默认规则
│  ├─ prompts/                # 教学提示词模板
│  └─ skills/                 # geometry/calculus/linear_algebra
├─ skills/                    # 兼容入口，复用 agent.skills 实现
├─ rendering/                 # 视图渲染与场景构建
│  ├─ __init__.py
│  ├─ axis.py                 # 坐标轴绘制
│  ├─ curve_scene.py          # 曲线场景渲染器
│  ├─ geometry_scene.py       # 二维几何对象渲染与命中检测
│  ├─ helper.py               # 辅助线与参考线
│  ├─ lighting.py             # 光照参数定义
│  ├─ materials.py            # 材质和颜色配置
│  ├─ scene.py                # 三维场景构建与更新
│  ├─ ticks.py                # 坐标轴刻度与可见边界计算
│  ├─ two_d_scene.py          # 二维场景渲染
│  └─ layer_scene.py          # 图层式渲染控制器
├─ ui/                        # 用户界面及交互逻辑
│  ├─ __init__.py
│  ├─ agent_panel.py          # 右侧聊天抽屉、计划卡片与确认
│  ├─ agent_settings.py       # QSettings 配置和连接测试
│  ├─ agent_sidebar.py        # AI 抽屉侧栏封装
│  ├─ algebra_panel.py        # 左侧代数与图层控制面板
│  ├─ designer_window.py      # Designer UI 加载与界面绑定
│  ├─ lighting_dialog.py      # 光照参数对话框
│  ├─ main_window.py          # 主窗口逻辑
│  ├─ main_window.ui          # Qt Designer 布局文件
│  ├─ scene_settings.py       # 场景设置面板
│  ├─ two_d_tools.py          # 二维点线工具与网格吸附
│  └─ ...
├─ tests/                     # 单元测试
│  ├─ test_algebra_panel.py
│  ├─ test_cas_surface.py
│  ├─ test_intersections.py
│  ├─ test_layer_scene.py
│  ├─ test_lighting.py
│  ├─ test_lighting_dialog.py
│  ├─ test_main_window_layout.py
│  ├─ test_agent_panel.py
│  ├─ test_agent_provider.py
│  ├─ test_agent_settings.py
│  ├─ test_scene_commands.py
│  ├─ test_standard_surfaces.py
│  ├─ test_surface_layers.py
│  └─ ...
├─ .venv/                     # 本地 Python 虚拟环境，通常不提交到 Git
├─ .gitignore                 # Git 忽略规则
└─ .vscode/                   # 编辑器配置（如需要）
```

### 目录说明

- `MathInputWidget/`：可复用的 MathLive 公式输入组件，本地捆绑 MathLive 运行时与字体，无需联网。
- `widgets/`：自定义 Qt 控件（如灯光方位角圆环）。
- `geometry/`：数学表达式解析、曲线和曲面生成、常见几何体定义。
- `models/`：保存参数、图层状态和场景模式，是界面和渲染层之间的数据桥梁。
- `rendering/`：负责视觉渲染、辅助线、坐标轴、光照和图层绘制。
- `ui/`：包含 Qt 用户界面、菜单、面板和交互逻辑。
- `services/`：提供与 UI 解耦的 Agent provider、命令校验、事务执行和确定性教学宏。
- `tests/`：用于验证解析逻辑、渲染行为、交线计算和界面布局。

## 安装

推荐使用 `uv` 进行环境管理：

```bash
uv sync
```

如果尚未安装 `uv`，可以先执行：

```bash
pip install uv
```

## 运行

```bash
uv run python main.py
```

或者在已激活虚拟环境时：

```bash
python main.py
```

启动后点击视口右上角的 AI 图标即可展开常驻 Sidebar。默认本地 Provider 不需要 API key；在 Agent 设置中选择 OpenAI-compatible 或 DeepSeek，填写连接信息并启用远程模型即可切换。配置错误或网络失败时，聊天记录保留，可随时切换回本地演示模式而不丢失已填写的连接信息。MCP 工具层可通过 `python -m agent.mcp_server` 使用本地 stdio JSON-RPC，不连接外部工具。

## 测试

测试位于 `tests/`，基于标准库 `unittest`，覆盖表达式解析、几何对象、场景命令、光照与界面布局等模块：

```bash
uv run python -m unittest discover -s tests
```

也可以使用 pytest（兼容 `unittest` 用例）：

```bash
uv run pytest
```

## 使用方式

1. 启动程序后，可以在 2D 与 3D 场景模式之间切换。
2. 在左侧面板中输入或选择曲线/曲面表达式。
3. 调整参数、颜色、透明度和显示范围，以观察几何变化。
4. 使用交线功能、坐标轴和辅助线帮助分析几何特征。
5. 调整光照和材质设置，以提升教学演示效果。
6. 点击右上角 AI 图标，在 2D 场景中输入自然语言请求，检查命令计划后点击“执行计划”。

## 示例表达式

### 显式曲面

```text
z = x^2 - y^2
```

### 隐式曲面

```text
x^2 + y^2 + z^2 = 1
```

### 参数曲面

```text
(x(u,v), y(u,v), z(u,v)); u=[0,1], v=[-1,1]
```

### 2D 函数示例

```text
y = sin(x)
```

## 内置曲面与函数目录

程序内置了常见二次曲面与二维函数目录，无需手工输入即可直接插入并编辑。

### 3D 内置二次曲面

| 名称 | 表达式 | 类型 |
| --- | --- | --- |
| 平面 | `z = a*x + b*y + c` | 显式 |
| 球面 | `x^2 + y^2 + z^2 = r^2` | 隐式 |
| 椭球面 | `x^2/a^2 + y^2/b^2 + z^2/c^2 = 1` | 隐式 |
| 椭圆锥面 | `x^2/a^2 + y^2/b^2 = z^2/c^2` | 隐式 |
| 椭圆柱面 | `x^2/a^2 + y^2/b^2 = 1` | 隐式 |
| 双曲柱面 | `x^2/a^2 - y^2/b^2 = 1` | 隐式 |
| 抛物柱面 | `z = x^2/a` | 显式 |
| 椭圆抛物面 | `z = x^2/a^2 + y^2/b^2` | 显式 |
| 双曲抛物面（马鞍面） | `z = x^2/a^2 - y^2/b^2` | 显式 |
| 单叶双曲面 | `x^2/a^2 + y^2/b^2 - z^2/c^2 = 1` | 隐式 |
| 双叶双曲面 | `x^2/a^2 + y^2/b^2 - z^2/c^2 = -1` | 隐式 |

### 2D 函数目录

- **基本初等函数**：正弦、余弦、正切、指数、对数、平方根、绝对值
- **代数函数**：一次函数、二次函数、三次函数、反比例、反比例平方
- **圆锥曲线**：圆、椭圆、双曲线、抛物线

目录中的每个条目都附带默认参数、颜色与 LaTeX 显示，插入后作为独立图层继续编辑。

## 交互操作

### 3D 场景

| 操作 | 效果 |
| --- | --- |
| 左键拖动 | 绕坐标原点旋转视角 |
| 中键拖动 / Shift+左键拖动 | 平移 |
| 右键拖动 | 缩放（dolly） |
| Ctrl+左键拖动 | 自旋（spin） |
| Shift+右键拖动 | 环境光旋转 |

### 2D 场景

| 操作 | 效果 |
| --- | --- |
| 滚轮 | 以光标为中心缩放 |
| 左键 | 放置 / 选中几何对象 |
| 右键拖动 | 平移 |
| `Ctrl+Z` | 撤回 |
| `Ctrl+Shift+Z` | 重做 |
| `Delete` / `Backspace` | 删除选中对象 |
| `Esc` | 取消选择 / 退出当前工具 |

### 2D 几何工具

右侧工具栏提供：选择/移动、点、直线、线段、射线、向量，以及网格吸附、撤回与重做按钮。启用吸附后，落点接近网格线时自动对齐，避免“抢”走自由位置。

## 适用场景

该项目适合用于：

- 数学教学演示
- 平面与空间函数可视化
- 二次曲面研究
- 代数表达式与几何图形关联教学
- 交互式数学实验平台开发

## 贡献

欢迎提交问题、建议以及改进内容。

## 许可证

项目尚未声明正式许可证。如需公开发布，建议在仓库根目录添加 `LICENSE` 文件并在此处补充说明，例如 MIT License。

> 注意：`MathInputWidget` 捆绑的 MathLive 运行时按其自身许可证分发，详见 `MathInputWidget/README.md` 与上游项目。
