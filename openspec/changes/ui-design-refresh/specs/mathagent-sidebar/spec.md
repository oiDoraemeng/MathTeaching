## ADDED Requirements

### Requirement: Host-synchronized theming

The Agent Web UI SHALL render with the theme provided by the host application and SHALL NOT follow the OS `prefers-color-scheme`. The host SHALL send a `theme_state` event containing the effective mode and token values when the document finishes loading and whenever the effective theme changes. If no theme event has arrived, the Web UI SHALL render with built-in light tokens.

#### Scenario: Initial theme match
- **WHEN** the Agent sidebar opens while the host is in dark mode
- **THEN** the sidebar renders dark on first meaningful paint without a visible light-to-dark flash

#### Scenario: Theme change while visible
- **WHEN** the user switches the host theme while the sidebar is visible
- **THEN** the sidebar applies the new theme tokens without reloading the document or losing conversation state

#### Scenario: Theme change while hidden
- **WHEN** the host theme changes while the sidebar is hidden
- **THEN** the sidebar renders the new theme on its next open without an intermediate wrong-theme frame

#### Scenario: Token fallback
- **WHEN** a `theme_state` event is missing or malformed
- **THEN** the Web UI continues rendering with built-in light tokens and recovers when a valid event arrives

### Requirement: Theme-consistent sidebar surfaces

All Agent sidebar surfaces — conversation timeline, event cards, plan cards, composer, history, and settings views — SHALL use only semantic CSS custom properties from the token-generated theme, with text contrast meeting WCAG AA in both light and dark themes. Hardcoded literal colors SHALL not remain in sidebar stylesheets.

#### Scenario: Both themes pass contrast
- **WHEN** the sidebar renders in light or dark mode
- **THEN** body text, muted text, and status-colored event card accents meet the AA contrast threshold against their backgrounds

### Requirement: Resizable sidebar layout integrity

The Agent sidebar SHALL remain usable across its 360–560px width range: session tabs scroll horizontally, the composer controls do not overflow, model popovers stay within the sidebar bounds, and the conversation column keeps its maximum readable width centered. The existing narrow-width (≤359px) fallback rules SHALL remain for undersized rendering contexts.

#### Scenario: Narrow bound
- **WHEN** the user drags the sidebar to its 360px minimum
- **THEN** header actions, session tabs, composer toolbar, and send controls remain visible and functional

#### Scenario: Wide bound
- **WHEN** the user drags the sidebar to its 560px maximum
- **THEN** event cards do not stretch full width and the timeline stays centered with readable measure
