# ui-design-system Specification

## Purpose
TBD - created by archiving change ui-design-refresh. Update Purpose after archive.

## Requirements

### Requirement: Design token single source of truth

The application SHALL define all visual styling values (colors, typography, spacing, radius, shadows) as semantic design tokens in one version-controlled JSON file, loaded by a typed Python module and consumed by the Agent Web frontend build. Style code SHALL reference semantic token names instead of ad-hoc literal values.

#### Scenario: Token-generated Qt stylesheet
- **WHEN** the application applies its global stylesheet
- **THEN** the stylesheet is rendered from a QSS template substituted with the design tokens for the current effective theme
- **AND** no panel-level widget style uses hardcoded border-gray literals from the five legacy gray values

#### Scenario: Token-generated web theme
- **WHEN** the Agent Web frontend is built
- **THEN** its CSS custom properties for both light and dark themes are generated from the same token file
- **AND** a missing or corrupt token file falls back to built-in light tokens without failing the build

#### Scenario: Token validation at startup
- **WHEN** the application starts and the token file is structurally invalid (missing theme keys, unparsable colors, or mismatched theme key sets)
- **THEN** startup fails fast with a descriptive token error instead of rendering a partially themed UI

#### Scenario: Single accent color
- **WHEN** either the Qt shell or the Agent Web UI renders an accent-colored control
- **THEN** both surfaces use the accent hue defined by the token file for the current theme
- **AND** the legacy web accent values `#3794ff` and `#006ab1` are no longer used

### Requirement: Light and dark themes

The application SHALL support `light`, `dark`, and `system` theme modes, persisted in QSettings, with `system` following the OS color scheme and reacting to OS theme changes without restart. Every surface — panels, viewport overlays, dialogs, status bar, and the Agent sidebar — SHALL render a complete token set in both themes meeting WCAG AA contrast for text.

#### Scenario: Switch theme at runtime
- **WHEN** the user switches the theme mode from the status bar control
- **THEN** the Qt shell, floating overlays, and dialogs restyle immediately
- **AND** the Agent sidebar, if loaded, receives a `theme_state` event carrying only the effective mode and restyles without reload
- **AND** the choice persists across application restarts

#### Scenario: OS theme change
- **WHEN** the OS color scheme changes while the theme mode is `system`
- **THEN** the effective theme is recomputed and applied to all surfaces without restart

#### Scenario: 3D canvas follows theme
- **WHEN** the effective theme changes and the user has not chosen an explicit scene background override
- **THEN** the 3D background and 2D grid colors switch to the theme-appropriate defaults

### Requirement: Typography scale

The application SHALL set one application-wide font family and size on `QApplication`, SHALL express all font sizes in pixels from the token scale (11/12/13/15), and SHALL remove per-widget hardcoded font families and point-size overrides.

#### Scenario: Consistent fonts
- **WHEN** the main window renders with default system font availability
- **THEN** all Qt labels, buttons, and inputs use the application font and a token font size
- **AND** no widget hardcodes a specific platform font family

#### Scenario: Document typography distinct from chrome
- **WHEN** a reading surface such as the teaching case reader renders its document title
- **THEN** it uses the 20px document-title style
- **AND** panel chrome titles elsewhere remain at the 15px token title size

### Requirement: Unified icon language

All Qt toolbar, panel, and status bar icon buttons SHALL use vector SVG icons rendered and tinted through a shared icon module, matching the icon names and stroke style already used by the Agent Web UI. Unicode character icons SHALL not be used for controls.

#### Scenario: Icon tinting per theme
- **WHEN** the effective theme changes
- **THEN** Qt icon buttons re-render their SVG icons in the token icon colors for that theme
- **AND** the icons remain visually consistent with the lucide icons used in the Agent Web UI

#### Scenario: High-DPI icon rendering
- **WHEN** icons render on a display with device pixel ratio greater than 1
- **THEN** the icon module renders at the physical resolution and icons appear sharp without a per-resolution asset set

### Requirement: Depth, motion, and focus

The token system SHALL define two shadow levels (overlay, modal) and a motion scale (120/150/200ms with a shared ease-out curve). Floating chrome SHALL use shadow instead of heavy borders to express elevation, popovers and panels SHALL animate with the motion scale, and keyboard focus SHALL be indicated by a visible 2px accent focus ring. Web surfaces SHALL respect `prefers-reduced-motion` by disabling transitions.

#### Scenario: Elevation through shadow
- **WHEN** a floating toolbar or popover appears over the viewport
- **THEN** its elevation is expressed by the overlay or modal shadow token rather than a strong border

#### Scenario: Animated popover
- **WHEN** a floating panel opens or closes
- **THEN** it animates opacity and a small translation within the 150–200ms motion range using the shared ease-out curve

#### Scenario: Keyboard focus visible
- **WHEN** the user navigates controls with the keyboard
- **THEN** the focused control shows a 2px accent focus ring
- **AND** pointer interaction does not leave a persistent focus ring

#### Scenario: Reduced motion on web
- **WHEN** the OS requests reduced motion
- **THEN** the Agent Web UI disables its transitions
