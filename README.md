# Math3D Teaching

Math3D Teaching 是一个基于 PySide6 和 PyVista 的交互式三维解析几何教学应用，主要用于展示双叶双曲面及其它代数曲面在三维空间中的几何关系。该项目面向数学教学与可视化演示，强调参数交互、空间感知和几何关系的直观理解。

## 亮点

- 实时交互式参数调节：可直接调整 a、b、c 参数
- 3D 场景浏览：支持旋转、缩放和平移
- 坐标轴与辅助线显示：便于理解空间结构
- 代数曲面输入：支持显式、隐式和参数式曲面
- 图层管理：可控制曲面的显示、颜色、透明度和采样范围
- 交线计算：支持自动交线和手动交线生成
- 光照与材质控制：适合教学演示和视觉效果调优

## 技术栈

- Python 3.11+
- PySide6
- PyVista
- PyVistaQt
- SymPy
- NumPy

## 项目结构

```text
Math3DTeaching/
├─ main.py                     # 应用入口，启动 PySide6 主窗口
├─ pyproject.toml             # Python 项目配置与依赖声明
├─ requirements.txt           # 依赖列表
├─ README.md                  # 项目说明文档
├─ geometry/                  # 几何计算与曲面生成模块
│  ├─ __init__.py
│  ├─ cas_surface.py          # CAS 表达式解析与曲面网格构造
│  ├─ hyperboloid.py          # 双叶双曲面等几何体实现
│  └─ standard_surfaces.py    # 内置标准二次曲面定义
├─ models/                    # 数据模型定义
│  ├─ __init__.py
│  ├─ parameters.py           # 双曲面参数模型
│  └─ surface_layer.py        # 可编辑曲面图层数据结构
├─ rendering/                 # 3D 渲染与场景构建
│  ├─ __init__.py
│  ├─ axis.py                 # 坐标轴绘制
│  ├─ helper.py               # 辅助线与投影辅助构造
│  ├─ lighting.py             # 光照设置
│  ├─ materials.py            # 材质与颜色配置
│  ├─ scene.py                # 基础场景构建和渲染状态更新
│  └─ layer_scene.py          # 图层式渲染控制器
├─ ui/                        # 用户界面相关代码
│  ├─ __init__.py
│  ├─ algebra_panel.py        # 左侧代数面板，输入与管理曲面
│  ├─ designer_window.py      # Designer UI 加载与事件绑定
│  ├─ lighting_dialog.py       # 光照参数对话框
│  ├─ main_window.py          # 传统主窗口逻辑
│  └─ main_window.ui          # Qt Designer 设计文件
├─ tests/                     # 自动化测试
│  ├─ test_algebra_panel.py
│  ├─ test_cas_surface.py
│  ├─ test_intersections.py
│  ├─ test_layer_scene.py
│  ├─ test_lighting.py
│  ├─ test_lighting_dialog.py
│  ├─ test_main_window_layout.py
│  ├─ test_standard_surfaces.py
│  └─ test_surface_layers.py
└─ .venv/                     # 本地虚拟环境（通常不提交到 Git）
```

### 结构说明

- `geometry/`：负责数学对象和曲面构造，包含公式解析、二次曲面生成和标准曲面定义。
- `models/`：保存参数和图层状态，作为 UI 和渲染之间的数据桥梁。
- `rendering/`：负责 3D 场景、光照、坐标轴、辅助线和材质的可视化输出。
- `ui/`：包含界面布局与交互逻辑，支持 Qt Designer 和程序内事件绑定。
- `tests/`：用于验证表达式解析、图层更新、交线计算和界面布局行为。

## 安装

推荐使用 uv 进行环境管理：

```bash
uv sync
```

如果没有安装 uv，可以先执行：

```bash
pip install uv
```

## 运行

```bash
uv run python main.py
```

也可以在已激活虚拟环境的情况下：

```bash
python main.py
```

## 使用说明

1. 启动程序后，左侧面板可以实时调整双叶双曲面的参数。
2. 右侧 3D 视口支持旋转、缩放和平移操作。
3. 在代数面板中可以输入：
   - 显式曲面方程
   - 隐式曲面方程
   - 参数曲面表达式
4. 可分别修改曲面的颜色、透明度、范围和可见性。
5. 打开辅助线、坐标轴和交线功能，有助于教学演示和几何理解。

## 典型示例

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

## 适用场景

该项目特别适合：

- 解析几何教学
- 三维曲面可视化
- 空间几何演示
- 数学软件原型开发
- 可视化交互式课堂辅助工具

## 贡献

欢迎提交问题、反馈和改进建议。

## 许可证

如需公开发布到 GitHub，建议补充实际的许可证说明，例如 MIT License。
