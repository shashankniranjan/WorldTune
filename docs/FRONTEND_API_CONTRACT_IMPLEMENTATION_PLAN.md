# WorldTune frontend API and intelligence implementation plan

## Goal

Build an evidence-grounded WorldTune backend in
`/Users/shashankniranjan/IdeaProjects/WorldTune-BE` that satisfies the executable frontend
contract in
`/Users/shashankniranjan/IdeaProjects/WorldTune-FE/src/schemas/worldShift.schema.ts`.

The implementation must do more than reshape the existing Parquet rows. It must improve the
underlying evidence, connect corroborated developments, produce useful persona-specific impact
analysis, and deliver clean API responses for every UI tab.

OpenRouter will be used for constrained extraction, normalization, synthesis, and explanation.
It must never manufacture a fact, price, causal relationship, confidence score, source, or image
to fill a required UI field. The canonical chain remains:

```text
raw source -> observed record -> deterministic metrics -> AI-enriched claims
-> corroboration and relationship checks -> persona impact -> API snapshot -> UI
```

## V1 source scope

V1 uses **GDELT only**. No GitHub, Hacker News, Stack Exchange, jobs, market-price, government,
or other external dataset is required or consulted to derive V1 World Shifts.

The source boundary includes:

- locally stored GDELT GKG records;
- the publisher URLs discovered through those GDELT records;
- bounded retrieval of metadata from those exact publisher pages for title, description,
  publication metadata, and article image discovery; and
- OpenRouter processing of the resulting GDELT evidence bundle.

Following a GDELT-discovered URL to obtain its article metadata is enrichment of that GDELT
record, not an independent confirmation source. V1 confirmation therefore means
**cross-publisher corroboration within GDELT**, never cross-dataset confirmation.

V2 will evaluate and add other source families. Their existing adapters may remain in the
repository, but the V1 World Shift pipeline must not read from them.

## Product boundary

WorldTune may help the user connect the dots, but it must preserve the distinction between:

- **Observed:** directly present in a source or measured series.
- **Calculated:** reproducible metrics computed from observed data.
- **AI extracted:** structured facts or claims extracted from supplied source content.
- **Inferred:** a plausible mechanism or impact connected to explicit evidence.
- **Associated:** signals that co-occur or move together without causal proof.
- **Causal:** used only when the source evidence and validation rules support the claim.
- **Predictive:** shown only after point-in-time evaluation demonstrates adequate performance.

The UI may render all of these, but the backend must not collapse them into one confidence label.

## Frontend contract

The canonical routes are:

| Route | Required response |
| --- | --- |
| `GET /world-shifts` | `{ snapshotId, generatedAt, validUntil, entries }` |
| `GET /world-shifts/{shiftId}?persona=...` | complete `WorldShiftSnapshot` |
| `GET /world-shifts/{shiftId}/relationships?persona=...` | snapshot metadata plus relationships |
| `GET /world-shifts/{shiftId}/evidence?persona=...` | snapshot metadata plus evidence |

The frontend Zod schema remains the executable delivery contract. Backend Pydantic models must
mirror it with camelCase aliases. The existing `/world/shifts...` routes remain temporary,
deprecated compatibility aliases during migration.

## Current data and gaps

### Reusable now

- 15-day full GDELT GKG extract and a one-file-per-day, one-year GDELT baseline.
- Silver article records, daily topic metrics, signal candidates, signal evidence, World Shift
  artifacts, and manifests.
- Deterministic anomaly, momentum, persistence, diversity, and signal-strength calculations.
- Persona metadata for technology, career, geography, crypto, gold, silver, and HINDALCO.
- Existing GDELT processing code plus the OpenRouter-compatible `LLMExplainer` transport and
  deterministic fallback.

### Must be improved

- The GKG field mapping currently produces unreliable titles, languages, source countries,
  organizations, and locations.
