## Purpose

Persist MathAgent conversations and mathematical scene states locally so users can reopen sessions, restore any completed turn, undo a drawing, and continue from a historical state without losing the original branch.

## ADDED Requirements

### Requirement: Application-managed `.math` storage

The application SHALL create and manage a `.math` directory under the operating-system application-data directory. It SHALL store SQLite conversation data plus attachments, previews, and exports there; users SHALL NOT need to create a mathematical project.

#### Scenario: First launch storage
- **WHEN** the application starts for the first time
- **THEN** the application creates the `.math` directory and its required storage areas automatically

### Requirement: Durable session and turn records

The system SHALL store sessions, per-turn user and assistant messages, event records, selected mode, execution strategy, model, branch relationships, command plans, validation status, and execution status. Closing a tab SHALL mark it closed without deleting its records.

#### Scenario: Reopen database
- **WHEN** the application restarts after a completed turn
- **THEN** the session and its turn timeline can be loaded with the same execution metadata and messages

### Requirement: Versioned scene snapshots

Every turn that changes the scene SHALL store JSON-compatible `scene_before` and `scene_after` snapshots containing the 2D/3D mode, drawable geometry, layers, annotations, and required view state. Unsupported snapshot versions SHALL be rejected without partially applying them.

#### Scenario: Restore a turn
- **WHEN** the user restores a stored turn
- **THEN** the corresponding snapshot is applied through the existing scene refresh path and no model request is made

### Requirement: Startup recovery

The system SHALL persist the last open session IDs, active session ID, and the final scene snapshot. On startup it SHALL restore those sessions and the scene while keeping the MathAgent sidebar hidden.

#### Scenario: Recover after restart
- **WHEN** the application starts after the user closed it with open sessions
- **THEN** the previous tabs, active turn, and last scene are restored in the background and the panel remains hidden

### Requirement: Attachments and privacy

Accepted attachments SHALL be copied into `.math/attachments/`, while records SHALL contain only relative path, MIME type, byte size, hash, and timestamps. API keys SHALL NOT be written to the conversation database.

#### Scenario: Persist an attachment
- **WHEN** a valid image, PDF, or text attachment is sent
- **THEN** its metadata and copied path are recoverable from the turn without exposing credentials in the database
