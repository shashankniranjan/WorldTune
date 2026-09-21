# WorldTune Frontend + Backend Low-Level Design

**Status:** V2 implemented and locally validated  
**Scope:** Evidence-grounded World Shifts with optional bounded web research  
**Backend:** `/Users/shashankniranjan/IdeaProjects/WorldTune-BE`  
**Frontend:** `/Users/shashankniranjan/IdeaProjects/WorldTune-FE`

This is the single implementation reference for an AI agent that needs to understand,
validate, extend, or plan work on WorldTune. It describes the code that exists today, the
runtime flow, the data contract, the evidence boundary, and the rules for future changes.

## 1. Product boundary

WorldTune V2 is a personalized, evidence-grounded news context product. It is not a trading
system, hiring-market measurement system, causal inference system, or investment adviser.

The deterministic baseline uses:

1. Locally generated GDELT GKG-derived artifacts.
2. Publisher URLs already discovered in those GDELT records.
3. Optional metadata/image enrichment of those exact publisher URLs.

During a background refresh, optional bounded OpenRouter web search may add a small number of
URL-cited results for the exact shift. Those results are labelled `web-research`, cached, and
remain observed source records; all interpretations still require evidence IDs. The request
path never performs web search.

Every statement must retain its evidence class:

| Class | Meaning in V1 |
|---|---|
| `observed` | Present in a GDELT-derived record or measured artifact field. |
| `calculated` | Deterministically computed from observed records. |
| `inferred` | A bounded interpretation of observed/calculated evidence. |
| `associated` | Co-occurrence or repeated association; not causality. |
| `causal` | Disabled for V1 World Shifts. |
| `predictive` | Disabled for V1 World Shifts. |

AI may improve extraction and wording, but it cannot manufacture evidence, URLs, entities,
numbers, confidence, causal claims, market outcomes, career outcomes, or images.

## 2. Repository map

### Backend

| Path | Responsibility |
|---|---|
| `worldtune/backend/app/main.py` | FastAPI application factory, CORS, middleware, startup lifecycle. |
| `worldtune/backend/app/api/routes.py` | HTTP routes; validation, sanitization, response models, error mapping. |
| `worldtune/backend/app/schemas/world_shift.py` | Pydantic models for the frontend World Shift contract. |
| `worldtune/backend/app/services/world_shift_contract.py` | Loads immutable GDELT artifact and composes contract responses. |
| `worldtune/backend/app/services/world_shifts.py` | Legacy raw artifact adapter used by `/world/shifts...` compatibility routes. |
| `worldtune/backend/app/llm/explainer.py` | Existing optional OpenRouter-compatible explanation transport and fallback. |
| `data/processed/worldtune/world_shifts/gold_world_shifts.parquet` | Default World Shift artifact consumed by V1. |
| `worldtune/backend/tests/test_world_shift_contract.py` | Contract, snapshot, filter, and nullable-image regression tests. |

### Frontend

| Path | Responsibility |
|---|---|
| `src/api/worldShifts.ts` | HTTP adapter, mock/API switch, Zod parsing, snapshot mismatch check. |
| `src/schemas/worldShift.schema.ts` | Executable runtime response contract. |
| `src/types/worldShift.ts` | TypeScript compile-time contract. |
| `src/hooks/useWorldShifts.ts` | Fetches the snapshot list. |
| `src/hooks/useWorldShift.ts` | Fetches detail only after a list snapshot is available. |
| `src/app/world-shifts/[shiftId]/page.tsx` | Page orchestration, persona/tab state, loading/error states. |
| `src/components/renderers.tsx` | Overview, impact, persona, relationship, forecast, and evidence renderers. |
| `src/mocks/worldShifts.ts` | Explicit mock mode only. |
| `.env.example` | API runtime defaults. |

## 3. Runtime topology

```text
Browser :3000
    |
    | GET /world-shifts
    | GET /world-shifts/{id}?persona=tech&snapshotId=...
    | GET /world-shifts/{id}/relationships?... 
    | GET /world-shifts/{id}/evidence?...
    | GET/PUT /world-shifts/refresh-configuration
    v
FastAPI :8090
    |
    v
world_shift_contract.py
    |
    v
gold_world_shifts.parquet
```

Run the services locally:

```bash
# Backend
cd /Users/shashankniranjan/IdeaProjects/WorldTune-BE
PYTHONPATH=worldtune/backend .venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8090

# Frontend
cd /Users/shashankniranjan/IdeaProjects/WorldTune-FE
NEXT_PUBLIC_WORLDTUNE_DATA_SOURCE=api \
NEXT_PUBLIC_WORLDTUNE_API_URL=http://localhost:8090 \
pnpm dev
```

