# Research: Linear Team Lookup by Name or Key

## 1. Detecting whether a value is a raw Linear ID

**Decision**: A simple UUID-shape regex:
`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`. A value
matching this pattern is treated as a raw ID and sent straight through today's unmodified
`_validate_team` path (even if it turns out not to correspond to a real team — that still
raises the *existing* `LinearTeamNotFoundError`, unchanged). A value that doesn't match
skips the direct lookup entirely and goes to team-listing + name/key matching instead.

**Rationale**: confirmed decision (plan.md "Decisions confirmed" §1) — avoids a wasted
round-trip for values that obviously aren't IDs, with no behavior change for the
already-working raw-ID case (spec FR-003/US3), since that code path doesn't even know this
feature exists.

**Alternatives considered**: Always attempt the direct lookup first, fall back to name/key
search on "not found" — rejected in favor of up-front detection (see plan.md).

## 2. Team-listing query shape

**Decision**: Mirror `_fetch_all_completed_at`'s exact pagination pattern (006 research.md
§2), against the root `teams` field instead of `issues`:

```graphql
query($after: String) {
  teams(first: 100, after: $after) {
    nodes { id name key }
    pageInfo { hasNextPage endCursor }
  }
}
```

Loop until `hasNextPage` is `false`, concatenating every page's `nodes` (spec FR-008 — no
silent truncation), exactly like the existing issues-fetch loop.

**Rationale**: Linear's GraphQL API is consistently Relay-style pagination across every
list-returning root field already confirmed in this project (`issues`) — the `teams` root
field is documented in Linear's public API reference with the identical
`nodes`/`pageInfo { hasNextPage endCursor }` shape, and `Team.key` is the same short
code (e.g. `ENG`) visible throughout Linear's own UI and issue identifiers (`ENG-123`).
**Not yet independently re-confirmed via live introspection in this session** — unlike
006's original queries and the `$teamId: String!` fix, which were caught by *actually*
exercising the live API. quickstart.md's manual scenario for this feature exists
specifically to close that gap before merge, the same lesson this feature's own motivating
bug (the `ID!`/`String!` mismatch) just taught.

**Alternatives considered**: A server-side filtered query (e.g.
`teams(filter: { or: [{name: {eqIgnoreCase: $value}}, {key: {eqIgnoreCase: $value}}] })`)
instead of fetching all teams and matching client-side — would save bandwidth for large
workspaces, but requires confirming Linear's `TeamFilter` supports `eqIgnoreCase` and an
`or` combinator (unconfirmed, more schema surface to get wrong); rejected for this version
in favor of the already-proven-correct pagination pattern. Worth revisiting if team counts
in practice turn out large enough for the fetch-everything approach to matter.

## 3. Matching and error classification

**Decision**:

- Matching is case-insensitive exact comparison against each team's `name` and `key`
  (spec FR-004/FR-005) — `value.casefold() in {team.name.casefold(), team.key.casefold()}`.
- **Zero matches**: reuse the *existing* `LinearTeamNotFoundError(value)` — its message
  ("Linear team '{value}' was not found or is not accessible with this API key") already
  satisfies spec FR-006 without a new exception type or duplicated message text, matching
  this project's established "don't duplicate an error that already says the right thing"
  precedent (006 research.md §3, CSV research.md §4).
- **More than one match**: a new `LinearTeamAmbiguousError(value, candidates)`, message
  listing every candidate as `"name (key)"` — e.g. `"Linear team 'Engineering' matches
  more than one team: Engineering (ENG), Engineering Support (ENGSUP) - use a more specific
  value or the team's ID"`.
- **Exactly one match**: resolve to that team's `id`, then proceed through the *existing*
  `_validate_team`/fetch flow exactly as a raw ID would (re-validating the now-resolved ID
  is harmless — one extra call for the name/key path only, not the common raw-ID path).

**Rationale**: `LinearTeamAmbiguousError` is the only genuinely new exception this feature
needs — every other outcome (no match, success) reuses existing code paths/messages
unchanged, directly satisfying Principle V.

## 4. Ambiguous-match message format

**Decision**: `"name (key)"` per candidate, comma-separated.

**Rationale**: confirmed in plan.md — this is the one format that directly tells the user
a more specific value (the key) they could retry with, not just a list of names they'd
still have to cross-reference themselves.
