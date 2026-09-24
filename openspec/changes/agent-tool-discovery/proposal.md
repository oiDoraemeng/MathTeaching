## Why

当前 Agent 的 native tool loop 在每次请求中发送完整 capability catalog。工具数量从个位数增长到几十或上百后，会同时造成上下文浪费、工具选择歧义、schema 维护困难和安全边界变薄。仓库已经具备版本化 `CapabilitySpec`、受限分发、暂存场景和 `CommandPlan` 校验，但还缺少一个让模型先找到能力、再获得少量完整 schema 的发现协议。

## What Changes

- 为 `CapabilitySpec` 增加工具族、显示标题、标签、示例、曝光级别、生命周期状态和 schema 版本元数据。
- 增加固定的核心发现能力：`tool.search`、`tool.describe`、`scene.inspect`、`scene.find`。
- 为现有可发现能力建立确定性的本地检索索引；搜索即激活，按回合替换 bounded active set，不向模型发送全量 catalog。
- 修改 native provider loop：首轮只发送核心工具，搜索成功后下一轮发送核心工具加已激活工具；每次请求冻结 offered tool snapshot。
- 拒绝未激活、禁用、废弃、实验性未授权或场景不匹配的调用；保留现有 staged scene、`CommandPlan`、取消、限额和回滚语义。
- 为 discovery、activation、rejection 和动态工具调用补充有界生命周期事件与运行时指标。
- 保持非 native provider 的既有 JSON/fenced `CommandPlan` fallback，不伪造动态 search tool。

## Deferred Follow-ups

- 语义绘图 capability（`draw.2d.*`、`draw.3d.*`）属于 Stage 2，当前变更只验证现有 `scene.edit` 与 `math.derive` 的发现、激活和调用。
- 2D/3D 工具栏映射、`ToolIntent` 统一入口和 Skills explorer 属于 Stage 3；本变更不改变工具栏交互，也不要求 UI 手动激活工具。

## Capabilities

### New Capabilities

None. 发现协议扩展现有 `mathagent-capabilities` 和 `mathagent-runtime`，不建立第二套能力体系。

### Modified Capabilities

- `mathagent-capabilities`: 增加能力元数据、确定性搜索、`tool.search`/`tool.describe`、回合激活和未激活调用拒绝。
- `mathagent-runtime`: 增加核心目录到动态目录的 native tool loop、请求快照、发现事件、预算和兼容性规则。

## Impact

- Python Agent：`agent/capabilities/contracts.py`、`registry.py`、`orchestrator.py`、新增搜索索引/同义词模块和 `agent/runtime.py`。
- Provider 边界：native function-tools provider 每轮接收 bounded catalog；非 native 路径保持既有协议。
- Web bridge：复用现有 lifecycle event envelope，增加可选 discovery 字段；不发送完整 schema、内部路径或敏感参数。
- 测试：增加注册表检索、原子激活、动态 provider loop、错误与兼容性测试。
- 不新增网络 embedding、外部 MCP 或运行时依赖。