Useful URLs:

- Frontend: `http://localhost:3000`
- Example page: `http://localhost:3000/world-shifts/ai-infrastructure?persona=tech&tab=overview`
- Backend operator root: `http://localhost:8090/`
- Backend health: `http://localhost:8090/health`

The backend root is an operator status response, not a frontend page.

## 4. GDELT data pipeline

The artifact is built outside the request path by the local processing scripts. The conceptual
pipeline is:

```text
GDELT GKG files
  -> normalized Silver article records
  -> daily topic/entity/source metrics
  -> anomaly, momentum, persistence, diversity metrics
  -> signal evidence rows
  -> user-facing World Shift rows
  -> immutable Parquet snapshot
  -> FastAPI contract composer
  -> frontend Zod validation and renderers
```

The API does not scan raw GDELT history on every request. It loads the latest artifact, sorts by
date and signal strength, selects the latest observation date, and composes the UI response.

The default artifact is:

```text
/Users/shashankniranjan/IdeaProjects/WorldTune-BE/
data/processed/worldtune/world_shifts/gold_world_shifts.parquet
```

Tests may override it with `WORLD_TUNE_SHIFTS_PATH` and use CSV, JSON, or Parquet fixtures.

## 5. Backend contract implementation

### 5.1 Snapshot identity

`world_shift_contract.py` computes:

```text
snapshotId = YYYY-MM-DD + "-" + first 16 hex characters of SHA-256(artifact bytes)
```

`generatedAt` is the latest artifact date at `23:59:59Z`. `validUntil` is one day later.
These values are returned by every canonical response.

The loader cache key includes artifact path, modification time, and file size. The metadata
cache includes the same file identity and latest date. Replacing the artifact produces a new
snapshot ID.

### 5.2 Canonical routes

#### `GET /world-shifts?limit=20`

Returns the latest ranked list:

```json
{
  "snapshotId": "2026-09-19-cdb0f031afbb5db6",
  "generatedAt": "2026-09-19T23:59:59Z",
  "validUntil": "2026-09-20T23:59:59Z",
  "entries": [
    {
      "id": "crypto-regulation",
      "title": "Crypto Regulation",
      "rank": 1,
      "status": "surging",
      "direction": "up"
    }
  ]
}
```

The list is sorted by numeric `signal_strength` descending and limited to the latest artifact
date. `id` is a stable slug of the topic.

#### `GET /world-shifts/{shiftId}?persona=tech&snapshotId=...`

Returns a complete schema-versioned `WorldShiftSnapshot` containing:

- snapshot metadata;
- `persona` selected by the request;
- `shift` overview and related shifts;
- `content.impact` and `content.domain`;
- `relationships`; and
- `whatHappensNext`; and
- `evidence`.

The `persona` currently changes bounded explanatory text and is not a separate data source.

#### `GET /world-shifts/{shiftId}/relationships?persona=...&snapshotId=...`

Returns the same snapshot metadata plus the relationship graph. V2 distinguishes intra-shift
links, cross-shift links, and persona-specific paths. Every link includes mechanism wording,
confidence, temporal order, alternatives, and evidence IDs. Unsupported links remain explicit
empty states rather than invented causality.

#### `GET/PUT /world-shifts/refresh-configuration`

Reads or updates the persisted refresh interval and bounded web-research controls. Allowed
intervals are five minutes (`300`), one hour (`3600`), and twelve hours (`43200`). Five minutes
is the validation default. The scheduler re-reads the persisted value and the UI uses the same
value for query polling, so selecting twelve hours changes both layers without a redeploy.

#### `GET /world-shifts/{shiftId}/evidence?...`

Supports:

| Query | Behavior |
|---|---|
| `type` | Exact evidence type filter. |
| `source` | Case-insensitive source-domain filter. |
| `tag` | Tag membership filter. |
| `confidence` | `low`, `medium`, or `high`. |
| `limit` | 1–100 result limit. |
| `snapshotId` | Required for stable page pinning after the list request. |

### 5.3 Error behavior

| Condition | Status | Detail code |
|---|---:|---|
| Missing artifact | 503 | `SNAPSHOT_UNAVAILABLE` |
| Requested snapshot differs from current artifact | 409 | `SNAPSHOT_MISMATCH` |
| Unknown shift | 404 | `World Shift not found` |
| Invalid query bounds | 422 | FastAPI validation response |