- Broad keyword detectors admit false positives.
- GDELT attention alone cannot establish real-world activity or causality.
- Current representative evidence lacks complete article metadata and images.
- Current technology and finance impact objects correctly report `not_supported`.
- No aligned market series or job/developer-demand dataset is in V1 scope.
- The current OpenRouter output contract is an explanation contract, not a full extraction,
  corroboration, or relationship contract.

## V1 capabilities and evidence limits

### 1. Relationships and connecting the dots

OpenRouter may propose connections among GDELT-derived event clusters, but deterministic gates
decide the label exposed to the UI.

V1 relationship levels are:

1. `co_occurs_with`: shared time window, entity, organization, location, or theme.
2. `associated_with`: the connection recurs across multiple independently published GDELT
   articles after syndicated duplicates are collapsed.
3. `plausibly_influences`: one or more GDELT-discovered articles explicitly describe a mechanism
   and the temporal ordering is valid.

V1 does not emit `causes`. Even when an article uses causal language, WorldTune records it as a
source-stated mechanism and exposes at most `plausibly_influences`. Causal verification requires
additional source families and is deferred to V2.

Every relationship edge stores evidence IDs, publisher diversity, time ordering, proposed
mechanism, counter-evidence, and the deterministic rule that admitted it. AI output alone cannot
promote an edge.

### 2. Technology and career impact

V1 derives possible technology/career implications from GDELT article evidence and the user's
skills, target roles, Bengaluru location, and European consulting context.

It may describe:

- technologies, companies, regulations, projects, and skills mentioned in coverage;
- plausible delivery, consulting, learning, or role implications;
- geographic and regulatory relevance; and
- what additional evidence would confirm the implication.

It must label these items as inferred or possible. It must not claim measured developer
adoption, hiring demand, salary movement, or skill-market growth because V1 has no developer or
jobs dataset.

### 3. Market and holding-specific impact

V1 uses GDELT evidence to build qualitative economic-mechanism maps for BTC, ETH, gold, silver,
HINDALCO, and INR/EUR/USD exposure. For example, a sourced event may be connected to regulation,
inflation, real-yield, currency, energy-cost, China-demand, or European-demand channels.

V1 may provide:

- asset or holding relevance;
- possible positive, negative, mixed, or uncertain mechanisms;
- near-, medium-, or longer-horizon narrative implications; and
- evidence-backed risks and watch items.

V1 must not claim an observed market reaction, price correlation, expected return, portfolio
return, trade direction, or profitability. Holdings remain context-only labels; quantities,
cost basis, and broker data are not stored.

### 4. Cross-publisher corroboration within GDELT

Confirmation is based on independent publishers present in GDELT, not external datasets and not
ten syndicated copies of one story. Track:

- publisher domain and inferred publisher family;
- canonical story and claim IDs;
- publication and GDELT observation timestamps;
- primary-source links mentioned in the coverage when available;
- agreement, contradiction, and unresolved status;
- unique-publisher and unique-story counts.

V1 corroboration status is `unconfirmed`, `single-publisher`, `multi-publisher`,
`publisher-corroborated`, or `contested`. The API and UI must call this publisher corroboration,
not cross-source confirmation. AI clusters semantically similar claims, while deterministic URL,
publisher, timestamp, and content-hash rules prevent syndicated copies from inflating it.

### 5. Confidence classifications

Confidence is calculated outside the LLM from GDELT-derived components:

- publisher quality prior and diversity;
- independent-story count after syndication deduplication;
- evidence completeness;
- entity/time/location agreement;
- freshness;
- contradiction penalty;
- detector precision history;
- GDELT coverage and missingness; and
- AI extraction agreement or review status.

The API's `low`, `medium`, and `high` values come from documented thresholds. The LLM may explain
the score but cannot set or override it. In V1, `high` may describe confidence that articles
support a reported claim; it must never imply externally verified causality, market effect, or
career outcome.

