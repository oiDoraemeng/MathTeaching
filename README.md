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

## 技术栈

- Python 3.11+
- PySide6
- PyVista
- PyVistaQt
- SymPy
- NumPy
- SciPy

## 项目结构

```text
Math3DTeaching/
├─ main.py                     # 程序入口，启动应用窗口
├─ pyproject.toml             # Python 项目配置与依赖声明
├─ requirements.txt           # 依赖列表
├─ README.md                  # 项目说明文档
├─ geometry/                  # 几何计算与数学表达式处理
│  ├─ __init__.py
│  ├─ cas_curve.py            # 曲线 CAS 解析
│  ├─ cas_surface.py          # 曲面 CAS 解析与网格构造
│  ├─ hyperboloid.py          # 双叶双曲面等主要几何体实现
│  ├─ standard_surfaces.py    # 内置标准二次曲面定义
│  └─ ...
├─ models/                    # 数据模型
│  ├─ __init__.py
│  ├─ curve_layer.py          # 曲线图层数据结构
│  ├─ function_catalog.py     # 函数目录与表达式列表
│  ├─ parameters.py           # 参数模型
│  ├─ scene_mode.py           # 2D/3D 场景模式定义
│  ├─ surface_layer.py        # 曲面图层数据结构
│  └─ ...
├─ rendering/                 # 视图渲染与场景构建
│  ├─ __init__.py
│  ├─ axis.py                 # 坐标轴绘制
│  ├─ curve_scene.py          # 曲线场景渲染器
│  ├─ helper.py               # 辅助线与参考线
│  ├─ lighting.py             # 光照参数定义
│  ├─ materials.py            # 材质和颜色配置
│  ├─ scene.py                # 三维场景构建与更新
│  ├─ ticks.py                # 坐标轴刻度与可见边界计算
│  ├─ two_d_scene.py          # 二维场景渲染
│  └─ layer_scene.py          # 图层式渲染控制器
├─ ui/                        # 用户界面及交互逻辑
│  ├─ __init__.py
│  ├─ algebra_panel.py        # 左侧代数与图层控制面板
│  ├─ designer_window.py      # Designer UI 加载与界面绑定
│  ├─ lighting_dialog.py       # 光照参数对话框
│  ├─ main_window.py          # 主窗口逻辑
│  ├─ main_window.ui          # Qt Designer 布局文件
│  ├─ scene_settings.py       # 场景设置面板
│  └─ ...
├─ tests/                     # 单元测试
│  ├─ test_algebra_panel.py
│  ├─ test_cas_surface.py
│  ├─ test_intersections.py
│  ├─ test_layer_scene.py
│  ├─ test_lighting.py
│  ├─ test_lighting_dialog.py
│  ├─ test_main_window_layout.py
│  ├─ test_standard_surfaces.py
│  ├─ test_surface_layers.py
│  └─ ...
├─ .venv/                     # 本地 Python 虚拟环境，通常不提交到 Git
├─ .gitignore                 # Git 忽略规则
└─ .vscode/                   # 编辑器配置（如需要）
```

### 目录说明

- `geometry/`：数学表达式解析、曲线和曲面生成、常见几何体定义。
- `models/`：保存参数、图层状态和场景模式，是界面和渲染层之间的数据桥梁。
- `rendering/`：负责视觉渲染、辅助线、坐标轴、光照和图层绘制。
- `ui/`：包含 Qt 用户界面、菜单、面板和交互逻辑。
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

## 使用方式

1. 启动程序后，可以在 2D 与 3D 场景模式之间切换。
2. 在左侧面板中输入或选择曲线/曲面表达式。
3. 调整参数、颜色、透明度和显示范围，以观察几何变化。
4. 使用交线功能、坐标轴和辅助线帮助分析几何特征。
5. 调整光照和材质设置，以提升教学演示效果。

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

如果需要公开发布到 GitHub，建议补充正式许可证说明，例如 MIT License。