### 5.4 Pydantic rules

`world_shift.py` uses camelCase aliases and `extra="forbid"`. This is deliberate: adding an
unknown field to a backend response should fail validation during development instead of being
silently ignored by the UI contract.

Important nullable fields:

- `Evidence.imageUrl` is `string | null` and is allowed to be absent or null.
- `Evidence.summary`, `Evidence.relationshipRole`, and several relationship/impact fields are
  optional.
- Empty relationship edges and empty persona groups are valid V1 states.

An absent article image is normal GDELT data, not an API failure.

## 6. Evidence and interpretation model

The composer intentionally uses conservative wording:

- article count and domain count are displayed as attention metrics;
- confidence is currently low for representative GDELT evidence;
- impact text says it is inferred and does not measure outcomes;
- risks describe syndication, selection, and media-attention limitations;
- watch items identify V2 evidence needed for validation.

The composer does not currently claim:

- verified causal relationships;
- actual technology adoption or career impact;
- market or holding performance;
- cross-dataset confirmation;
- strong causal confidence; or
- predictive/investment conclusions.

These are product safety boundaries, not missing UI fields to fill with invented text.

## 7. Frontend implementation

### 7.1 API adapter

`src/api/worldShifts.ts` is the only frontend module that knows the HTTP paths. It:

1. Selects API mode unless `NEXT_PUBLIC_WORLDTUNE_DATA_SOURCE=mock` is explicitly set.
2. Fetches raw JSON.
3. Parses every response with the matching Zod schema.
4. Adds `snapshotId` to detail, relationship, and evidence requests.
5. Rejects a detail response whose snapshot ID differs from the requested ID.

Do not call `fetch` directly from renderers or page components.

### 7.2 Query flow

```text
useWorldShifts()
    -> list response and snapshotId
    -> useWorldShift(shiftId, persona, snapshotId)
    -> render only when list snapshot is known
```

The detail query is disabled until `snapshotId` exists. This prevents a page from combining a
new list with a detail response from an older artifact.

Query keys include `snapshotId`, so React Query does not reuse a detail from a different
snapshot.

### 7.3 Page behavior

`src/app/world-shifts/[shiftId]/page.tsx` owns:

- route `shiftId`;
- persona selection;
- active tab;
- list loading and list errors;
- detail loading and detail errors;
- evidence focus IDs selected by clicking impact/domain/relationship items.

The page uses the list entry as a fallback title while detail data loads. It renders six
semantic tabs through `renderers.tsx`:

1. Overview
2. Tech/Market Impact
3. Your Lens
4. Relationships
5. What Happens Next
6. Evidence

### 7.4 Renderers

- `OverviewRenderer`: observed summary, why it matters, quick take, characteristics, themes.
- `ImpactRenderer`: direct chain, second-order effects, mechanisms, horizons, confidence,
  counter-evidence, invalidators, risks, opportunities, and watch items.
- `DomainRenderer`: evidence-linked persona implications; no unsupported personalized claim is
  substituted for missing data.
- `RelationshipRenderer`: React Flow graph plus cross-shift links and persona paths; observed
  and inferred semantics use different visual treatments.
- `ForecastRenderer`: base, upside, and downside conditional scenarios with triggers,
  indicators, invalidators, implications, evidence, and an explicit forecast boundary.
- `EvidenceRenderer`: evidence cards, filters by selected evidence IDs, source links, and
  optional images.

Evidence images use native `<img>` because publisher hosts are arbitrary and cannot be safely
enumerated in a Next image-host allowlist. `imageUrl=null` renders no image block.

## 8. Exact contract shape

The frontend executable contract is:

```text
SnapshotMeta
  snapshotId: string
  generatedAt: string
  validUntil: string

WorldShiftListResponse = SnapshotMeta + entries: WorldShiftListItem[]

WorldShiftSnapshot = SnapshotMeta +
  schemaVersion + persona + shift + content + relationships + whatHappensNext + evidence

RelationshipsResponse = SnapshotMeta + relationships
EvidenceResponse = SnapshotMeta + evidence
```

Every claim-like object carries `evidenceIds`. A renderer may show a claim only if its evidence
IDs are present in the same response. This is the primary UI traceability rule.

## 9. Request sequence for a stable page

```text
1. Browser loads /world-shifts/{id}
2. Frontend requests GET /world-shifts
3. Backend computes/returns snapshot metadata and ranked entries
4. Frontend stores snapshotId in the React Query key
5. Frontend requests GET /world-shifts/{id}?persona=tech&snapshotId=...
6. Backend validates snapshotId before composing detail
7. Frontend validates JSON using worldShiftSnapshotSchema
8. Tabs render only validated response data
9. Clicking a claim filters evidence by evidenceIds
```

