## Context

现有系统已经把 Agent 调用约束在 `CapabilityRegistry -> CapabilitySession -> CommandPlan -> SceneCommandService` 边界内，但 `AgentRuntime._native_turn` 每次向 provider 发送完整 catalog。设计目标是让 registry 可以扩展到数百个能力，同时保证模型看到的 schema 少而稳定、执行仍然可审计。

本变更只实现 Stage 1：发现基础设施和现有能力的动态注入。Stage 2 的语义绘图能力和 Stage 3 的工具栏/Skills 统一入口单独立项。

## Goals / Non-Goals

**Goals:**

- 首轮和续轮的 provider tool payload 与 registry 总量解耦。
- 搜索、激活、描述和调用具有确定、可测试、可审计的状态转换。
- 不暴露低层 renderer operation；继续由 `SceneCommandService` 作为唯一 mutation boundary。
- native provider 使用动态 tool loop；非 native provider 不伪造搜索协议。
- 保留现有 snapshot、staged reads、计划合成、审批/执行、取消、回滚、旧别名和事件兼容。

**Non-Goals:**

- 本变更不增加 `draw.2d.*` 或 `draw.3d.*` 语义绘图工具。
- 本变更不修改 2D/3D 工具栏，不实现 `ToolIntent`，不实现 Skills explorer。
- 不实现远程向量库、embedding 服务、自动 Python/Qt/PyVista 执行或通用 `tool.invoke`。
- 不让模型调用低层命令、文件系统、鼠标拖动、吸附或自由相机手势。

## Decisions

### 1. Core, discoverable and internal exposure

`CapabilitySpec` 新增以下字段：`family`、`title`、`tags`、`examples`、`exposure`、`status`、`schema_version`。合法值分别为稳定的本地枚举：

- `exposure`: `core | discoverable | internal`
- `status`: `stable | experimental | deprecated | disabled`
- `family`: `scene | math | view | export | teaching | general`

旧能力默认 `family=general`、`exposure=discoverable`、`status=stable`、`schema_version=1`。catalog version 仍为 1，不增加第二个 metadata version。`tool.search`、`tool.describe`、`scene.inspect`、`scene.find` 是唯一 core 工具。`scene.edit`、`scene.clear`、`math.calculate`、`math.derive`、`view.control`、`result.export`、`teaching.explain` 保持 discoverable。internal 能力永远不进入模型 catalog。

Provider 定义继续只使用现有 `name`、`description`、`input_schema`；元数据用于本地检索、事件和 UI 投影，不塞进工具参数。

### 2. Deterministic local search

注册表建立惰性、不可变快照式索引，register 时标记 dirty；500 个工具以内使用 O(N) 候选扫描即可，避免新增运行时依赖。索引字段包括 name、title、aliases、family、tags、description、examples、scene scope 和 status。

中文同义词放在独立的 `agent/capabilities/search_terms.py`，覆盖函数/曲线、切线/导数、投影、曲面/交线、拟合/视图、导出、讲解等词族。排序必须稳定：canonical name +100、alias +80、tag/synonym +60、title +40、description +20、example +10、scene exact +15、scene both +5；同分按 canonical name 排序，score 只在当前结果集内归一化。

`tool.search` 输入：`query`（必填，1-512）、可选 `scene`（`2d|3d`）、`family`（最多 32）、`tags`（最多 8 个，每个最多 32）、`limit`（默认 6，硬上限 8）、`include_experimental`（默认 false）。输出只包含 `name/title/score/reasons/scene_scope/status`，`near_misses` 最多 3 个，不包含完整 schema。无匹配返回 `matches=[]`、`near_misses`、`limitation` 和 `status=no_match`；错误使用稳定 CapabilityResult error code。

核心搜索错误码：`invalid_search_query`、`no_capability_match`、`scene_scope_mismatch`、`experimental_capability_unavailable`、`search_limit_exceeded`。搜索次数最多 3 次/回合；激活集合最多 8 个。

### 3. Search is activation

`tool.search` 成功后由 session 原子替换 active set，最新搜索替换旧集合，不累加。有效无匹配会清空旧集合；参数错误、索引异常或候选校验失败保留旧集合。search handler 本身纯函数，不直接修改 session。

`tool.describe` 只接受当前 active set 中的名称，返回 name/title/description/family/scene_scope/status/schema_version/input_schema/examples；不返回 handler 路径、依赖、原子操作或内部异常。模型如果需要旧工具必须再次搜索，不能通过 describe 绕过激活。