### 6. Predictive conclusions

Predictive conclusions are disabled in V1. The UI may show observed GDELT attention direction,
anomaly, momentum, and persistence, but never predicted market, holding, hiring, or career
direction.

Prediction research requiring aligned outcome data, chronological training, walk-forward
evaluation, prefix tests, baselines, calibration, and stability analysis is deferred to V2 or
later. V1 uses `uncertain` or an explicit no-prediction explanation wherever the UI might
otherwise imply a forecast.

## AI enrichment architecture

### Reuse of the existing OpenRouter implementation

Reuse its configuration and resilient transport:

- `OPENROUTER_API_KEY` / `LLM_API_KEY` alias handling.
- OpenAI-compatible base URL and model selection.
- timeout, malformed-response handling, and deterministic fallback.
- no credential logging or persistence.

Do not overload the current five-field `Explanation` model. Add task-specific interfaces and
strict response schemas:

- `ArticleMetadataExtraction`
- `ClaimExtraction`
- `EntityNormalization`
- `EventClusterSummary`
- `RelationshipCandidate`
- `PersonaImpactExplanation`
- `ContradictionReview`

### Enrichment passes

1. **Document pass:** extract title, concise summary, event time, claims, entities, locations,
   organizations, topics, and image candidates from one source document.
2. **Claim normalization:** map equivalent names and claims to deterministic canonical IDs.
3. **Cluster pass:** group duplicate/syndicated coverage and summarize only supplied records.
4. **Corroboration pass:** compare independent GDELT publishers and record agreement or conflict.
5. **Relationship pass:** propose typed edges with mechanism, temporal order, supporting and
   opposing evidence IDs.
6. **Persona pass:** translate the validated cluster into technology/career or finance/holding
   implications, using only the validated evidence bundle and deterministic metrics.
7. **Presentation pass:** generate concise text for UI fields without changing the underlying
   scores, labels, or evidence links.

### AI safety and reproducibility

- Treat article content as untrusted input and isolate it from system instructions.
- Require strict JSON; reject unknown keys and invalid enum values.
- Require evidence IDs for every extracted claim, relationship, and impact item.
- Reject invented URLs, entities not present in evidence, unsupported numbers, and timestamps
  outside the source coverage.
- Cache by source-content digest, model, prompt version, and schema version.
- Store generation metadata, validation result, and fallback reason.
- Use bounded batches, concurrency, retries, token budgets, and resumable checkpoints.
- Send representative evidence, not the complete GDELT history, to OpenRouter.
- Preserve the original observed record; AI output is a separate derived layer.
- Permit deterministic fallback and partial snapshots when OpenRouter is unavailable.

## News image pipeline

The frontend contract already supports optional `evidence.imageUrl`; no contract-breaking field
is required.

### Image discovery order

1. Image URL explicitly supplied by a trusted source feed.
2. Schema.org/JSON-LD `image` from the canonical article page.
3. Open Graph `og:image`.
4. Twitter/X card image metadata.
5. Publisher/site image only when it is article-specific.
6. Category placeholder when no valid article image exists.

Do not generate synthetic news photographs. A generated image could be mistaken for observed
evidence. Missing images should use a clearly generic WorldTune category visual or no image.

### Image validation

- Fetch article metadata with bounded timeout, redirects, response size, and per-domain pacing.
- Respect provider terms, robots policy, and image licensing/attribution requirements.
- Require HTTPS in API output where possible.
- Validate `Content-Type`, byte signature, minimum dimensions/aspect ratio, and maximum size.
- Reject tracking pixels, icons, favicons, data URLs, SVG/script payloads, and broken/expired
  links.
- Block loopback, private, link-local, and cloud-metadata destinations to prevent SSRF.
- Record canonical source URL, discovered image URL, discovery method, validation time, hash,
  dimensions, attribution, and cache policy.
- Cache/proxy an image only when permitted. Otherwise return the validated publisher URL and a
  fallback for load failure.
