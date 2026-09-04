## MODIFIED Requirements

### Requirement: Status bar

The main window SHALL provide a compact bottom status bar showing the current scene mode (`2D`/`3D`), the active 2D tool state when one is active, scene render status, and the Agent connection state. The status bar SHALL include the theme mode toggle. All status bar segments — labels and buttons alike — SHALL render at the caption token font size so no segment appears larger or smaller than its neighbors. It SHALL not host business operations and SHALL not wrap or overflow at the minimum window width.

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

#### Scenario: Uniform segment type size
- **WHEN** the status bar renders the Agent state segment next to the mode and render status labels
- **THEN** the Agent segment text and the labels use the same caption token size in both themes

### Requirement: Panel sizing and resizing

The main window SHALL arrange three primary regions — algebra panel, viewport, and Agent panel — where the algebra panel is adjustable by dragging a divider handle between 260 and 420px with a default of 320px, the Agent panel is adjustable by dragging a divider handle between 360 and 720px with a default of 440px, and the viewport takes the remaining space. Both handles SHALL be visually discoverable at rest: a visible thin indicator strip on the panel border color in both themes, an accent highlight while hovered or dragged, and a tooltip explaining drag-to-resize and double-click-to-reset. Both handles SHALL restore their panel's default width on double-click, SHALL be clamped to the allowed range during dragging, and both panel widths SHALL persist across sessions. The algebra handle SHALL remain visible at all times; the Agent handle SHALL appear only while the Agent panel is visible. The Agent panel SHALL occupy no layout space when closed.

#### Scenario: Resize agent panel
- **WHEN** the user drags the divider between the viewport and the Agent panel
- **THEN** the Agent panel width follows the pointer and is clamped to the 360–720px range
- **AND** the new width persists after restart

#### Scenario: Resize algebra panel
- **WHEN** the user drags the divider between the algebra panel and the viewport
- **THEN** the algebra panel width follows the pointer and is clamped to the 260–420px range
- **AND** the new width persists after restart

#### Scenario: Divider reset
- **WHEN** the user double-clicks either divider
- **THEN** the corresponding panel returns to its default width (algebra 320px, Agent 440px)

#### Scenario: Divider discoverability
- **WHEN** either divider is at rest, hovered, or being dragged in either theme
- **THEN** the divider presents a visible indicator strip, an accent-colored highlight on hover or drag, and a resize tooltip
- **AND** a persisted Agent panel width previously clamped at the old 560px maximum is restored up to the new 720px maximum

#### Scenario: Closed panel frees space
- **WHEN** the Agent panel is collapsed
- **THEN** the viewport expands to the freed space, the Agent divider hides, and no placeholder strip remains

### Requirement: Overlay chrome consistency

Floating viewport controls — the main viewport toolbar, the 2D geometry toolbar with its flyout, and the scene settings panel — SHALL share one overlay visual style generated from tokens: overlay background, subtle border, medium radius, and overlay shadow. Their icon buttons SHALL use a uniform 36px hit area with 16px SVG icons. Any text rendered on overlay buttons SHALL use a token scale font size rather than a hardcoded size. Interactive shell controls SHALL carry accessible names so assistive technologies can identify them. Dialogs and large popovers SHALL use the large radius with the modal shadow.

#### Scenario: Overlay family
- **WHEN** any floating control becomes visible
- **THEN** its background, border, radius, shadow, and button metrics match the shared overlay token style
- **AND** hover feedback uses the token soft accent background in both themes

#### Scenario: Overlay button typography
- **WHEN** the viewport toolbar renders its scene mode ("2D"/"3D") button
- **THEN** its text uses a token scale size instead of a hardcoded 18px size

#### Scenario: Shell accessibility names
- **WHEN** assistive technology inspects the main window toolbars and status bar controls
- **THEN** every interactive control exposes an accessible name matching its tooltip or visible label

### Requirement: Lighting dialog theming and interaction

The lighting dialog's self-drawn rotation widget SHALL take its card, label, and accent colors from the design tokens of the effective theme. Resetting lighting to defaults SHALL update the dialog controls in place without closing the dialog, and value sliders SHALL display their current numeric value next to the slider.

#### Scenario: Reset keeps dialog open
- **WHEN** the user restores default lighting
- **THEN** all lighting controls reflect the default values and the dialog remains open for further adjustment

#### Scenario: Slider value readouts
- **WHEN** the user drags an ambient or intensity slider
- **THEN** a numeric label next to the slider shows the current value and updates live

#### Scenario: Rotation widget dark theme
- **WHEN** the lighting dialog opens in the dark theme
- **THEN** the rotation widget renders with the dark theme token colors and no light-only hardcoded card
