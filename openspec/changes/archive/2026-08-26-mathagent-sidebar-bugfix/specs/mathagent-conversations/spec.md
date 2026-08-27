## MODIFIED Requirements

### Requirement: Durable session and turn records

The system SHALL store a nullable `hidden_at` timestamp for sessions in addition to existing closed/session metadata. Listing sessions for the sidebar SHALL exclude hidden sessions by default, while storage SHALL retain the session, turns, branch relationships, command plans, scene snapshots, and attachment metadata.

#### Scenario: Hide without deletion
- **WHEN** a user hides a session from the history view
- **THEN** the session is omitted from visible session and history queries
- **AND** reopening the local store preserves all records and snapshots for that session

#### Scenario: Rename a session
- **WHEN** a user saves a new title
- **THEN** the title is persisted on the existing session record without changing its turns or current scene

#### Scenario: Reopen database
- **WHEN** the application restarts after a completed turn
- **THEN** the session and its turn timeline can be loaded with the same execution metadata and messages

#### Scenario: Additive migration
- **WHEN** the application opens a database created before `hidden_at` existed
- **THEN** it adds the nullable column without deleting or rewriting existing sessions, turns, events, snapshots, or attachments
