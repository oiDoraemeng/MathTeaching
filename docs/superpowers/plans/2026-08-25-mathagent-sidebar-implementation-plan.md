# MathAgent Sidebar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Math3D Teaching 的右侧 AI 区域升级为默认隐藏、支持多会话标签、逐轮场景恢复/撤销/分支、Agent/Ask/Plan 模式和确认/连续执行的 MathAgent 工作区。

**Architecture:** 保留 PySide6、PyVista、SymPy、`CommandPlan` 和 `SceneCommandService`。新增 SQLite 会话存储、JSON 场景快照、事件驱动的 Agent Runtime 和受控数学工具；聊天时间线使用本地 `QWebEngineView` 渲染，WebView 只能通过消息桥发送 UI 意图。

**Tech Stack:** Python 3.11、PySide6/QWebEngineView、SQLite WAL、OpenAI Python SDK 的 OpenAI-compatible Chat Completions/SSE、Pydantic JSON Schema、pypdf、现有 SymPy/PyVista 场景宿主、KaTeX、Markdown-it。

---

## Scope Decomposition

本计划拆成三个可独立验证的子系统，按顺序实施：

1. **数据基础**：会话、逐轮记录、场景快照、恢复/撤销/分支、启动恢复。
2. **上下文与 Agent Runtime**：Context Broker、附件、DeepSeek 流式响应、工具调用、Agent/Ask/Plan、确认/连续执行。
3. **右侧工作区**：隐藏/打开、标题栏、会话标签、空状态、历史视图、WebView 时间线、输入区和悬浮操作。

每个子系统完成后都要有单元测试或协议测试，再连接到下一个子系统。

## File Map

### New files

- `agent/scene_snapshot.py`：纯 JSON 场景快照类型和版本化序列化。
- `agent/session_store.py`：`.math/mathagent.db` 的 SQLite schema、迁移、会话/轮次/事件/附件 CRUD。
- `agent/conversation.py`：会话、轮次、分支和当前指针的领域模型。
- `agent/events.py`：Runtime/UI 之间的可序列化事件类型。
- `agent/context_broker.py`：场景摘要、历史压缩、附件上下文和 token 用量估算。
- `agent/tool_registry.py`：数学工具定义、JSON Schema 和调用分派。
- `ui/agent_history.py`：历史记录窗口和恢复入口。
- `ui/agent_web/index.html`：聊天时间线和输入区 HTML。
- `ui/agent_web/app.js`：WebView 状态、事件渲染、按钮消息桥。
- `ui/agent_web/style.css`：MathAgent 工作区视觉样式。
- `tests/test_scene_snapshot.py`：场景快照协议测试。
- `tests/test_session_store.py`：SQLite 存储测试。
- `tests/test_conversation.py`：分支与当前轮测试。
- `tests/test_agent_events.py`：事件 schema 测试。
- `tests/test_context_broker.py`：上下文包、附件限制和用量指示器测试。
- `tests/test_agent_tools.py`：工具参数和 CommandPlan 测试。
- `tests/test_agent_runtime_loop.py`：双模式 Runtime 测试。
- `tests/test_agent_web_protocol.py`：WebView 消息协议测试。

### Modify files

- `pyproject.toml`、`requirements.txt`：加入 OpenAI SDK、Pydantic、pypdf；确认 PySide6 包含 `QtWebEngineWidgets`。
- `services/agent_provider.py`：从一次性读取响应扩展为流式响应和 tool call 结果协议；保留旧 `create_plan()` 兼容入口。
- `agent/providers/deepseek_provider.py`：DeepSeek base URL、model、thinking/tool-call 参数适配。
- `agent/runtime.py`：改为可取消的事件驱动状态机，保留 `validate()`/`execute()` 兼容方法；接入 Context Broker 和每会话模式/模型。
- `services/agent_worker.py`：改为转发 Runtime 事件，支持停止和排队消息。
- `services/scene_commands.py`：补充快照恢复所需的宿主协议或保持命令服务作为唯一执行入口，不允许新增绕过入口。
- `ui/designer_window.py`：提供纯数据场景捕获/恢复适配器，接入 SessionStore、Runtime 和面板打开/关闭。
- `ui/agent_sidebar.py`：移除 40px 折叠态，改成默认隐藏、打开后固定右侧宽度的容器。
- `ui/agent_panel.py`：改为 QWebEngineView 宿主和 Qt 消息桥，不再把 JSON 文本作为主计划视图；加入上下文环形用量指示器。
- `ui/main_window.ui`：保留主视口右上角 Agent 图标按钮的挂载位置。
- `tests/test_agent_panel.py`、`tests/test_sidebar.py`、`tests/test_main_window_layout.py`：更新面板可见性、标签和按钮行为测试。

