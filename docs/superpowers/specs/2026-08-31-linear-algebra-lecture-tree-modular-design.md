# 线性代数讲义绘图目录模块化技术设计

## 1. 目标与边界

本变更把《线性代数讲义》前三章中需要几何表达的内容实现为可搜索、可展开的课程树。课程树只收录已从原文确认的绘图主题，不收录自测题、练习题、挑战题和纯符号推导。

本设计明确放弃现有 `models/linear_algebra_cases.py` 的案例模型、旧案例 ID 和兼容适配器。新课程目录、数学解释和绘图配方从零建立，旧案例测试改写或删除，不作为新实现的行为约束。

前三章的绘图目录固定为 54 个叶子主题：第一章 24 个、第二章 15 个、第三章 15 个。章和节节点只用于导航，只有叶子节点可以加载场景和数学解释。

## 2. 设计原则

1. 讲义目录是内容来源，代码中的 manifest 是运行时快照。
2. 目录、数学解释、绘图配方和底层绘图能力分层维护。
3. 内容模块不得导入 PySide6、PyVista 或主窗口对象。
4. 绘图配方只生成经校验的 `CommandPlan`，不直接修改场景。
5. 新增一个绘图主题时可以只新增或修改绘图模块，不需要修改数学解释实现。
6. 缺失绘图能力必须在开发校验阶段显式失败，不得静默隐藏目录项。
7. 所有章节和主题使用稳定的新 ID；不迁移旧案例 ID。

## 3. 模块布局

```text
linear_algebra/
├─ __init__.py
├─ catalog/
│  ├─ __init__.py
│  ├─ model.py              # LessonNode、LessonEntry、SourceAnchor
│  ├─ chapter_01.py         # 第一章叶子清单
│  ├─ chapter_02.py         # 第二章叶子清单
│  ├─ chapter_03.py         # 第三章叶子清单
│  └─ manifest.py           # 汇总章节，构建父节点和稳定顺序
├─ explanations/
│  ├─ __init__.py
│  ├─ chapter_01.py         # 第一章 ExplanationContent
│  ├─ chapter_02.py
│  └─ chapter_03.py
├─ visualizations/
│  ├─ __init__.py
│  ├─ chapter_01.py         # 第一章 VisualizationRecipe
│  ├─ chapter_02.py
│  └─ chapter_03.py
├─ registry.py              # 显式注册并校验三类内容
└─ validation.py            # 讲义标题、引用和能力覆盖率校验
```

UI 只依赖课程服务，不依赖上述章节文件：

```text
ui/
├─ linear_algebra_dialog.py       # 弹窗、搜索和按钮
├─ linear_algebra_tree_model.py   # 树节点、过滤和展开状态
└─ linear_algebra_content_view.py # 解释内容和加载状态
```

现有 `ui/algebra_panel.py` 只保留入口按钮和服务装配；旧的扁平案例弹窗实现移除。

## 4. 核心数据模型

### 4.1 目录节点

```python
@dataclass(frozen=True)
class LessonNode:
    id: str
    kind: Literal["chapter", "section", "topic"]
    title: str
    order: tuple[int, ...]
    parent_id: str | None
    children: tuple[str, ...]
    source_path: tuple[str, ...]
    explanation_id: str | None
    visualization_id: str | None
    required_capabilities: tuple[str, ...]
```

章和节节点的 `explanation_id`、`visualization_id` 为 `None`。主题节点必须同时引用一个解释和一个绘图配方。

`source_path` 保存从章到原文标题的完整路径。对于讲义中标题重复的情况，`SourceAnchor` 额外记录标题层级和出现序号，校验时按路径和序号匹配，避免仅按标题文本误匹配。

### 4.2 数学解释

```python
@dataclass(frozen=True)
class ExplanationContent:
    id: str
    title: str
    summary: str
    formula: str
    steps: tuple[str, ...]
    geometric_meaning: str
    conclusion: str
    searchable_text: tuple[str, ...]
```

解释内容使用纯字符串和 LaTeX，不包含 QWidget、场景对象或绘图回调。`searchable_text` 可包含关键词、别名和公式文本，供目录搜索使用。

### 4.3 绘图配方

```python
@dataclass(frozen=True)
class VisualizationRecipe:
    id: str
    scene: Literal["2d", "3d"]
    required_capabilities: tuple[str, ...]
    builder: Callable[[RenderContext], CommandPlan]
```

`builder` 必须是确定性函数。`RenderContext` 只提供主题、视图和示例参数等序列化数据，不提供 Qt 或 PyVista 引用。配方返回的计划必须通过 `SceneCommandService.validate()`。

## 5. 注册和引用关系

`registry.py` 使用显式映射，不采用运行时扫描任意 Python 文件：

```python
CATALOG = (...)
EXPLANATIONS = {...}
RECIPES = {...}
CAPABILITIES = {...}
```

注册校验按以下顺序执行：

1. 所有 ID 唯一，节点顺序连续且父子关系完整；
2. 每个主题节点的解释和配方引用都存在；
3. 节点声明的能力和配方声明的能力都已注册；
4. 每个配方在默认 `RenderContext` 下生成合法 `CommandPlan`；
5. 计划中的操作通过场景命令白名单和参数校验。

