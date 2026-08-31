## ADDED Requirements

### Requirement: Host-synchronized theming

The Agent Web UI SHALL render with the theme provided by the host application and SHALL NOT follow the OS `prefers-color-scheme`. The host SHALL guarantee a correct first paint by loading the document with the effective theme as a URL parameter applied by a document-creation user script, and SHALL communicate runtime theme changes through a `theme_state` bridge event carrying only the effective mode. If no theme information is available, the Web UI SHALL render with built-in light tokens.

#### Scenario: Initial theme match
- **WHEN** the Agent document loads while the host is in dark mode
- **THEN** the document root carries `data-theme="dark"` before any stylesheet is evaluated, producing a correct first paint without a visible light-to-dark flash

#### Scenario: Theme change while loaded
- **WHEN** the host switches its effective theme while the sidebar document is loaded
- **THEN** the sidebar applies the new theme from the `theme_state` event without reloading the document or losing conversation state

#### Scenario: Theme change while hidden
- **WHEN** the host theme changes while the sidebar widget is hidden
- **THEN** the sidebar renders the new theme on its next open without an intermediate wrong-theme frame

#### Scenario: Mode fallback
- **WHEN** a `theme_state` event is missing, malformed, or carries an unknown mode value
- **THEN** the sidebar keeps its current theme and renders light when no theme has ever been applied, recovering when a valid event arrives

### Requirement: Theme-consistent sidebar surfaces

All Agent sidebar surfaces — conversation timeline, event cards, plan cards, composer, history, settings views, and the teaching case reader — SHALL use only semantic CSS custom properties from the token-generated theme, with text contrast meeting WCAG AA in both light and dark themes. Hardcoded literal colors SHALL not remain in sidebar stylesheets, and the native `color-scheme` property SHALL follow the applied theme so scrollbars and form controls match.

#### Scenario: Both themes pass contrast
- **WHEN** the sidebar renders in light or dark mode
- **THEN** body text, muted text, and status-colored event card accents meet the AA contrast threshold against their backgrounds

#### Scenario: No system theme following
- **WHEN** the OS color scheme differs from the host application theme
- **THEN** the sidebar still renders the host-provided theme

### Requirement: Resizable sidebar layout integrity

The Agent sidebar SHALL remain usable across its 360–560px width range: session tabs scroll horizontally, the composer controls do not overflow, model popovers stay within the sidebar bounds, and the conversation column keeps its maximum readable width centered. The existing narrow-width (≤359px) fallback rules SHALL remain for undersized rendering contexts.

#### Scenario: Narrow bound
- **WHEN** the user drags the sidebar to its 360px minimum
- **THEN** header actions, session tabs, composer toolbar, and send controls remain visible and functional

#### Scenario: Wide bound
- **WHEN** the user drags the sidebar to its 560px maximum
- **THEN** event cards do not stretch full width and the timeline stays centered with readable measure

### Requirement: Teaching case tabs

The sidebar tab strip SHALL support two tab kinds — conversation tabs and teaching case tabs — distinguished by a small leading icon on case tabs. Case tabs SHALL always show a close action; closing a case tab SHALL return activation to the current conversation tab. Case tabs are transient: they live only in the sidebar document memory, are rebuilt when the host re-publishes a `math_case` event, and are never persisted to the session store.

#### Scenario: Case tab identity
- **WHEN** both conversation tabs and case tabs are open
- **THEN** case tabs display a leading book icon so the user can tell teaching content from conversations at a glance
- **AND** the icon uses muted color, switching to the accent color when the case tab is active

#### Scenario: Receive a case
- **WHEN** the host publishes a `math_case` event
- **THEN** the sidebar upserts the case by id and activates its tab
- **AND** re-publishing the same case id reuses the existing tab

#### Scenario: Close a case tab
- **WHEN** the user closes the active case tab
- **THEN** the sidebar removes the case tab and reactivates the current conversation tab
- **AND** no conversation state is affected

#### Scenario: Case tabs survive conversation work
- **WHEN** a model turn is running in a conversation and the user opens or closes case tabs
- **THEN** the running turn and its streaming events are unaffected

### Requirement: Teaching case reader

The teaching case view SHALL present the case as a reading page: a category eyebrow, the case name as a document title, the summary, a centered KaTeX formula card, numbered steps rendered as Markdown, and a conclusion card. Reading cards SHALL follow the card visual spec (elevated background, medium radius, no default border), and document typography (reading title at 20px) is independent of panel chrome typography (15px).

#### Scenario: Reading layout
- **WHEN** a case tab is active
- **THEN** the case renders in a centered reading column with the eyebrow, title, summary, formula card, numbered steps, and conclusion card in reading order
- **AND** formulas render through KaTeX and steps render inline Markdown

#### Scenario: Card styling
- **WHEN** the formula card and conclusion card render in either theme
- **THEN** they use the elevated background with medium radius and no default border
- **AND** step markers use the accent color and steps keep comfortable reading line height

#### Scenario: Case pending before document load
- **WHEN** the host publishes a case before the sidebar document finishes loading
- **THEN** the case is delivered after load and opens without loss
