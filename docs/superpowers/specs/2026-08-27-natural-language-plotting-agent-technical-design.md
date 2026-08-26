# 自然语言绘图 Agent 深度技术设计

## 目标

将数学 Agent 的能力做成可发现、可校验、可审计的本地工具目录。模型负责选择工具和组织解释，工具只产生 JSON 数据或受限 `CommandPlan`；任何 Qt、PyVista 和文件系统写入仍由既有场景命令边界处理。

## 现状结论

- `agent/tool_registry.py` 目前是平铺的六个工具，Schema 只作为描述，调用前没有统一严格校验。
- `services/agent_provider.py` 能解析流式 `tool_calls`，但 `MathTeacherAgent` 没有把工具目录传给 Provider，也没有把工具结果带回模型进行下一轮调用。
- `AgentRuntime`、`SceneCommandService` 和场景宿主已经具备验证、事务、审批、撤销和跨线程 GUI 代理基础，必须复用。
- `SceneSnapshot` 比 `SceneContext` 完整；当前 `SceneContext` 缺相机、图层、标注、选中状态和稳定场景版本，不能独立支撑安全的读写编排。
- 当前 2D/3D `CommandPlan` 只有一个 `scene` 字段，不能在一次原子计划中混合修改两种场景。

## 文件边界

```text
agent/
  capabilities/
    contracts.py       # Catalog、ToolCall、CapabilityResult、CapabilityError
    registry.py        # Schema 验证、别名解析、分发
    scene_index.py     # Snapshot -> 可变但无渲染器的暂存索引
    scene_tools.py     # scene.*、view.control、result.export
    math_tools.py      # math.*、teaching.explain
    orchestrator.py    # Provider 工具循环、配额、计划合并、事件
  tool_registry.py     # 向后兼容门面
  runtime.py           # 运行时装配、模式和审批

services/
  agent_provider.py    # Chat Completions / Responses 的工具协议转换
  scene_commands.py    # 最终命令验证、唯一模式切换、场景指纹守卫

ui/
  designer_window.py   # 初始 snapshot、GUI 线程指纹比对、导出根目录
  agent_web/src/       # catalog 状态、工具事件卡、Skills 分组
```

新增模块均不能 import `PySide6` 或 `pyvista`。`designer_window.py` 是唯一可以把当前 GUI 场景转换为快照、执行已验证计划、或解析导出目标的层。

## 数据契约

```python
@dataclass(frozen=True)
class CapabilitySpec:
    catalog_version: int
    name: str
    category: Literal[
        "scene_read", "scene_edit", "math_analysis",
        "view_control", "result_export", "teaching_explain",
    ]
    description: str
    input_schema: dict[str, object]
    result_kind: Literal["data", "plan", "explanation"]
    scene_scope: Literal["2d", "3d", "both"]
    mutating: bool
    aliases: tuple[str, ...] = ()

@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, object]

@dataclass(frozen=True)
class CapabilityResult:
    call_id: str
    name: str
    status: Literal["ok", "no_op", "error"]
    data: dict[str, object] | None = None
    plan: CommandPlan | None = None
    explanation: str | None = None
    error: CapabilityError | None = None
```

`status="ok"` 时 `data`、`plan`、`explanation` 恰有一个；`no_op` 没有计划；`error` 只带稳定 `code`、用户可读 `message` 和可选 `field`。目录版本为 1，模型可调用的名称固定为：

```text
scene.inspect  scene.find  scene.edit  scene.clear
math.calculate math.derive
view.control   result.export  teaching.explain
```

旧名称只在本地兼容层解析，例如 `create_curve -> scene.edit`、`create_tangent -> math.derive`。目录 API 不展示旧名称，避免新模型继续依赖旧协议。

## 输入校验和安全数学

每个 Capability 先经过 Draft 2020-12 JSON Schema 校验，再进入领域校验。所有对象 Schema 均拒绝额外字段；别名是 ASCII 机器 ID，中文名称放入 `label`；字符串、数组、调用参数和结果都有硬上限。

`math.calculate` 不再使用当前工具注册表中对任意文本的 `sympy.sympify`。实现抽出或复用曲线/曲面已有的字符、函数、常量白名单解析逻辑，并要求计算表达式不存在自由变量。导数、切线和曲面公式在生成计划前分别用 `parse_curve_expression` 和 `parse_surface_expression` 作语义检查。

`result.export` 的 `filename` 是展示名，不是路径。GUI 在执行阶段把合法的 `.png` basename 解析到 `.math/exports/` 下并拒绝绝对路径、`..`、分隔符、保留设备名和其他扩展名。Agent 不具备保存 JSON 场景、读取任意文件、恢复历史场景或执行 shell/Python 的能力。

## 暂存场景和一致性

