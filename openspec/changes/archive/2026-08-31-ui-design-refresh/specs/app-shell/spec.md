## ADDED Requirements

### Requirement: Status bar

The main window SHALL provide a compact bottom status bar showing the current scene mode (`2D`/`3D`), the active 2D tool state when one is active, scene render status, and the Agent connection state. The status bar SHALL include the theme mode toggle. It SHALL not host business operations and SHALL not wrap or overflow at the minimum window width.

#### Scenario: Mode indication
- **WHEN** the user switches between 2D and 3D scene modes
- **THEN** the status bar mode segment updates immediately

#### Scenario: Agent state indication
- **WHEN** the Agent panel is hidden or no model is configured or a turn is running
- **THEN** the status bar shows the corresponding Agent state with token-styled status color
- **AND** clicking the Agent segment toggles the Agent panel visibility

#### Scenario: Theme toggle
- **WHEN** the user clicks the status bar theme toggle
- **THEN** the theme mode cycles through light, dark, and system and the current mode is shown in the tooltip

### Requirement: Panel sizing and resizing

The main window SHALL arrange three primary regions — algebra panel, viewport, and Agent panel — where the algebra panel is adjustable by dragging a divider handle between 260 and 420px with a default of 320px, the Agent panel is adjustable by dragging a divider handle between 360 and 560px with a default of 440px, and the viewport takes the remaining space. Both handles SHALL restore their panel's default width on double-click, SHALL be clamped to the allowed range during dragging, and both panel widths SHALL persist across sessions. The algebra handle SHALL remain visible at all times; the Agent handle SHALL appear only while the Agent panel is visible. The Agent panel SHALL occupy no layout space when closed.

#### Scenario: Resize agent panel
- **WHEN** the user drags the divider between the viewport and the Agent panel
- **THEN** the Agent panel width follows the pointer and is clamped to the 360–560px range
- **AND** the new width persists after restart

#### Scenario: Resize algebra panel
- **WHEN** the user drags the divider between the algebra panel and the viewport
- **THEN** the algebra panel width follows the pointer and is clamped to the 260–420px range
- **AND** the new width persists after restart

#### Scenario: Divider reset
- **WHEN** the user double-clicks either divider
- **THEN** the corresponding panel returns to its default width (algebra 320px, Agent 440px)

#### Scenario: Closed panel frees space
- **WHEN** the Agent panel is collapsed
- **THEN** the viewport expands to the freed space, the Agent divider hides, and no placeholder strip remains

### Requirement: Overlay chrome consistency

Floating viewport controls — the main viewport toolbar, the 2D geometry toolbar with its flyout, and the scene settings panel — SHALL share one overlay visual style generated from tokens: overlay background, subtle border, medium radius, and overlay shadow. Their icon buttons SHALL use a uniform 36px hit area with 16px SVG icons. Dialogs and large popovers SHALL use the large radius with the modal shadow.

#### Scenario: Overlay family
- **WHEN** any floating control becomes visible
- **THEN** its background, border, radius, shadow, and button metrics match the shared overlay token style
- **AND** hover feedback uses the token soft accent background in both themes

### Requirement: Visual hierarchy and panel separation

The shell SHALL separate the algebra panel, viewport, and Agent sidebar by background tonal steps (panel lighter than scene lighter than canvas) without 1px divider borders between regions. Group labels inside panels SHALL use the section-header style (caption size, muted color, increased letter spacing). Layer rows in the algebra panel SHALL render as cards: elevated background, medium radius, no default border, a 4px leading color strip reflecting the layer color, a border appearing on hover, and an accent border with soft accent background when selected.

#### Scenario: Tonal separation
- **WHEN** the main window renders in either theme
- **THEN** the three regions are distinguishable by background tone alone
- **AND** no 1px border is drawn between the algebra panel and the viewport or between the viewport and the Agent sidebar

#### Scenario: Layer row states
- **WHEN** the pointer hovers a layer row or the row is selected
- **THEN** the row shows a subtle border on hover, and an accent border with soft accent background when selected
- **AND** the row shows a 4px leading strip in the layer's color at all times

#### Scenario: Section headers
- **WHEN** a panel renders a group label such as the layer list header
- **THEN** it uses caption size, muted color, and letter spacing instead of a bordered or boxed header

### Requirement: Control metric scale

Interactive controls SHALL use only three height grades: 36px for toolbar icon buttons, 32px for form controls (inputs, combo boxes, primary buttons), and 28px for in-row small buttons. Random one-off control sizes SHALL be removed.

#### Scenario: Unified metrics
- **WHEN** toolbars, forms, and list rows render their controls
- **THEN** every control height matches one of the three token grades
- **AND** the retired 38px, 40px, and 30px ad-hoc sizes no longer appear

### Requirement: Title hierarchy

Panel titles across the shell SHALL follow the token typography scale, with main panel titles at the token subtitle size and weight, and the main window title SHALL be `Math3D Teaching` without trailing whitespace.

#### Scenario: Title consistency
- **WHEN** the algebra panel and the Agent sidebar render their headers
- **THEN** both use the same token title style and neither renders a 20px title

### Requirement: Removal of dead UI code

The application SHALL delete the unused legacy `ui/main_window.py` window, remove the dead sidebar configuration from `ui/main_window.ui`, and remove stylesheet selectors that target the retired Qt chat panel. Comments and constants describing panel dimensions SHALL match the implementation.

#### Scenario: No dead stylesheet selectors
- **WHEN** the global stylesheet is generated
- **THEN** it contains no selectors for the retired `#agentPanel`, `#agentMessageScroll`, `#agentUserBubble`, `#agentAssistantBubble`, or `#agentPlanCard` widgets

#### Scenario: Layout tests updated
- **WHEN** the main window layout tests load the `.ui` file
- **THEN** they assert only the live widgets (root layout, central widget, viewport host) and pass

### Requirement: Teaching case popup

The algebra panel SHALL present built-in teaching cases through a grouped popup styled with the shared overlay chrome (overlay background, default border, large radius, overlay shadow, appear animation). Case rows SHALL render as two-line cards (name + summary) with token padding, medium radius, a soft accent hover background with a leading accent indicator, and a muted single-line-clamped summary. Selecting a case SHALL close the popup, rebuild the 2D scene from the case plan, and open the case reader in the Agent sidebar.

#### Scenario: Popup chrome
- **WHEN** the user opens the teaching case popup
- **THEN** it renders with the shared overlay style including border, large radius, shadow, and a short appear animation
- **AND** category labels use the section-header style

#### Scenario: Case row hover
- **WHEN** the pointer hovers a case row
- **THEN** the row shows a soft accent background with a leading accent indicator
- **AND** the summary remains clamped and muted

#### Scenario: Load a case
- **WHEN** the user selects a case
- **THEN** the popup closes, the 2D scene is rebuilt from the case plan, and the Agent sidebar opens the case reader tab (expanding the sidebar if hidden)

#### Scenario: Unknown case
- **WHEN** a requested case id does not exist
- **THEN** the scene is left unchanged and an error status is shown in the algebra panel