注册失败使用包含节点 ID、模块名和缺失能力的错误信息，阻止应用进入不完整的课程目录状态。

## 6. 讲义来源校验

开发测试阶段读取：

```text
D:\github\Math3DTeaching\.agents\线性代数讲义.md
```

校验器只提取前三章的 Markdown 标题层级，生成标题路径索引，然后检查 manifest：

- 每个 `SourceAnchor` 在原文中存在且只匹配一次；
- manifest 顺序与原文顺序一致；
- 叶子数量为 24、15、15；
- 排除标题不会出现在 manifest 中，包括自测、练习、挑战和纯符号计算条目；
- manifest 中没有孤立的解释或绘图配方。

应用运行时使用已注册的 manifest，不依赖 `.agents` 文件存在。这样发布包只携带课程内容模块，源码仓库仍能通过校验发现讲义变更造成的漂移。

## 7. 绘图能力分层

绘图配方通过现有 `CommandPlan -> SceneCommandService -> renderer` 链路执行。第一阶段补充以下通用能力：

```text
geometry.vector_3d
geometry.segment_3d
geometry.plane
geometry.polygon
geometry.parallelogram_3d
geometry.parallelepiped
geometry.projection
geometry.angle_arc
geometry.right_angle_marker
geometry.transformed_grid
geometry.subspace_region
geometry.oriented_area
geometry.oriented_volume
geometry.staged_transform
annotation.formula
annotation.vector_label
```

二维能力覆盖向量、投影、有向面积、角度、变换网格和子空间阴影；三维能力覆盖向量、平面、平行六面体、法向方向和有向体积。高维内容通过二维或三维类比图表示，并在解释中明确“类比”而不是伪造高维画布。

通用能力放在场景命令与渲染层，章节配方只组合它们。这样同一投影、角弧或变换网格能力可以被多个章节复用。

## 8. UI 数据流和交互

```text
点击“线性代数”
  -> LinearAlgebraDialog 打开
  -> CatalogService 返回 manifest 树
  -> TreeModel 构建章/节/主题节点
  -> 默认展开章节点，节和主题折叠

点击主题叶子
  -> Registry 获取 ExplanationContent 和 VisualizationRecipe
  -> recipe.builder(RenderContext) 生成 CommandPlan
  -> 主窗口以 scene.clear + plan 的单事务加载
  -> ContentView 显示公式、几何解释和结论
```

树节点点击分为两类：

- 章、节节点只切换展开状态，不发出加载信号；
- 主题叶子发出稳定主题 ID，加载对应解释和绘图。

搜索匹配主题标题、完整讲义路径、解释摘要、公式和 `searchable_text`。匹配时保留主题的所有祖先并自动展开路径；清空搜索后恢复默认展开状态。

“展开全部”展开所有可见节点；“折叠”折叠所有节点，仅保留三个章节点可见。搜索、展开和折叠逻辑由 `linear_algebra_tree_model.py` 维护，弹窗不复制目录数据。

## 9. 加载和错误处理

主题加载必须先构建并校验完整计划，再执行清场和应用。计划构建或校验失败时：

- 不清空当前场景；
- 在解释区域显示可读错误；
- 记录主题 ID、配方 ID 和校验消息；
- 不发送成功的 `math_case` 事件。

执行失败由现有事务回滚机制处理，保持当前场景不变。缺失能力属于开发期注册错误，测试必须在启动 UI 之前捕获。

## 10. 测试矩阵

### 内容和来源

- 章节叶子数量为 24、15、15，总数 54；
- 所有节点、解释和配方 ID 唯一；
- 每个 source anchor 存在且顺序正确；
- 自测、练习、挑战和纯符号条目不存在；
- 每个主题拥有非空公式、步骤、几何含义和结论。

### 绘图能力

- 每个配方在默认上下文下生成有效 `CommandPlan`；
- 所有操作使用已注册能力；
- 二维和三维命令参数经过有限值、维度和对象引用校验；
- 关键几何能力分别测试退化、方向和边界情况。

### UI

- 初始状态有三个章节点且章展开、节折叠；
- 分支点击不触发加载，主题叶子触发一次主题 ID；
- 展开全部和折叠按钮达到确定深度；
- 搜索保留祖先上下文、自动展开匹配路径、空结果不加载场景；
- 清空搜索恢复默认展开状态。

### 集成

- 54 个主题均可从树选择并生成解释和绘图；
- 加载事务的第一步是全场景清空，失败时原场景保留；
- 解释区域和画布主题 ID 一致；
- 运行 Python 全量测试、前端测试和 OpenSpec 严格校验。

## 11. 实施顺序

1. 删除旧案例模型和旧案例测试约束，建立新的课程包与数据模型。
2. 按章实现 54 个目录节点、解释和绘图配方，并补齐注册校验。
3. 先实现通用二维能力，再实现三维向量、平面、体积和变换网格能力。
4. 替换线性代数弹窗为独立树模型和内容视图。
5. 接入现有事务加载链路，补充来源、能力、UI 和集成测试。
6. 更新 OpenSpec 需求和任务清单，完成全量验证。