- Deduplicate images by perceptual/content hash so syndicated cards do not appear unique.

### Frontend image work

- Render an optional thumbnail/hero in `EvidenceRenderer` with the article title as alt text.
- Configure permitted remote image hosts dynamically or serve validated images through a
  controlled backend media route.
- Preserve layout when an image is missing or fails.
- Lazy-load images, constrain aspect ratio, and avoid making image success a page-load blocker.
- Keep source, time, confidence, and link visible; the image is supporting presentation, not
  evidence by itself.

## Snapshot and API design

### Immutable bundle

Publish each completed run as a versioned bundle containing:

- observed and enriched evidence;
- event/shift clusters;
- deterministic metrics and confidence components;
- relationships and persona impacts;
- image metadata;
- validation results and limitations;
- a manifest containing content hashes, schema/prompt/model versions, source coverage,
  `snapshotId`, `generatedAt`, and `validUntil`.

Derive `snapshotId` from effective UTC coverage plus a content digest, not request time. Publish
to a temporary directory, validate, then atomically switch the latest pointer. Retain prior
bundles long enough for pinned page loads.

### Stable IDs

- Use a date-independent public topic/event slug for `shift.id`.
- Retain date-specific analytical IDs internally.
- Generate deterministic evidence, claim, cluster, impact, node, and edge IDs.
- Every `evidenceIds` and `supports` reference must resolve inside the same snapshot.

### Snapshot pinning

The list response establishes the page's snapshot. Detail, relationship, and evidence requests
accept an optional `snapshotId`; the frontend passes it and rejects mismatches. Return a
structured 409 when a requested snapshot is unavailable instead of silently mixing runs.

## Contract field mapping

| Frontend field | Backend source or rule |
| --- | --- |
| `snapshotId` | snapshot manifest coverage + content digest |
| `generatedAt`, `validUntil` | immutable manifest, ISO-8601 UTC |
| `shift.id` | stable event/topic slug |
| `shift.title` | validated cluster title; deterministic fallback if AI unavailable |
| `shift.summary` | cited cluster summary, stripped of unsupported claims |
| `shift.signalStrength` | deterministic 0-1 score scaled and clamped to 0-100 |
| `shift.updatedAt` | latest included observation time, never request time |
| `shift.status` | documented mapping from anomaly, momentum, and persistence |
| `shift.direction` | observed attention/metric direction; never silently a price prediction |
| `overview` | observed cluster summary plus deterministic characteristics/themes |
| `relatedShifts` | same-snapshot stable IDs ranked by validated relationship/relevance score |
| `content.impact` | AI-narrated but evidence-constrained persona impacts |
| `content.domain.groups` | GDELT-supported entities and explicitly inferred persona implications |
| `relationships` | typed, evidence-linked association/mechanism edges |
| `evidence` | observed records with source, time, URL, optional image, entities, tags, confidence, and supports |

Unsupported sections remain valid empty arrays with an explicit summary. Required strings must
describe the limitation rather than invent content.

## Implementation sequence

### Phase 0 - repository and contract hygiene

- Use `/Users/shashankniranjan/IdeaProjects/WorldTune-BE` as the backend path.
- Preserve all existing uncommitted retrieval and World Shift work.
- Decide separately whether to rename the GitHub repository/remote.
- Fix the frontend ESLint 9 flat configuration.
- Add backend Pydantic models and frontend wrapper Zod schemas.
- Add a cross-repository command that validates live backend JSON with the actual frontend Zod
  schemas.

### Phase 1 - repair canonical GDELT parsing

- Reparse raw GKG using the official field layout instead of trying to repair malformed
  location/organization tokens downstream.
- Validate titles, language, source country, people, organizations, locations, themes, tone,
  publication time, and normalized URL on reviewed fixtures.