调用开始时，主线程创建 `SceneSnapshot` 并计算：

```python
scene_fingerprint = sha256(snapshot.to_json().encode("utf-8")).hexdigest()
```

工具只读取该快照。`SceneIndex` 将其转换为 `alias -> {type, summary, staged}` 的有序映射。每个变更工具产生 `CommandPlan` 后先经 `SceneCommandService.preview()`，然后把 `expanded_operations` 应用于 `SceneIndex`。这使后续 `scene.find` 能看见“尚未执行”的 `f` 或 `P`，并在同一回合提前发现别名冲突。

计划合并遵守以下规则：

1. 工具调用按照 Provider 返回顺序串行处理。
2. 仅把成功的 mutating result 加入候选计划，no-op 和失败不加入。
3. 所有候选计划必须同为 2D 或同为 3D；混合即 `scene_conflict`。
4. 原始操作最多 32 个，宏展开操作最多 128 个。
5. 合成结果只保留一个场景模式；命令服务在首操作缺失时补充唯一的 `scene.set_mode`，2D/3D 一致。

自动执行与批准执行都使用初始 fingerprint。宿主在开始事务前于 GUI 线程重新快照并对比；不相等时抛出 `scene_changed_since_plan`，不执行任何 operation，并使审批票据失效。指纹存在 turn 的 validation JSON，而不是模型可控的 `CommandPlan` 本体。

## 工具调用循环

```text
capture snapshot
  -> provider request(catalog, parallel_tool_calls=false)
  -> tool calls?
       no  -> compose + validate -> mode decision
       yes -> validate call -> emit tool_started
              -> dispatch against SceneIndex -> emit tool_finished
              -> append structured output -> provider continuation
```

上限：每回合最多 8 次调用、其中最多 4 次修改调用、单调用参数 16 KiB、单结果 32 KiB；`scene.inspect` 返回最多 50 项，`scene.find` 返回最多 20 项。规范化参数完全相同的第三次调用报 `tool_loop_detected`。取消在每个网络事件、每次分发、合并和执行前检查；取消后抵达的模型内容只能被丢弃，不能造成工具调用或场景变更。

Provider 使用两种序列化：Chat Completions 的 `tool_calls`/`tool` 消息，Responses 的 `function_call`/`function_call_output` 项，并用匹配的 call ID 关联结果。若自定义兼容服务拒绝工具，原 Provider 仅重试一次结构化 `CommandPlan` 回退，不换模型，并向 UI 发出 fallback 事件。回退路径不承诺“读工具后继续调用”的多轮能力。

## Agent/Ask/Plan 语义

只读工具在三种模式下自动执行。没有修改工具结果时，回合状态为 `answered`，不显示计划确认。存在合成计划时：

- Agent：校验并使用指纹守卫执行。
- Ask：显示一个完整计划，保存一张审批票据。
- Plan：显示一个完整计划与预览，等待同一张审批票据。

重复批准、停止、验证失败、场景冲突和执行完成都会使该票据无效。执行错误依靠既有场景事务回滚，并保留执行前快照。

## 事件与 Web UI

新增 `tool_started`、`tool_finished`、`plan_composed`、`capability_fallback`、`scene_conflict` 事件。每项都带 session/turn、调用 ID、canonical 名称、分类、只读/修改标记和有限摘要；不携带原始附件、完整提示词、密钥、异常堆栈或隐藏推理。

`build_session_snapshot()` 增加 `capability_catalog`。Skills 弹层直接按六个分类显示能力说明，不能从弹层手动启动工具。时间线新增工具结果和 fallback 卡片，原有 `PlanCard` 继续展示最终唯一的 `CommandPlan`。前端 reducer 延续现有 sequence 去重和断档检测，catalog 更新不能重置已打开会话或事件。

## 验收测试矩阵

| 场景 | 证明点 |
|---|---|
| 目录序列化 | 9 个 canonical 工具、6 个分类、版本和 schema 都稳定；alias 不出现 |
| 严格分发 | 未知字段、NaN、超限、未知工具在 handler 前失败 |
| 安全表达式 | 非法函数、导入文本、自由变量计算、错误曲面不会进入 renderer |
| 暂存读取 | 创建 `f` 后查找能标为 staged，真实场景仍未变化 |
| 合成与维度 | 多个 2D 操作一个计划；2D+3D 产生 `scene_conflict` |
| 模式与并发 | Ask/Plan 无执行；重复批准和场景指纹变化不启动事务 |
| 停止 | Provider 结果晚到后不再调工具和执行 |
| 导出 | 合法 `plot.png` 进入受管目录；路径遍历完全拒绝 |
| Provider 回退 | native 工具不支持时仅同 Provider 回退一次，事件可见 |
| UI | 弹层分组、工具事件卡、序列去重、离线 Vite 构建都通过 |
