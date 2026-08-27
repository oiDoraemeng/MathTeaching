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

The main window SHALL arrange three primary regions — algebra panel, viewport, and Agent panel — where the algebra panel remains adjustable between 300 and 360px, the Agent panel is adjustable between 360 and 560px with a default of 440px, and the viewport takes the remaining space. The Agent panel width SHALL persist across sessions, and the Agent panel SHALL occupy no layout space when closed.

#### Scenario: Resize agent panel
- **WHEN** the user drags the divider between the viewport and the Agent panel
- **THEN** the Agent panel width follows the pointer and is clamped to the 360–560px range
- **AND** the new width persists after restart

#### Scenario: Closed panel frees space
- **WHEN** the Agent panel is collapsed
- **THEN** the viewport expands to the freed space and no placeholder strip remains

### Requirement: Overlay chrome consistency

Floating viewport controls — the main viewport toolbar, the 2D geometry toolbar with its flyout, and the scene settings panel — SHALL share one overlay visual style generated from tokens: overlay background, default border, medium radius, and overlay shadow. Their buttons SHALL use a uniform 32px size with 16px SVG icons.

#### Scenario: Overlay family
- **WHEN** any floating control becomes visible
- **THEN** its background, border, radius, shadow, and button metrics match the shared overlay token style
- **AND** hover feedback uses the token soft accent background in both themes

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