If the artifact changes between steps 3 and 6, the backend returns 409. The UI should surface a
refresh action rather than silently mixing snapshots.

## 10. Validation and test commands

### Backend

```bash
cd /Users/shashankniranjan/IdeaProjects/WorldTune-BE
./.venv/bin/python -m pytest -q
```

The contract-focused tests cover list/detail consistency, evidence ID linkage, nullable image
URLs, stale snapshot rejection, and evidence filters.

### Frontend

```bash
cd /Users/shashankniranjan/IdeaProjects/WorldTune-FE
pnpm typecheck
pnpm lint
pnpm build
```

### Live smoke test

```bash
curl -fsS http://localhost:8090/health
curl -fsS http://localhost:8090/world-shifts
curl -fsS http://localhost:3000/world-shifts/crypto-regulation
```

Do not treat a successful build alone as proof that API data is wired. Verify at least one live
list response and one snapshot-pinned detail response.

## 11. AI/OpenRouter extension point

The existing transport is at `worldtune/backend/app/llm/explainer.py` and is configured by:

```text
OPENROUTER_API_KEY or LLM_API_KEY
OPENROUTER-compatible base URL
LLM_MODEL
```

World Shift refreshes use strict JSON OpenRouter stages and retain deterministic fallback.
Optional web research uses OpenRouter's server-side web-search tool with a bounded result and
character budget. Keep this boundary:

```text
GDELT evidence bundle
  -> strict extraction schema
  -> deterministic evidence/quality gates
  -> optional relationship and persona wording
  -> Pydantic contract model
  -> API
```

Required AI safeguards:

- send only bounded, cited GDELT evidence bundles;
- treat article text as untrusted input;
- require strict JSON and reject unknown keys;
- require evidence IDs for every generated claim;
- reject URLs/entities/numbers not present in the input bundle;
- cache by content digest, model, prompt version, and schema version;
- preserve deterministic fallback when OpenRouter is unavailable;
- never allow the model to set confidence or promote an association to causality.

## 12. Image pipeline plan

The contract already carries `imageUrl: string | null`. The current composer passes no image URL
unless the source artifact supplies one, so null is expected for many records.

The bounded V1 enrichment order is:

1. trusted image field from the GDELT-derived record;
2. JSON-LD `image` on the exact publisher URL;
3. Open Graph `og:image`;
4. Twitter card image;
5. no image.

Image retrieval must be bounded, cached, timeout-limited, and tied to the original GDELT URL.
Do not search unrelated images or invent a thumbnail. Preserve image URL failure as null.

## 13. Known limitations and deferred scope

Current limitations:

- GDELT GKG is metadata-oriented; it is not a complete article-text corpus.
- Topic matching and signal metrics are descriptive and may include irrelevant or syndicated
  coverage.
- Current evidence confidence is low and source quality is not independent verification.
- No jobs/developer-demand data exists in V1.
- No aligned BTC/ETH/gold/silver/HINDALCO or FX outcome series exists in this contract path.
- No causal, predictive, or investment conclusion is valid.
- Scenario outcome scoring requires a future observation at the stated horizon; until then each
  scenario remains open and the UI presents no fabricated accuracy score.

Next candidates:

1. publisher metadata/image enrichment;
2. GDELT claim/entity normalization and syndication clustering;
3. strict OpenRouter extraction and persona wording passes;
4. independent market, jobs, official, and technology datasets;
5. causal/predictive research only with point-in-time data, walk-forward validation, and explicit
   leakage checks.

## 14. AI change-planning checklist

Before changing this system, an AI agent should answer these questions:

1. Which repository and exact file owns the behavior?
2. Is the requested data GDELT-only V1 scope or a deferred V2 source?
3. Is the output observed, calculated, inferred, associated, causal, or predictive?
4. Which Pydantic and Zod schemas must change together?
5. Does the new field allow null/optional values in real source data?
6. Does every claim-like output retain evidence IDs?
7. Does the change preserve snapshot pinning and 409 mismatch behavior?
8. Does it preserve deterministic fallback when AI or external metadata retrieval fails?
9. What focused backend test, frontend typecheck, lint, build, and live smoke test prove it?
10. Does the change accidentally imply investment, career, causal, or predictive certainty?

Never silently widen the data-source boundary, remove evidence links, or make the frontend
accept unvalidated JSON.