- Rebuild Silver/Gold artifacts deterministically and publish before/after validation metrics.
- Tighten broad detectors with word boundaries, negative cases, and reviewed precision samples.

Exit gate: no known numeric garbage locations and no known detector fixture failures.

### Phase 2 - article metadata, content, and image enrichment

- Build a bounded, resumable article metadata fetcher for representative candidate URLs.
- Capture canonical URL, title, description, JSON-LD, Open Graph, image candidates, publication
  time, publisher, language, and retrieval status.
- Validate and persist image metadata using the image rules above.
- Retain only content permitted by source terms; store hashes and provenance even when full text
  cannot be retained.
- Add per-domain pacing, retry/backoff, failure classification, and manifests.

Exit gate: representative evidence has valid title/time/source and either a validated image or
an explicit no-image reason.

### Phase 3 - structured OpenRouter enrichment

- Refactor the existing transport into reusable OpenRouter client infrastructure while keeping
  `LLMExplainer` backward compatible.
- Implement the task-specific strict schemas and prompts.
- Run extraction only on bounded representative evidence.
- Validate every output against source-bound entities, evidence IDs, timestamps, numbers, and
  URLs.
- Persist accepted/rejected status and deterministic fallback output.
- Build a reviewed golden set and measure extraction precision before bulk execution.

Exit gate: no accepted AI record lacks resolvable evidence, provenance, model/prompt version,
and validation status.

### Phase 4 - GDELT publisher corroboration

- Add publisher-domain and publisher-family classification to GDELT evidence.
- Deduplicate syndicated stories and normalize claims/entities across GDELT records.
- Compute publisher agreement, disagreement, independence, and evidence completeness.
- Record GDELT coverage gaps and article-fetch failures in snapshot limitations.
- Do not invoke or read any non-GDELT source adapter in the V1 World Shift build.

Exit gate: a `publisher-corroborated` label requires multiple independent publishers and passes
the documented rule; otherwise it remains unconfirmed, single-publisher, or associated.

### Phase 5 - relationship graph and causal-language gate

- Generate candidate edges from shared claims, entities, times, quantitative co-movement, and
  explicit source mechanisms.
- Use OpenRouter to explain candidate mechanisms and surface counter-evidence.
- Apply deterministic relationship-level gates after AI output.
- Store supporting and opposing evidence IDs and never emit orphan nodes or edges.
- Add review fixtures for association-versus-causation language.

Exit gate: future data cannot alter a published graph, and no edge is promoted by AI alone.

### Phase 6 - GDELT-derived persona impact

- Calculate persona relevance from validated GDELT topics, claims, entities, locations,
  organizations, and source-stated mechanisms.
- Build possible technology/career implications without claiming measured hiring or developer
  demand.
- Build qualitative finance/holding mechanism maps without claiming price movement,
  correlation, returns, or a trade direction.
- Use OpenRouter to narrate the validated GDELT evidence for `tech` and `finance`.
- Preserve context-only holdings, inference labels, evidence links, and explicit uncertainty.

Exit gate: every impact card links to GDELT evidence and its wording cannot masquerade as jobs,
developer-activity, market-price, or externally verified evidence.

### Phase 7 - GDELT confidence and no-prediction gate

- Implement transparent publisher/evidence confidence components and thresholds.
- Calibrate thresholds against the reviewed GDELT golden set before enabling `high`.
- Cap confidence according to claim type; inferred career/market effects cannot inherit high
  confidence from article-volume strength.
- Keep predictive output disabled and publish an explicit no-prediction limitation.
- Test that attention direction is never presented as predicted price or career direction.

Exit gate: V1 contains no predictive wording, and every confidence value is reproducible from
stored GDELT-derived components.

### Phase 8 - immutable snapshot composer

- Extend the pipeline to emit stable slugs, deterministic IDs, complete evidence, relationships,
  impacts, images, confidence components, and the manifest.
