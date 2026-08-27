## ADDED Requirements

### Requirement: Design token single source of truth

The application SHALL define all visual styling values (colors, typography, spacing, radius, shadows) as semantic design tokens in one Python module, and both the Qt stylesheet and the Agent Web UI stylesheet SHALL be generated from that module. Style code SHALL reference semantic token names instead of ad-hoc literal values.

#### Scenario: Token-generated Qt stylesheet
- **WHEN** the application applies its global stylesheet
- **THEN** the stylesheet is rendered from the design token module for the current effective theme
- **AND** no panel-level widget style uses hardcoded border-gray literals from the five legacy gray values

#### Scenario: Token-generated web theme
- **WHEN** the Agent Web frontend is built
- **THEN** its CSS custom properties are generated from the same token definitions exported as JSON
- **AND** a missing or stale token export falls back to built-in light tokens without failing the build

#### Scenario: Single accent color
- **WHEN** either the Qt shell or the Agent Web UI renders an accent-colored control
- **THEN** both surfaces use the accent hue defined by the token module for the current theme
- **AND** the legacy web accent values `#3794ff` and `#006ab1` are no longer used

### Requirement: Light and dark themes

The application SHALL support `light`, `dark`, and `system` theme modes, persisted in QSettings, with `system` following the OS color scheme and reacting to OS theme changes without restart. Every surface — panels, viewport overlays, dialogs, status bar, and the Agent sidebar — SHALL render a complete token set in both themes meeting WCAG AA contrast for text.

#### Scenario: Switch theme at runtime
- **WHEN** the user switches the theme mode from the status bar control
- **THEN** the Qt shell, floating overlays, and dialogs restyle immediately
- **AND** the Agent sidebar, if visible, receives an updated theme event and restyles without reload
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

### Requirement: Unified icon language

All Qt toolbar, panel, and status bar icon buttons SHALL use vector SVG icons rendered and tinted through a shared icon module, matching the icon names and stroke style already used by the Agent Web UI. Unicode character icons SHALL not be used for controls.

#### Scenario: Icon tinting per theme
- **WHEN** the effective theme changes
- **THEN** Qt icon buttons re-render their SVG icons in the token icon colors for that theme
- **AND** the icons remain visually consistent with the lucide icons used in the Agent Web UI
