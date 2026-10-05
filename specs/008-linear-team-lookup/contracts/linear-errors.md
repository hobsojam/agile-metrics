# Contract Delta: Linear Error Messages

This document describes **only what changes** relative to
[specs/006-linear-integration/contracts/forecast-api.md](../../006-linear-integration/contracts/forecast-api.md).
No request/response shape changes at all (CLI flags, `ForecastRequestBody` fields,
`POST /api/forecast` behavior) — this feature only changes what the Linear-side error table
can produce for `--linear-team`/`linear_team_id`.

## `--linear-team` / `linear_team_id`: no shape change

Still a plain string. Still accepts a raw Linear team ID exactly as before. Now **also**
accepts a team's name or short key — resolved server-side before the existing flow runs.

## New error case

All still surfaced the same way every existing Linear error already is — 400 with
`{"error": "..."}` on the web, `Error: <message>` / exit code 1 on the CLI:

| Condition | Example message |
|---|---|
| Name/key value matches more than one team | `"Linear team 'Engineering' matches more than one team: Engineering (ENG), Engineering Support (ENGSUP) - use a more specific value or the team's ID"` |

## Unchanged error case, now reachable via a new path

| Condition | Message (unchanged from spec 006) |
|---|---|
| Raw ID doesn't exist, **or** name/key value matches zero teams | `"Linear team '<value>' was not found or is not accessible with this API key"` |

Before this feature, this message only ever meant "that raw ID doesn't exist." After, it
also covers "that name/key doesn't match any team" — the same message, now reachable from
a second input shape. No wording change; this row exists to make that explicit for anyone
matching on the message text.