- Add integrity checks for duplicate IDs, unresolved references, invalid URLs/images, future
  observations, contradictory enum values, out-of-range scores, and missing limitations.
- Cache immutable bundles by ID instead of reading the whole Parquet dataset per request.

### Phase 9 - implement the backend API

- Implement the four canonical `/world-shifts...` endpoints.
- Support evidence filters `type`, `source`, `tag`, `confidence`, and bounded `limit`.
- Return 404 for unknown shifts, 409 for snapshot mismatch/unavailability, and 422 for invalid
  filters.
- Make CORS origins configurable.
- Expose source freshness and snapshot/schema versions in diagnostics without leaking secrets.

### Phase 10 - wire the frontend

- Validate list, detail, relationship, and evidence wrappers with Zod.
- Load the list first and pin subsequent calls to its `snapshotId`.
- Redirect `/` to the first returned shift instead of a mock-only slug.
- Render evidence images with lazy loading and graceful fallback.
- Preserve explicit observed/inferred labels and unsupported states.
- Keep mock mode available for component development; use API mode for integration tests.

### Phase 11 - validation and rollout

- Backend unit/API tests, full existing suite, schema fixtures, invariant tests, snapshot prefix
  tests, AI rejection/fallback tests, image security tests, and source-degradation tests.
- Frontend typecheck, repaired lint, production build, Zod contract tests, and browser tests for
  five tabs, two personas, image/no-image, empty/contested, and stale-snapshot states.
- End-to-end mock-disabled run against a published snapshot.
- Performance test cold/warm routes and confirm bounded memory/CPU use.
- Document exact source coverage, timestamps, model/prompt versions, costs, limitations, and
  unsupported conclusions for every published snapshot.

## Acceptance criteria

- All canonical endpoints pass the frontend's actual Zod schemas.
- A page load uses one immutable snapshot and detects mismatches.
- Every observed, AI-extracted, calculated, inferred, and associated item is distinguishable
  through stored provenance and API wording.
- Every claim, impact, entity, relationship, and confidence explanation resolves to evidence.
- OpenRouter failure cannot prevent snapshot/API availability and cannot corrupt canonical data.
- Publisher corroboration excludes syndicated duplicates, records disagreements, and is never
  labeled cross-source confirmation.
- V1 emits no verified-causality claim; OpenRouter may only propose source-linked mechanisms.
- Career and holding impacts are explicitly possible/inferred GDELT interpretations, not measured
  jobs, developer, market-price, portfolio, or outcome evidence.
- Predictive conclusions are disabled throughout V1.
- Every returned `imageUrl` is discovered from a source, validated, safe to fetch, and has a
  graceful UI fallback; no synthetic news image is represented as evidence.
- Existing backend tests remain green and all new contract, AI, image, causality, and integration
  tests pass.
- Frontend typecheck, lint, build, and mock-disabled browser tests pass.

## Current verified baseline (20 September 2026)

- Backend full suite: 273 passed, 3 deprecation warnings.
- Existing `/health` and `/world/shifts` routes: HTTP 200.
- Frontend TypeScript check and production build: passed.
- Frontend standalone lint: blocked because ESLint 9 cannot find a flat configuration file.
- Latest short-window World Shift artifact: 8 rows for 19 September 2026.
- Existing GDELT-derived entity/location fields and topic precision are not yet suitable for
  unqualified display.
- Existing OpenRouter-compatible explainer is reusable, but live OpenRouter execution has not
  yet been verified in the supported backend environment.

## Deferred to V2

V2 will separately evaluate additional source families such as developer platforms, community
signals, job postings, official statistics, market prices, FX, and company/commodity data. V2
may upgrade publisher corroboration to true cross-source confirmation and may validate measured
technology/career or market/holding effects.

No V1 contract or storage decision should prevent those additions, but V1 implementation,
confidence, relationships, persona impacts, images, and UI responses are derived from GDELT and
GDELT-discovered publisher metadata only.
