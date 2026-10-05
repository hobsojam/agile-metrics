# Feature Specification: Linear Team Lookup by Name or Key

**Feature Branch**: `008-linear-team-lookup`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "Let a user identify a Linear team by a human-readable value (the team's name, e.g. \"Engineering\", or its short key, e.g. \"ENG\") instead of requiring the raw Linear team UUID for --linear-team (CLI) and linear_team_id (web UI/API). The tool resolves the human-readable value to the team's actual id via a Linear API lookup before proceeding with the existing forecast flow - no change to what happens after resolution. If the given value doesn't match any team (by name or key) accessible to the API key, or matches more than one team, the user gets a clear, specific error naming the problem (no match found vs multiple teams match, listing the ambiguous candidates) rather than a generic \"team not found\". The raw team UUID must continue to work unchanged for any existing user/script relying on it - this is a strictly additive input format, not a replacement. No change to any other part of the Linear integration (periods, lookback window, error handling for auth/rate-limit/unavailable) and no change to the CSV or manual-paste data sources."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Forecast using a team's name or key instead of hunting for its ID (Priority: P1)

A user setting up a Linear-backed forecast knows their team as "Engineering" or by its
short key "ENG" — not by a UUID they'd have to separately look up via Linear's API or
settings. They type the name or key they already know, and the forecast works exactly as
if they'd supplied the raw ID.

**Why this priority**: This is the entire point of the feature — removing a lookup step
that currently blocks anyone who doesn't already have the team's raw ID handy, which is
every first-time user of Linear import (#179's own quickstart surfaced exactly this
friction).

**Independent Test**: Submit a Linear-backed forecast (CLI or web UI) using a team's exact
name or key instead of its UUID, and confirm the forecast renders identically to one
submitted with that team's actual ID.

**Acceptance Scenarios**:

1. **Given** a Linear workspace where the API key has access to a team named "Engineering"
   with key "ENG", **When** the user supplies `--linear-team Engineering` (or
   `--linear-team ENG`), **Then** the forecast is computed for that team, identical to
   supplying its raw ID.
2. **Given** the same setup, **When** the user supplies the value in different letter
   casing (e.g. `engineering` or `eng`), **Then** it still resolves to the same team.

---

### User Story 2 - Clear errors when a name or key doesn't resolve to exactly one team (Priority: P2)

A user mistypes a team name, or two teams in the workspace happen to share a name or key
pattern that makes their input ambiguous. They need to know immediately whether the
problem is "no such team" or "which of these did you mean," not a generic failure.

**Why this priority**: Without this, a resolution failure would be indistinguishable from
every other Linear error, defeating the clarity this integration otherwise already provides
(spec 006 US3) — but it only matters once lookup (US1) exists.

**Independent Test**: Submit a forecast with a team value that matches no team, then one
that matches two or more teams, and confirm each produces a distinct, specific message.

**Acceptance Scenarios**:

1. **Given** a value that doesn't match any team's name, key, or ID accessible to the API
   key, **When** the user submits the forecast, **Then** they see a message naming the
   value and stating no matching team was found — distinct from every other Linear error
   message.
