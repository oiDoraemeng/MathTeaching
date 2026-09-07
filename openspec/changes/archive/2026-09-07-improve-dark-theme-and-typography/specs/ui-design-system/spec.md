## MODIFIED Requirements

### Requirement: Light and dark themes

The application SHALL support `light`, `dark`, and `system` theme modes, persisted in QSettings, with `system` following the OS color scheme and reacting to OS theme changes without restart. Every surface — panels, viewport overlays, dialogs, status bar, the Agent sidebar, the math input webviews (formula list, formula editor popup, inline overlay, and preview), self-drawn widgets such as the lighting rotation card, and the native window title bar — SHALL render a complete token set in both themes meeting WCAG AA contrast for text.

#### Scenario: Switch theme at runtime
- **WHEN** the user switches the theme mode from the status bar control
- **THEN** the Qt shell, floating overlays, and dialogs restyle immediately
- **AND** the Agent sidebar, if loaded, receives a `theme_state` event carrying only the effective mode and restyles without reload
- **AND** the math input webviews restyle to the effective theme without reloading their documents
- **AND** the choice persists across application restarts

#### Scenario: OS theme change
- **WHEN** the OS color scheme changes while the theme mode is `system`
- **THEN** the effective theme is recomputed and applied to all surfaces without restart

#### Scenario: 3D canvas follows theme
- **WHEN** the effective theme changes and the user has not chosen an explicit scene background override
- **THEN** the 3D background and 2D grid colors switch to the theme-appropriate defaults

#### Scenario: Native title bar follows theme
- **WHEN** the effective theme changes to dark or light on a platform whose native window chrome supports a dark mode attribute
- **THEN** the main window title bar is switched to the matching dark or light appearance via the platform attribute in the same theme application step as the stylesheet
- **AND** platforms or window managers without such an attribute continue to theme every in-application surface without error

#### Scenario: Math input webviews follow theme
- **WHEN** the effective theme changes while the algebra panel is visible
- **THEN** the formula list, the formula editor popup, the inline formula overlay, and the formula preview render with the theme's token colors (backgrounds, hover, selection, borders, and MathLive selection highlights) without hardcoded light-only literals
- **AND** a math input webview opened after the theme switch renders the effective theme on first paint without an intermediate wrong-theme frame

#### Scenario: Lighting rotation widget follows theme
- **WHEN** the lighting dialog is open in the dark theme or the theme changes while it is open
- **THEN** the rotation widget card background, labels, and accent elements use the token colors of the effective theme instead of hardcoded light-only values

#### Scenario: Formula preview fallback readable in both themes
- **WHEN** the formula preview webview has not finished loading or fails to load in the dark theme
- **THEN** the fallback label text uses a token-driven color that remains readable against the dark panel background

#### Scenario: Long formula scrollable without scrollbar
- **WHEN** a formula exceeds the algebra panel width
- **THEN** the formula cell allows horizontal scrolling to reveal the full formula
- **AND** no visible horizontal scrollbar is rendered

### Requirement: Typography scale

The application SHALL set one application-wide font on `QApplication` using the token font family stack (Latin UI font plus Simplified Chinese fallbacks) with the body size expressed in pixels from the token scale (11/12/13/15), antialiased rendering preferred, and SHALL express all font sizes in pixels from the token scale. All chrome widget categories without an explicit token size — including tool buttons, menus, tooltips, combo box popups, and tree/list views — SHALL render at a token scale size rather than an inherited non-token size, and per-widget hardcoded font families and point-size overrides SHALL be removed.

#### Scenario: Consistent fonts
- **WHEN** the main window renders with default system font availability
- **THEN** all Qt labels, buttons, and inputs use the application font and a token font size
- **AND** no widget hardcodes a specific platform font family

#### Scenario: Pixel-accurate application font
- **WHEN** the application starts with the token body size of 12
- **THEN** the application font renders at 12 pixels (not 12 points) so widgets without an explicit stylesheet font size match token-styled labels
- **AND** Latin text uses the Latin UI font and Simplified Chinese text renders in the declared Chinese fallback family

#### Scenario: Unstyled controls fall back to token sizes
- **WHEN** a tool button, menu item, tooltip, combo popup item, or tree/list view item renders
- **THEN** its font size matches a token scale value (caption or body) instead of an inherited point-based application default

#### Scenario: Status bar uniform type size
- **WHEN** the status bar renders its mode label, tool label, render status, and Agent state segment together
- **THEN** every segment uses the same caption token size

#### Scenario: Document typography distinct from chrome
- **WHEN** a reading surface such as the teaching case reader renders its document title
- **THEN** it uses the 20px document-title style
- **AND** panel chrome titles elsewhere remain at the 15px token title size

#### Scenario: Web font stack parity
- **WHEN** the Agent Web UI or a math input webview renders mixed Latin and Chinese text
- **THEN** it uses a quoted font stack that applies the same Latin UI family and a declared Simplified Chinese fallback family

### Requirement: Unified icon language

All Qt toolbar, panel, and status bar icon buttons SHALL use vector SVG icons rendered and tinted through a shared icon module, matching the icon names and stroke style already used by the Agent Web UI. Unicode character icons and emoji SHALL not be used for controls. Icons on co-located controls SHALL be visually distinguishable: no two tool buttons in the same toolbar SHALL share the same icon glyph.

#### Scenario: Icon tinting per theme
- **WHEN** the effective theme changes
- **THEN** Qt icon buttons re-render their SVG icons in the token icon colors for that theme
- **AND** the icons remain visually consistent with the lucide icons used in the Agent Web UI

#### Scenario: High-DPI icon rendering
- **WHEN** icons render on a display with device pixel ratio greater than 1
- **THEN** the icon module renders at the physical resolution and icons appear sharp without a per-resolution asset set

#### Scenario: Distinct tool icons
- **WHEN** the 2D geometry toolbar renders its vector, ray, line-tool, straight-line, angle, and projection buttons
- **THEN** each button uses a distinct icon glyph so tools are distinguishable without reading tooltips

#### Scenario: Password visibility toggle
- **WHEN** the Agent settings API key field toggles visibility
- **THEN** the toggle shows a filled circle while the key is visible and a hollow circle while it is hidden, rendered through the shared icon module rather than an emoji

### Requirement: Depth, motion, and focus

The token system SHALL define two shadow levels (overlay, modal) and a motion scale (120/150/200ms with a shared ease-out curve). Floating chrome SHALL use shadow instead of heavy borders to express elevation, popovers and panels SHALL animate with the motion scale, and keyboard focus SHALL be indicated by a visible 2px accent focus ring implemented with Qt-supported style sheet pseudo-states so it actually renders. Web surfaces SHALL respect `prefers-reduced-motion` by disabling transitions.

#### Scenario: Elevation through shadow
- **WHEN** a floating toolbar or popover appears over the viewport
- **THEN** its elevation is expressed by the overlay or modal shadow token rather than a strong border

#### Scenario: Animated popover
- **WHEN** a floating panel opens or closes
- **THEN** it animates opacity and a small translation within the 150–200ms motion range using the shared ease-out curve

#### Scenario: Keyboard focus visible
- **WHEN** the user navigates controls with the keyboard
- **THEN** the focused control shows a 2px accent focus ring rendered by a Qt-supported pseudo-state in both themes
- **AND** the generated stylesheet contains no pseudo-states unsupported by Qt style sheets that would silently drop the rule

#### Scenario: Reduced motion on web
- **WHEN** the OS requests reduced motion
- **THEN** the Agent Web UI disables its transitions