## Task 1: Add Versioned Scene Snapshots

**Files:**
- Create: `agent/scene_snapshot.py`
- Modify: `ui/designer_window.py`
- Test: `tests/test_scene_snapshot.py`

- [ ] **Step 1: Write failing snapshot tests**

```python
def test_snapshot_round_trip_preserves_scene_state():
    snapshot = SceneSnapshot(
        version=1,
        scene_mode="2d",
        curves=({"alias": "f", "expression": "y=x^2"},),
        geometry=({"alias": "P", "coordinates": [1, 2]},),
        layers=(),
        camera={"parallel_scale": 10.0},
    )
    assert SceneSnapshot.from_json(snapshot.to_json()) == snapshot

def test_snapshot_rejects_unknown_version():
    with pytest.raises(ValueError, match="version"):
        SceneSnapshot.from_dict({"version": 99})
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `uv run pytest tests/test_scene_snapshot.py -q`

Expected: FAIL because `SceneSnapshot` is not defined.

- [ ] **Step 3: Implement the pure snapshot type**

Implement a frozen dataclass with `version`, `scene_mode`, `curves`, `geometry`, `layers`, and `camera`. `to_dict()` must emit only JSON-compatible primitives; `from_dict()` must validate the version and normalize tuples/lists. Do not import PySide6, PyVista, or SymPy.

- [ ] **Step 4: Expose a host adapter in `DesignerWindow`**

Add `capture_scene_snapshot() -> SceneSnapshot` and `restore_scene_snapshot(snapshot: SceneSnapshot) -> None`. Capture existing model-layer state and scene mode; restore through existing model synchronization and render methods. Do not instantiate or serialize PyVista objects.

- [ ] **Step 5: Run the focused test and the existing scene tests**

Run: `uv run pytest tests/test_scene_snapshot.py tests/test_scene_commands.py tests/test_layer_scene.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/scene_snapshot.py ui/designer_window.py tests/test_scene_snapshot.py
git commit -m "feat: add versioned math scene snapshots"
```

## Task 2: Implement `.math` SQLite Session Storage and Startup Recovery

**Files:**
- Create: `agent/session_store.py`
- Create: `tests/test_session_store.py`

- [ ] **Step 1: Write failing storage tests**

Cover automatic `.math` creation below an application data root, WAL mode, session creation, turn insertion, event insertion, attachment insertion, and reopening the database. Use `TemporaryDirectory`, never the real user profile.

```python
def test_store_creates_math_database_and_round_trips_turn(tmp_path):
    store = SessionStore(app_root=tmp_path)
    session = store.create_session("New Chat", model="deepseek-chat")
    turn_id = store.append_turn(
        session.id,
        user_message="画 y=x^2",
        assistant_message="已生成曲线计划",
        scene_before=empty_snapshot,
        scene_after=curve_snapshot,
        command_plan={"version": 1, "operations": []},
        status="completed",
    )
    assert (tmp_path / ".math" / "mathagent.db").exists()
    assert store.get_turn(turn_id).scene_after == curve_snapshot