2. **Given** a value that exactly matches the name or key of more than one team, **When**
   the user submits the forecast, **Then** they see a message naming the value and listing
   every matching team, so they can pick a more specific value (e.g. the team's ID).

---

### User Story 3 - Existing raw-ID usage keeps working unchanged (Priority: P3)

A user or automated script already supplying the raw Linear team ID (today's only option)
must see no change in behavior, output, or failure modes after this feature ships.

**Why this priority**: Protects existing users from a regression; lower priority only
because it's a non-regression guarantee rather than new value, and has no user-visible
difference to demo beyond "nothing changed."

**Independent Test**: Run the same raw-ID request before and after this feature, with a
real or mocked Linear team, and confirm byte-for-byte identical output.

**Acceptance Scenarios**:

1. **Given** a team's raw ID, **When** the user supplies it exactly as they do today,
   **Then** the forecast succeeds exactly as it did before this feature existed, with no
   additional lookup step changing the result, timing characteristics, or any error path.

---

### Edge Cases

- **Workspace with zero teams accessible to the API key**: any human-readable value
  produces the "no matching team" message (US2 Scenario 1) — not a different, special-cased
  error.
- **A name/key value that happens to be empty or whitespace-only**: treated as "no matching
  team" rather than silently resolving to an arbitrary team.
- **A workspace with more teams than fit in a single API page**: every accessible team is
  considered for matching — none silently excluded by pagination (mirrors spec 006's
  FR-009/FR-010 guarantee for issue fetching).
- **A human-readable value that happens to collide character-for-character with another
  team's raw ID**: not a realistic concern in practice (Linear's IDs and its human-readable
  names/keys are drawn from different, non-overlapping formats), so no special handling is
  required beyond normal exact matching.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to provide a team's human-readable name or short key in
  place of its raw ID, for both `--linear-team` (CLI) and `linear_team_id` (web UI/API).
- **FR-002**: A human-readable value MUST be resolved to the team's actual ID via a lookup
  against the teams accessible to the supplied API key, before the existing forecast flow
  proceeds unchanged — no other part of the Linear integration (period handling, lookback
  window, throughput fetching, forecast computation) is affected by this feature.
- **FR-003**: A raw team ID MUST continue to work exactly as it does today — this is a
  strictly additive input format, not a replacement, and MUST NOT change the outcome,
  timing characteristics, or error behavior of an already-working raw-ID request (User
  Story 3).
- **FR-004**: Matching a human-readable value against team names and keys MUST be
  case-insensitive.
- **FR-005**: Matching MUST be exact, not partial or substring — a value that isn't an
  exact (case-insensitive) match for any team's name or key does not resolve.
- **FR-006**: If a human-readable value matches no team, the system MUST surface a message
  naming the value and stating no match was found, distinct from every other error this
  integration can produce (spec 006 FR-007's precision standard, extended to this case).
- **FR-007**: If a human-readable value matches more than one team, the system MUST surface
  a message naming the value and listing every matching team, distinct from the "no match"
  case (US2).
- **FR-008**: Team lookup MUST consider every team accessible to the API key regardless of
  how many exist — no silent truncation due to pagination (mirrors spec 006 FR-009/FR-010).
- **FR-009**: The existing Linear-side error classifications (invalid/expired credential,
  rate limiting, API unavailability — spec 006 FR-007) MUST still apply to the lookup
  itself, using the same existing messages — no new, parallel error types for the same
  underlying failures.
- **FR-010**: The CSV and manual-paste data sources, and every other part of the Linear
  integration not explicitly covered above, remain unchanged.

### Key Entities

- **Team Identifier**: the value supplied for `--linear-team`/`linear_team_id` — either a
  raw Linear team ID (used exactly as today) or a human-readable name/key (resolved to a
  team ID via lookup before use). Not a new stored entity; a resolution step in front of
  the existing "Linear Team Selector" entity from spec 006.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who knows only their team's name or short key — not its ID — can get a
  complete Linear-backed forecast without looking up or copying a raw identifier from
  anywhere else first.
- **SC-002**: A user already supplying a raw team ID sees zero behavior change — same
  output, same timing characteristics, same error paths, for the same input.
- **SC-003**: An unresolved or ambiguous team value always produces a message specific
  enough to tell the user their next action (try a different value vs. pick among named
  candidates) — never a generic failure.
- **SC-004**: Lookup against a workspace with any number of teams never misses a team due
  to pagination.

## Assumptions

- **Exact matching, not fuzzy/partial**: a value must exactly (case-insensitively) match a
  team's full name or full key to resolve — no substring, prefix, or fuzzy matching. Keeps
  resolution predictable and avoids silently matching the wrong team from a partial guess;
  a future feature could add fuzzy matching if this proves too strict in practice.
  Case-insensitivity (FR-004) is the one concession to typing convenience, matching how
  most CLI tools treat human-typed identifiers.
- **Scope of "accessible to the API key"**: identical to the existing scope already
  established in spec 006 — whatever teams the key's owning account can see, no new
  permission model introduced.
- **No change to the 26-period default or any other existing Linear request
  parameter**: this feature is purely about how the team is identified, not how much
  history is fetched once it's resolved.
- **No persistence of resolved IDs**: each request resolves independently; nothing is
  cached or stored between requests, consistent with the integration's existing stateless,
  no-credential-persistence design (spec 006 FR-005).
