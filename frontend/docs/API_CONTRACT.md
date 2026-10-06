# WorldShiftSnapshot API contract

This repository consumes immutable daily snapshots. All endpoints must return the same `snapshotId` for a page load; a client will reject a response from a different snapshot.

| Endpoint | Response |
| --- | --- |
| `GET /world-shifts` | `{ snapshotId, generatedAt, validUntil, entries: WorldShiftListItem[] }` |
| `GET /world-shifts/:shiftId?persona=:persona` | `WorldShiftSnapshot` |
| `GET /world-shifts/:shiftId/relationships?persona=:persona` | `{ snapshotId, relationships }` |
| `GET /world-shifts/:shiftId/evidence?persona=:persona&...filters` | `{ snapshotId, evidence }` |
| `GET /world-shifts/refresh-configuration` | Persisted scheduler and web-research settings |
| `PUT /world-shifts/refresh-configuration` | Updated scheduler and web-research settings |

`WorldShiftSnapshot` schema version 2 separates `observed` evidence from `inferred`
relationships, impacts, and conditional scenarios, plus `personalized` persona content.
Inferred records must provide `evidenceIds`; the UI uses those IDs for reverse navigation.

The six tabs are Overview, Tech/Market Impact, Your Lens, Relationships, What Happens Next,
and Evidence. Forecast scenarios are conditional possibilities with triggers, indicators,
invalidators, confidence, and limitations; they are not predictions of certainty.

Refresh intervals are restricted to `300`, `3600`, or `43200` seconds. The runtime default is
`300` seconds for testing; choosing 12 hours in the UI persists `43200` for the scheduler.

The exact Zod validation schema is the executable source of truth: `src/schemas/worldShift.schema.ts`.