当前场景未显式传入时，搜索使用 session 的 scene scope；显式 scene 不匹配返回 `scene_scope_mismatch`。切换场景需要已激活的 `view.control`，切换后必须重新搜索。

### 4. Session snapshot and atomic activation

`CapabilitySession` 增加 `active_names: tuple[str, ...]`、`search_revision`、`search_count`、回合 registry snapshot 和本次请求的 `offered_names`。每个 provider request 前冻结 `offered_names = core + active`；同一响应中搜索后立即调用、但本轮未提供 schema 的能力返回 `tool_not_activated`，搜索结果只影响下一 request。

回合开始冻结 capability metadata/schema registry revision，保证描述和 provider schema 一致。registry 的新增、删除或 schema 变化下一回合生效；执行前仍检查紧急 disabled、scope、mode 和 cancellation。active set 不持久化到下一回合。

### 5. Native runtime loop and provider compatibility

native provider 路径采用显式发现：

```text
core catalog -> provider request
  -> tool.search -> atomically replace active set
  -> next request: core + active schemas
  -> invoke existing capability -> continue
  -> compose one plan or answer
```

每次请求最多 4 个 core + 8 个 active schema。每回合最多 8 次 capability calls（包含 search、describe 和普通调用），其中 search 子上限为 3，mutation 子上限为 4；provider request 最多 9 轮。继续应用 result/raw/expanded operation、duplicate call、cancel 和 scene conflict 限制。移除 system prompt 中列举的低层 renderer operation，只说明模型只能调用当前提供的工具。

只对支持 native function-tools 的 provider 启用动态目录。JSON/fenced `CommandPlan` fallback 保持旧路径，不注入 `tool.search`，不声称支持多轮发现；如果 native transport 被服务拒绝，按现有 fallback 事件处理。

### 6. Failure, cancellation and safety

未激活调用返回 `tool_not_activated`；未知、disabled、deprecated、experimental 未授权、scope mismatch、invalid args 和 handler rejection 使用稳定错误码。可恢复错误作为 tool result 回传，终端错误（超限、取消、超时、跨场景、协议错误）结束回合。

工具计划必须先 `SceneCommandService.preview`，失败时整次调用不进入 staged scene。取消、超时或终端错误丢弃 staged operations，不调用 `finish()`。只有所有调用成功、计划通过校验且会话正常结束才提交唯一 `CommandPlan`。

搜索 query 512 字符、结果 6/8、near miss 3、reason 3 条且每条 64 字符；事件不携带完整 schema、内部异常、路径、凭证、renderer 对象或未经清洗的长参数。

### 7. Events and projection

继续使用 `tool_started` / `tool_finished` / `plan_composed` envelope。新增可选 `phase=discover|describe|invoke`、`search_revision`、`activated_names`；`result_kind` 可为 `search` 或 `description`。事件只记录 bounded query/argument summary、canonical name、status、error code 和 offered count，保证旧 validator 仍能处理未带新增字段的事件。

`build_session_snapshot()` 可投影完整本地 catalog 给后续 UI，但 runtime provider catalog 必须按 exposure/active 过滤。当前变更不实现 Skills explorer；后续 UI 变更可复用该 projection。

## Rejected Alternatives

- Python 侧先检索、再把单个工具预填给模型：会把“用户意图判断”从模型移到不可解释的隐式启发式，且无法支持模型在回合中修正搜索。
- 通用 `tool.invoke(name, args)`：省 token 但失去每个工具的 schema 约束和 provider 原生安全边界。
- 每轮发送全目录：随着工具数量增长不可控。
- 发送分页 catalog：模型需要维护页状态，且容易选择目录页而不是能力。
- 首阶段直接新增大量语义 `draw.*`：会把检索、绘图 handler、toolbar 和 UI 同时耦合，难以隔离回归。

## Verification Strategy

- 检索单测：名称、别名、中文同义词、scene/family/tag、稳定排序、near miss、实验过滤和边界长度。
- 协议单测：search/describe schema、revision、替换/清空/保留状态、未激活拒绝和 describe 权限。
- runtime 集成：fake native provider 验证首轮仅 4 个 core、后续为 core+active、同批次 stale call 拒绝、3/8/4/9 限额。
- 安全回归：preview 原子性、scope/lifecycle、取消/超时丢弃 staged operations、事件清洗。
- 兼容性：非 native provider 仍走既有 JSON/fenced path；既有 `scene.edit`、`math.derive`、2D/3D 和 bridge tests 保持通过。
- 验收样例：`求导并标出切线` 可搜索并激活现有能力；`画一个 3D 曲面` 在 Stage 1 返回未提供语义绘图能力的明确限制，不猜测低层操作。