```

Also test that `SessionStore` resolves the OS application-data root when no root is injected, persists `active_mode`, `execution_mode`, `model`, `current_turn_id`, `last_opened_at`, `closed_at`, and `parent_session_id`, and that closing a tab only marks the session closed without deleting turns. Test `app_state` round-trips the last open session IDs, active session ID, and a final scene snapshot.

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `uv run pytest tests/test_session_store.py -q`

Expected: FAIL because `SessionStore` is not defined.

- [ ] **Step 3: Implement schema and migrations**

Create `.math/mathagent.db`, `.math/attachments`, `.math/previews`, and `.math/exports` below an injected `app_root`. When no root is injected, resolve `%APPDATA%/Math3DTeaching` on Windows, `~/Library/Application Support/Math3DTeaching` on macOS, and `~/.local/share/Math3DTeaching` on Linux. Configure `PRAGMA journal_mode=WAL` and `PRAGMA foreign_keys=ON`. Create `sessions`, `turns`, `events`, `attachments`, and `app_state` tables matching the design document, including per-session mode/model, branch parent, current pointer, open-session state, and final scene snapshot. Store snapshots and plans as UTF-8 JSON text.

- [ ] **Step 4: Implement CRUD with transactions**

Provide `create_session`, `list_sessions`, `rename_session`, `close_session`, `reopen_session`, `append_turn`, `append_event`, `add_attachment`, `get_turn`, `list_turns`, `set_current_turn`, `save_app_state`, `load_app_state`, and `restore_last_open_sessions`. Every write uses a short transaction and returns domain dataclasses; UI code must not receive raw sqlite rows. `close_session` must never delete history.

- [ ] **Step 5: Run storage and runtime regression tests**

Run: `uv run pytest tests/test_session_store.py tests/test_agent_runtime.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/session_store.py tests/test_session_store.py
git commit -m "feat: persist MathAgent sessions in sqlite"
```

## Task 3: Add Conversation and Event Domain Models

**Files:**
- Create: `agent/conversation.py`
- Create: `agent/events.py`
- Create: `tests/test_conversation.py`
- Create: `tests/test_agent_events.py`

- [ ] **Step 1: Write failing branch and event tests**

Test that a new turn after restoring an earlier turn gets `parent_turn_id` set to the restored turn, old turns remain intact, and `branch_from_turn()` creates a separate session with copied context. Test event serialization rejects unknown event types and round-trips payload JSON.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `uv run pytest tests/test_conversation.py tests/test_agent_events.py -q`

Expected: FAIL because the domain models are not defined.

- [ ] **Step 3: Implement the domain models**

Define `ConversationSession`, `ConversationTurn`, `BranchPointer`, and `AgentEvent`. Keep them independent of Qt and SQLite. Define the event type literal set from the design document. `branch_from_turn()` must preserve the original session and return a new session id plus copied snapshot/context references.

- [ ] **Step 4: Connect models to `SessionStore`**

Add a thin repository method that loads a session timeline and current pointer into the domain models. Do not duplicate SQL in UI widgets.

- [ ] **Step 5: Run focused tests**

Run: `uv run pytest tests/test_conversation.py tests/test_agent_events.py tests/test_session_store.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/conversation.py agent/events.py tests/test_conversation.py tests/test_agent_events.py
git commit -m "feat: add MathAgent conversation events and branches"
```

## Task 3A: Add Context Broker and Attachment Pipeline

**Files:**
- Create: `agent/context_broker.py`
- Modify: `agent/runtime.py`
- Modify: `agent/session_store.py`
- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Create: `tests/test_context_broker.py`

- [ ] **Step 1: Write failing Context Broker tests**

Test that a context package contains a compact scene summary, selected-object summary, recent full messages, compressed older messages, attachment metadata/text, and `used_tokens`/`max_tokens`. Test the limits: six attachments are rejected, a 10 MB + 1 byte image is rejected, and a 20 MB + 1 byte document is rejected.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `uv run pytest tests/test_context_broker.py -q`

Expected: FAIL because `ContextBroker` is not defined.

- [ ] **Step 3: Implement deterministic context packing**

Create `ContextPackage` and `ContextBroker.build(...)`. Include current scene and selected object as structured JSON, keep the newest messages verbatim, summarize older messages with a bounded deterministic summary, and include PDF/text extraction results. Do not add a vector database. Use provider token usage when available and a documented local estimate otherwise.

- [ ] **Step 4: Implement attachment validation and storage**

Accept images, PDFs, and plain text. Enforce five attachments per turn, 10 MB per image, and 20 MB per PDF/text file. Copy accepted files into `.math/attachments/`, compute SHA-256, and store only relative paths and metadata in SQLite. Use `pypdf` for PDF text extraction. If the selected provider advertises no image input support, return a user-facing capability error while allowing text/document attachments.

- [ ] **Step 5: Connect per-session mode/model and usage events**

Pass the session's `active_mode`, `execution_mode`, and `model` into the Runtime request. Emit a context usage event containing only `used_tokens`, `max_tokens`, and `percentage`; never emit hidden reasoning content.

- [ ] **Step 6: Run focused tests**

Run: `uv run pytest tests/test_context_broker.py tests/test_session_store.py tests/test_agent_runtime.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add agent/context_broker.py agent/runtime.py agent/session_store.py pyproject.toml requirements.txt tests/test_context_broker.py
git commit -m "feat: add context broker and attachment handling"
```

## Task 4: Add Structured Mathematical Tool Registry

**Files:**
- Create: `agent/tool_registry.py`
- Modify: `agent/skills/geometry/handler.py`
- Modify: `agent/skills/calculus/handler.py`
- Modify: `agent/skills/linear_algebra/handler.py`
- Create: `tests/test_agent_tools.py`

- [ ] **Step 1: Write failing tool tests**

Cover `inspect_scene`, `calculate_expression`, `create_curve`, `create_tangent`, `create_integral_area`, and `create_determinant_demo`. Assert every mutating tool returns a `CommandPlan`, rejects invalid arguments, and passes `SceneCommandService.preview()`. Assert no handler imports PySide6 or PyVista.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `uv run pytest tests/test_agent_tools.py -q`

Expected: FAIL because the registry and tool functions are not defined.

- [ ] **Step 3: Implement schemas and dispatch**

Define a `ToolSpec(name, description, input_schema, handler, mutating)` dataclass. Use Pydantic models to validate tool arguments and emit JSON Schema. Make handlers call existing Skills and `SceneCommandService.preview()`; do not let a tool call `execute()`.

- [ ] **Step 4: Add approval-only execution**

Implement `apply_plan(plan_id)` in the registry as a Runtime callback, not a direct renderer call. The callback must re-fetch the stored plan, call `preview()`, and only then call `SceneCommandService.execute()`.

- [ ] **Step 5: Run tool and scene tests**

Run: `uv run pytest tests/test_agent_tools.py tests/test_scene_commands.py tests/test_agent_runtime.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/tool_registry.py agent/skills tests/test_agent_tools.py
git commit -m "feat: expose validated mathematical agent tools"
```

## Task 5: Upgrade DeepSeek Provider to Streaming Tool Calls

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Modify: `services/agent_provider.py`
- Modify: `agent/providers/deepseek_provider.py`
- Modify: `tests/test_agent_provider.py`

- [ ] **Step 1: Write failing provider tests**

Test that a streaming response emits text deltas, accumulates a function tool call, preserves `tool_call_id`, and serializes a tool result message for the next request. Test `response_format`/strict schema options are only sent when enabled and API errors mask the API key.

```python
events = list(provider.stream(messages, tools=tool_specs))
assert [event.type for event in events] == ["message_delta", "tool_call", "completed"]
assert events[1].name == "create_curve"
```

- [ ] **Step 2: Run provider tests and verify failure**

Run: `uv run pytest tests/test_agent_provider.py -q`

Expected: FAIL because the provider has no streaming/tool-call interface.

- [ ] **Step 3: Add dependencies and typed provider protocol**

Add `openai` and `pydantic` to both dependency declarations. Define `ProviderEvent`, `ToolCall`, and `ToolResultMessage` in `services/agent_provider.py`. Keep `create_plan()` as a compatibility wrapper that consumes the new stream and returns `AgentResponse`.

- [ ] **Step 4: Implement DeepSeek streaming**

Use the configured OpenAI-compatible base URL and model. Send `stream=True`, tool schemas, `tool_choice="auto"`, and the configured thinking/reasoning options. Parse SSE/tool deltas without exposing `reasoning_content` as hidden chain-of-thought in the UI. Return only safe summaries and structured tool arguments to Runtime.

- [ ] **Step 5: Run provider regression tests**

Run: `uv run pytest tests/test_agent_provider.py tests/test_agent_settings.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml requirements.txt services/agent_provider.py agent/providers/deepseek_provider.py tests/test_agent_provider.py
git commit -m "feat: stream DeepSeek tool calls"
```

## Task 6: Implement the Cancellable Dual-Mode Runtime

**Files:**
- Modify: `agent/runtime.py`
- Modify: `services/agent_worker.py`
- Modify: `ui/designer_window.py`
- Create: `tests/test_agent_runtime_loop.py`

- [ ] **Step 1: Write failing Runtime tests**

Use a fake streaming provider and fake command host. Test:

1. Confirm mode stops at `approval_required` and does not mutate the host.
2. Continuous mode calls `SceneCommandService.execute()` after validation.
3. Ask mode refuses mutation and returns a question.
4. Plan mode returns a plan without execution.
5. Validation failure triggers one bounded repair attempt.
6. Stop cancels the provider and prevents later tool calls.
7. A completed turn stores before/after snapshots and an event timeline.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `uv run pytest tests/test_agent_runtime_loop.py -q`

Expected: FAIL because the current Runtime performs one non-streaming request.

- [ ] **Step 3: Implement Runtime state transitions**

Add `run_turn(session_id, prompt, mode, execution_mode, context)` and `stop(session_id)`. Emit `AgentEvent` objects for every state transition. Limit repair attempts and tool calls with explicit constants. Keep `validate(plan)` and `execute(plan)` as compatibility methods.

- [ ] **Step 4: Add atomic turn persistence**

Capture `scene_before` before planning. On successful execution capture `scene_after`, persist plan/validation/events, and update the session current pointer. On rejection, cancellation, or failure persist the turn with the correct status and no fake after snapshot.

- [ ] **Step 5: Connect worker signals**

Replace one-shot `response_ready` flow with `event_ready`, `turn_finished`, `error`, and `finished`. Add a cancellation slot that the UI can invoke without touching Runtime internals.

- [ ] **Step 6: Run Runtime and existing Agent tests**

Run: `uv run pytest tests/test_agent_runtime_loop.py tests/test_agent_runtime.py tests/test_agent_provider.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add agent/runtime.py services/agent_worker.py ui/designer_window.py tests/test_agent_runtime_loop.py
git commit -m "feat: add cancellable MathAgent execution modes"
```

## Task 7: Replace the Sidebar Shell and Add Session Tabs

**Files:**
- Modify: `ui/agent_sidebar.py`
- Modify: `ui/agent_panel.py`
- Modify: `ui/designer_window.py`
- Modify: `tests/test_agent_panel.py`
- Modify: `tests/test_sidebar.py`
- Modify: `tests/test_main_window_layout.py`

- [ ] **Step 1: Write failing UI tests**

Test that the Agent panel is absent/hidden at startup, the viewport Agent button opens it, closing removes its layout slot, `+` creates a tab, tabs switch sessions, and closing a tab never leaves zero sessions. Test mode selector options and hover action visibility state.

- [ ] **Step 2: Run focused UI tests and verify failure**

Run: `uv run pytest tests/test_agent_panel.py tests/test_sidebar.py tests/test_main_window_layout.py -q`

Expected: FAIL because the existing sidebar exposes a permanent 40px collapsed bar.

- [ ] **Step 3: Implement panel visibility**

Remove the collapsed bar from the normal layout. Keep an `AgentSidebar` instance but insert it into the root layout only while open, with a fixed width of 440px. On close, remove/hide it and restore the viewport. The existing viewport toolbar Agent icon becomes the only open affordance. At startup restore sessions and the last scene in the background while leaving this panel hidden.

- [ ] **Step 4: Implement header and tab model**

Add `MathAgent`, icon-only new/history/settings buttons with tooltips, and a `QTabBar` or equivalent tab strip. Tabs bind to `ConversationSession.session_id`; switching tabs never changes the current scene unless the user explicitly restores a turn.

- [ ] **Step 5: Implement empty state and mode controls**

Add the title/subtitle/feature cards, the `Agent`/`Ask`/`Plan` selector, confirmation-vs-continuous execution selector for Agent mode, and the exact composer placeholder `提问或输入 "/"快捷命令`. Persist mode, execution strategy, and model per session; new sessions default to `Agent + 确认执行`.

- [ ] **Step 6: Add the read-only context usage ring**

Render a ring in the lower-right composer toolbar. It is not clickable; on hover it displays the percentage from the latest `context_usage` event. Do not expose a context configuration button in this position.

- [ ] **Step 7: Run UI tests**

Run: `uv run pytest tests/test_agent_panel.py tests/test_sidebar.py tests/test_main_window_layout.py -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add ui/agent_sidebar.py ui/agent_panel.py ui/designer_window.py tests/test_agent_panel.py tests/test_sidebar.py tests/test_main_window_layout.py
git commit -m "feat: add MathAgent panel and conversation tabs"
```

## Task 8: Add WebView Timeline and Message Bridge

**Files:**
- Create: `ui/agent_web/index.html`
- Create: `ui/agent_web/app.js`
- Create: `ui/agent_web/style.css`
- Modify: `ui/agent_panel.py`
- Create: `tests/test_agent_web_protocol.py`

- [ ] **Step 1: Write protocol tests**

Test pure JSON messages for `render_event`, `send_message`, `approve_plan`, `stop_session`, `undo_turn`, and `branch_from_turn`. Reject commands without a session/turn id and reject unknown message types.

- [ ] **Step 2: Run protocol tests and verify failure**

Run: `uv run pytest tests/test_agent_web_protocol.py -q`

Expected: FAIL because the bridge schema is not defined.

- [ ] **Step 3: Implement the local WebView document**

Render event cards for user/assistant text, context, calculation, plan, preview, execution and error. Use Markdown-it and bundled KaTeX assets. Keep all CSS local; do not load remote scripts or network content.

- [ ] **Step 4: Implement hover actions and composer**

Action buttons are hidden until a successful turn card is hovered. The composer renders left tools, attachment button, mode selector, per-session model selector, read-only context usage ring, send/stop button, and queued-message state. The context ring is not clickable.

- [ ] **Step 5: Implement the Python bridge**

Use `QWebChannel` or a narrow `runJavaScript()` adapter. WebView messages become Qt signals only; they never call `SceneCommandService` directly. Sanitize text and keep payloads JSON-only.

- [ ] **Step 6: Run protocol and UI tests**

Run: `uv run pytest tests/test_agent_web_protocol.py tests/test_agent_panel.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add ui/agent_web ui/agent_panel.py tests/test_agent_web_protocol.py
git commit -m "feat: render MathAgent timeline in local webview"
```

## Task 9: Add In-Panel History, Restore, Undo, and Branch Actions

**Files:**
- Create: `ui/agent_history.py`
- Modify: `ui/agent_panel.py`
- Modify: `ui/designer_window.py`
- Modify: `agent/session_store.py`
- Modify: `tests/test_conversation.py`
- Create: `tests/test_agent_history.py`

- [ ] **Step 1: Write failing history tests**

Test that a successful turn shows a thumbnail and three hover actions; restoring uses `scene_after` without a model call; undo uses `scene_before`; branching creates a new session while leaving the original session unchanged.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `uv run pytest tests/test_agent_history.py tests/test_conversation.py -q`

Expected: FAIL because history UI and snapshot actions are not connected.

- [ ] **Step 3: Implement history view**

The clock button replaces the current timeline inside the same right panel with a history view. Show a back button, sessions grouped by title, and each turn's prompt, short result, timestamp, thumbnail and hover actions. Do not open a separate dialog or expose raw database rows. Closing a session tab must preserve the session and turns so the history view can reopen it.

- [ ] **Step 4: Implement restore and undo commands**

`restore_turn(turn_id)` captures the current scene for an in-memory undo guard, restores `scene_after`, updates the current pointer, and refreshes the existing renderer. `undo_turn(turn_id)` restores `scene_before`. Neither path invokes the model.

- [ ] **Step 5: Implement new-session branching**

`branch_from_turn(turn_id)` creates a new session tab with copied snapshot/context and necessary prior messages, sets `parent_session_id` to the source session ID, and leaves the original session and turns untouched.

- [ ] **Step 6: Run history and scene regression tests**

Run: `uv run pytest tests/test_agent_history.py tests/test_conversation.py tests/test_scene_snapshot.py tests/test_layer_scene.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add ui/agent_history.py ui/agent_panel.py ui/designer_window.py agent/session_store.py tests/test_conversation.py tests/test_agent_history.py
git commit -m "feat: restore undo and branch MathAgent turns"
```

## Task 10: Settings, Attachments, and End-to-End Acceptance

**Files:**
- Modify: `ui/agent_settings.py`
- Modify: `agent/instruction.py`
- Modify: `agent/memory.py`
- Modify: `tests/test_agent_settings.py`
- Create: `tests/test_mathagent_acceptance.py`
- Modify: `README.md`

- [ ] **Step 1: Extend settings tests**

Test model switching, Agent/Ask/Plan and execution-strategy persistence per session, attachment copying into `.math/attachments`, five-file/size limits, unsupported-image-model messaging, and that API keys are never written to `mathagent.db`.

- [ ] **Step 2: Implement settings integration**

Keep provider credentials in QSettings. Store provider name/model and per-session mode/execution strategy in session rows. Connect existing Instructions and Memory editors to the Runtime when a new turn starts. Keep the history button in-panel and make tab close a non-destructive close rather than deletion.

- [ ] **Step 3: Implement end-to-end acceptance tests**

Use a fake provider and fake scene host to verify:

```text
start app -> restore sessions and app_state last scene while panel stays hidden
open panel -> create tab -> send prompt -> event cards
confirm mode -> plan waits -> apply -> scene changes
continuous mode -> plan auto-applies -> undo works
Ask mode -> mutation asks first
Plan mode -> no scene mutation
restore old turn -> continue -> branch record appears
branch button -> new tab, original unchanged
clock -> in-panel history -> back -> timeline
close tab -> history remains -> reopen tab
```

- [ ] **Step 4: Run the complete suite**

Run: `uv run pytest -q`

Expected: all existing 2D, 3D, PyVista, SymPy, layer, and Agent tests PASS.

- [ ] **Step 5: Run static checks and import checks**

Run: `python -m compileall agent services ui tests` and `git diff --check`.

Expected: no compilation errors and no whitespace errors.

- [ ] **Step 6: Update README**

Document the hidden panel toggle, Agent/Ask/Plan modes, confirmation/continuous execution, `.math` storage location, history restore, undo, and branch behavior. Do not document arbitrary code execution because it is explicitly unsupported.

- [ ] **Step 7: Commit**

```bash
git add ui/agent_settings.py agent/instruction.py agent/memory.py tests/test_agent_settings.py tests/test_mathagent_acceptance.py README.md
git commit -m "test: verify MathAgent sidebar end to end"
```

## Risks and Mitigations

- **QWebEngine unavailable in the runtime:** check the import before Task 7; if unavailable, install the full PySide6 distribution rather than silently falling back to the old JSON panel.
- **DeepSeek tool-call format differs by model:** keep a provider adapter, validate every tool argument with Pydantic, and use a fake stream fixture in tests.
- **Scene snapshot drift:** include a snapshot version and reject unsupported versions instead of partially restoring.
- **Restore corrupts the active scene:** capture an in-memory pre-restore snapshot and restore through the existing transaction/render path.
- **SQLite blocks the UI:** keep all storage calls short and off the UI thread for event-heavy writes; enable WAL and batch event inserts per turn.
- **Attachment/context growth:** enforce the five-file and per-file size limits before the provider call; cap old-message summaries and expose only the usage percentage in the ring.
- **Unsupported vision model:** inspect provider capabilities before sending image parts and show a clear capability error instead of silently changing models.
- **Startup restore surprises the user:** restore the last scene in the background while keeping the Agent panel hidden; provide history recovery if the snapshot is invalid.
- **WebView bypasses safety:** expose only JSON message signals; never expose a Python object, Qt pointer, PyVista object, or command-service callable to JavaScript.
- **Scope creep toward a code IDE:** keep the tool registry math-only and reject file/terminal tools in this product.

## Self-Review

- Panel visibility, title icons, tabs, empty state, composer, Agent/Ask/Plan, confirmation/continuous modes, hover actions, history, restore, undo, and branch behavior each have explicit tasks.
- Every scene mutation path still ends in `SceneCommandService.execute()`.
- Every persistence requirement has a schema or test task.
- Startup restore, per-session mode/model, Context Broker, attachment limits, in-panel history, and non-destructive tab close each have explicit implementation and acceptance coverage.
- No task depends on an unspecified project-root workflow; `.math` is application-managed.
- No raw API key is persisted in SQLite.
- 计划没有使用未定义的占位步骤。
