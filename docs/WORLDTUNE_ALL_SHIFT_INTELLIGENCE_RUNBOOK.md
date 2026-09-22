# WorldTune All-Shift Intelligence Runbook

## Purpose

This document tells an implementation model how to extend WorldTune correctly and efficiently so **every World Shift** has the same depth and readability as **Armed Conflict and Military Escalation**.

The product is a news and world-intelligence briefing, not a GDELT dashboard. GDELT and web research are evidence inputs. They must not become the story shown to the reader.

The reader should finish a World Shift knowing:

1. What the story is.
2. How the currently observed story began.
3. What happened in chronological order.
4. What is happening now.
5. Which countries, institutions, people, and companies are involved.
6. Which facts are confirmed, reported, claimed, or disputed.
7. Why the development matters.
8. What is driving it and what remains uncertain.
9. How a Finance & Investing reader should interpret it.
10. How a Tech & Career reader should interpret it.
11. What could happen next, with conditional scenarios rather than certain predictions.
12. Which source supports each important statement.

## Repositories and runtime

- Backend: `/Users/shashankniranjan/IdeaProjects/WorldTune-BE`
- Frontend: `/Users/shashankniranjan/IdeaProjects/WorldTune-FE`
- Backend API: `http://127.0.0.1:8090`
- Frontend: `http://127.0.0.1:3000`
- Backend virtual environment: `WorldTune-BE/.venv`
- Backend database when started from the backend repository root: `WorldTune-BE/worldtune.db`

Always confirm the process working directory before inspecting SQLite. A process started from another directory can resolve `sqlite:///./worldtune.db` to a different file.

## Non-negotiable product rules

### One shared story, two genuinely different interpretations

Generate one evidence-grounded semantic layer and one persona-neutral briefing for each shift. Derive both personas from that same semantic layer.

Do not generate two different versions of the underlying news.

- **Finance & Investing** explains company and sector exposure, earnings and cost mechanisms, order flow, commodities, policy, valuation sensitivity, direct versus indirect impact, India versus global exposure, and near-term versus long-term effects.
- **Tech & Career** explains technical problems, capability gaps, engineering opportunities, affected technology companies, possible advancements, India versus global relevance, and near-term versus long-term effects.

### Never invent completeness

If evidence does not establish the origin of a story, say:

> The available evidence begins on [date] with [event]. This is the beginning of the evidence window, not necessarily the origin of the wider issue.

Use an explicit empty or insufficient-evidence state instead of inventing actors, numbers, causal links, company contracts, market outcomes, or hiring demand.

### Keep observation and reasoning visually and structurally separate

- `observed`: directly supported by supplied evidence.
- `calculated`: deterministically computed from supplied inputs.
- `inferred`: a bounded interpretation grounded in evidence.
- `associated`: a relationship without established causality.
- `reasoned`: an explicit world-knowledge reasoning chain used for company or technology exposure.

A `reasoned` item is never presented as observed fact or investment advice.

## Required output for every World Shift

### Overview

Every shift must provide:

- `contextBrief.whatItIs`
- `contextBrief.howItStarted`
- `contextBrief.latest`
- dedicated evidence IDs for all three context paragraphs
- a dated `timeline`
- attributed `actors`
- source-supported `factsAndFigures`
- `whatsHappening`
- `whyItMattersPoints`
- `keyDevelopments`
- `drivers`
- `contradictions`
- `watchNext`

The timeline and actor wording must distinguish `confirmed`, `reported`, `claimed`, and `disputed` material.

### Finance & Investing

For each meaningful exposure, provide:

- specific public company name and ticker where known
- direction: positive, negative, or mixed sensitivity
- exposure ring: direct, supply chain, or second order
- mechanism: the business reason it could be affected
- a step-by-step reasoning chain
- grounded `derivedFrom` event, claim, or entity IDs
- countries
- near-term and/or long-term horizon
- confidence
- what the reader should verify next

Include India-specific companies only when a defensible path exists. Do not force an India company into every shift.

Never say a share **will** rise or fall. Say what could create positive, negative, or mixed sensitivity and what evidence would confirm it.

### Tech & Career

For each meaningful opportunity or risk, provide:

- specific global or Indian company where relevant
- the technical capability gap
- the possible technical advancement or implementation opportunity
- direct, enabling, or longer-term platform relationship
- a step-by-step reasoning chain
- grounded `derivedFrom` event, claim, or entity IDs
- countries
- near-term and/or long-term horizon
- confidence
- what the reader should verify next

A company capability is not proof that it has received a contract. Do not claim measured hiring demand without jobs evidence.

### Relationships

Relationships should explain a mechanism, not merely show nodes that share a country or keyword.

Each relationship needs:

- source and target
- relationship type
- plain-language explanation
- observed versus inferred classification
- evidence IDs
- confidence
- temporal order where available
- alternative explanation or counter-evidence where relevant

### What Happens Next

Generate bounded base, upside, and downside scenarios. Each scenario needs:

- horizon
- triggers
- leading indicators
- invalidators
- possible implications
- evidence IDs
- confidence

These are conditional scenarios, not forecasts of certainty.

### Evidence

Evidence cards should preserve:

- original headline
- publisher and source domain
- publication time
- URL
- source snippet or AI summary
- image when publisher metadata provides one
- source class
- retrieval status
- corroboration status
- event, claim, and entity links

Never invent a URL, source, headline, date, image, or quotation.

## Backend implementation map

The main files are:

- `worldtune/backend/app/schemas/world_shift.py`
  - Frozen API contract and Pydantic validation.
- `worldtune/backend/app/services/world_shift_ai.py`
  - Prompts, provider calls, grounding checks, semantic extraction, persona generation, and web research.
- `worldtune/backend/app/services/world_shift_refresh.py`
  - Background refresh lifecycle, evidence enrichment, snapshot assembly, validation, and atomic publication.
- `worldtune/backend/app/services/world_shift_contract.py`
  - Deterministic fallback and the curated Armed Conflict briefing.
- `worldtune/backend/app/services/world_shift_editorial.py`
  - Curated Armed Conflict source bundle and persona examples.
- `worldtune/backend/app/services/world_shift_runtime.py`
  - Persisted refresh interval and web-research controls.
- `worldtune/backend/app/config.py`
  - Model, prompt version, schema version, and defaults.

Do not copy the Armed Conflict facts into other shifts. Copy its **structure and depth** through the shared schema and generation pipeline.

## Frontend implementation map

The main files are:

- `src/types/worldShift.ts`
- `src/schemas/worldShift.schema.ts`
- `src/components/renderers.tsx`
- `src/components/refresh-control.tsx`
- `src/app/world-shifts/[shiftId]/page.tsx`
- `src/app/globals.css`

The frontend must use shared renderers. Do not add a separate page implementation for each shift.

Use editorial hierarchy—headlines, narrative paragraphs, chronology, actors, facts, and evidence actions—not a grid of GDELT metrics.

## Efficient daily AI pipeline

Run the following sequence once per changed shift:

1. Build bounded GDELT evidence.
2. Enrich publisher metadata and images on a best-effort basis.
3. Perform one bounded web-research call, prioritising primary sources and independent specialist reporting.
4. Extract a shared semantic layer: events, claims, entities, and relationships.
5. Generate one persona-neutral briefing.
6. Generate one Finance interpretation from the shared semantics and briefing.
7. Generate one Tech interpretation from the shared semantics and briefing.
8. Remove invalid leaf objects instead of rejecting an otherwise useful report.
9. Validate all remaining evidence, claim, entity, event, and URL references.
10. Assemble both persona snapshots.
11. Publish the new snapshot atomically only after all shifts validate.

Expected maximum daily calls for nine shifts:

- 9 bounded web-research calls
- 9 semantic extraction calls
- 9 shared briefing calls
- 9 Finance calls
- 9 Tech calls
- total: 45 provider calls before retries

Retries increase cost. Prefer filtering one bad leaf object over regenerating an entire response.

### Cost and latency controls

- Schedule the refresh once daily: `86400` seconds.
- Keep web research bounded to at most eight sources per shift.
- Cache web research for six hours.
- Build research cache keys from stable evidence IDs, URLs, headlines, and snippets—not retrieval timestamps or optional image metadata.
- Cache structured generations by stable input digest, stage, persona, model, prompt version, and schema version.
- Use low provider reasoning effort for extraction and schema-constrained synthesis.
- Change the prompt or schema version only when the actual contract or prompt changes.
- Do not refresh unchanged shifts merely because the UI was opened.
- Serve the current ACTIVE snapshot throughout a refresh.

## Grounding and validation rules

Before persistence:

1. Every evidence ID must exist in the supplied evidence set.
2. Every claim ID must exist in the semantic extraction.
3. Every relationship endpoint must exist.
4. Every `derivedFrom` reference must be a supplied event, claim, or entity ID.
5. Invalid extra `derivedFrom` values may be removed if at least one grounded reference remains.
6. A reasoned exposure must contain a reasoning chain and at least one grounded `derivedFrom` reference.
7. URLs must come from supplied evidence.
8. Non-reasoned numbers must appear in the grounding input.
9. Investment recommendations, guarantees, and fabricated certainty are forbidden.
10. Preserve empty arrays when evidence is insufficient.

Important: the system prompt permits `derivedFrom` to cite **events, claims, or entities**. The validator must accept all three.

## Deterministic fallback

If an AI call or provider fails, keep the shift available.

The fallback should:

- retain the current active snapshot until the replacement is complete
- show the topic in plain language
- use the earliest evidence item as the beginning of the available evidence window
- use the latest evidence item as the latest development
- build a short source-linked chronology
- show explicit limitations
- avoid fabricated actors, facts, companies, scenarios, or causality

The fallback is a reliability mechanism, not a substitute for a successful full AI briefing.

## Refresh configuration

Set and verify the daily configuration:

```bash
curl -fsS -X PUT http://127.0.0.1:8090/world-shifts/refresh-configuration \
  -H 'content-type: application/json' \
  --data '{"intervalSeconds":86400,"webResearchEnabled":true,"webResultsPerShift":8}'

curl -fsS http://127.0.0.1:8090/world-shifts/refresh-configuration
```

Start one manual validation refresh:

```bash
curl -fsS -X POST http://127.0.0.1:8090/world-shifts/refresh
```

Poll the returned run ID:

```bash
curl -fsS http://127.0.0.1:8090/world-shifts/refresh/RUN_ID
```

Do not repeatedly restart the backend during a live refresh. A local process restart interrupts the in-memory worker even though the database row can still say `running`.

If a run was genuinely interrupted, mark only that exact stale run failed before requesting a replacement. Never modify completed runs or active snapshots.

## Starting the applications locally

Backend:

```bash
cd /Users/shashankniranjan/IdeaProjects/WorldTune-BE
export PYTHONPATH=worldtune/backend
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8090
```

Frontend:

```bash
cd /Users/shashankniranjan/IdeaProjects/WorldTune-FE
export NEXT_PUBLIC_WORLDTUNE_DATA_SOURCE=api
export NEXT_PUBLIC_WORLDTUNE_API_URL=http://localhost:8090
npm run dev
```

Confirm the listeners and health endpoints rather than assuming detached launch scripts stayed alive.

## Required checks before reporting completion

### Automated checks

Backend:

```bash
cd /Users/shashankniranjan/IdeaProjects/WorldTune-BE
.venv/bin/python -m pytest -q worldtune/backend/tests
git diff --check
```

Frontend:

```bash
cd /Users/shashankniranjan/IdeaProjects/WorldTune-FE
npm run build
git diff --check
```

### Published-data audit

For every shift and both personas, verify:

- context brief exists
- timeline is populated or limitation is explicit
- actors are attributed and source-linked
- facts and figures are source-linked
- Finance and Tech summaries differ meaningfully
- Finance exposure includes specific companies when defensible
- Tech exposure includes specific companies/capabilities when defensible
- exposure has country, horizon, mechanism, reasoning, and verification hint
- relationship graph contains meaningful edges, not only the topic node
- scenarios are conditional and source-linked
- evidence URLs resolve
- evidence images appear when source metadata supplies them
- no placeholder such as “Headline unavailable” dominates the report
- no GDELT metric is presented as a real-world causal fact
- no investment recommendation appears

### Minimum audit script shape

The audit should iterate the list endpoint, then fetch both personas for every shift and report counts:

```text
shift_id
  finance: context, timeline, actors, facts, exposures, relationships, scenarios, evidence, images
  tech:    context, timeline, actors, facts, exposures, relationships, scenarios, evidence, images
```

Treat a completed refresh with empty reports as a failure. Completion status alone is not proof.

## Common failure modes

### The page still looks like a GDELT dashboard

Cause: generic deterministic points replaced the editorial structure.

Fix: populate `contextBrief`, timeline, actors, facts, narrative points, and persona exposure through the shared contract. Keep GDELT metrics in provenance, not as the lead story.

### Only Armed Conflict has detail

Cause: rich content remains behind the curated `CONFLICT_ID` branch.

Fix: retain the curated bundle as a high-quality reference, but populate the same shared fields from `WorldShiftSynthesis` for every other shift.

### Company exposures disappear

Causes:

- `derivedFrom` accepts claims/entities but not events
- the model emits one valid and one invalid reference and the whole item is rejected
- a filtered persona field is not copied back into the validated result

Fix:

- accept grounded event, claim, and entity IDs
- remove invalid extra references while retaining an item with at least one valid reference
- filter `directImpacts`, `impactChain`, `secondOrderEffects`, `risks`, `opportunities`, `watchItems`, domain groups, and exposure map consistently

### A refresh appears permanently running

Cause: the backend process was stopped while its in-memory worker was running.

Fix: verify no worker process remains, mark only the interrupted run failed, restart the backend, and request a new run. Continue serving the previous ACTIVE snapshot.

### Paid web research repeats unnecessarily

Cause: cache digest includes changing timestamps or best-effort metadata.

Fix: base the digest on stable topic/category and evidence identity/content fields.

## Copy-ready task prompt for a lower-capability model

```text
Implement and validate WorldTune all-shift intelligence using the runbook at:
/Users/shashankniranjan/IdeaProjects/WorldTune-BE/docs/WORLDTUNE_ALL_SHIFT_INTELLIGENCE_RUNBOOK.md

Goal:
Every World Shift must use the same shared news-briefing depth and layout as Armed Conflict and Military Escalation, without copying its facts. Generate one common evidence-grounded story and distinct Finance & Investing and Tech & Career interpretations for every shift.

Rules:
1. Inspect both repositories and existing dirty changes before editing.
2. Preserve unrelated changes.
3. Extend the shared backend contract and shared frontend renderers; do not create per-shift UI forks.
4. Use one semantic layer for both personas.
5. Populate context brief, chronology, actors, facts, overview points, relationships, scenarios, and evidence for every shift.
6. Finance must explain specific company/sector exposure, direct/indirect paths, India/global relevance, and near/long-term mechanisms without trade advice.
7. Tech must explain specific company/capability opportunities, India/global relevance, and near/long-term mechanisms without claiming contracts or hiring demand.
8. Every factual item must cite supplied evidence IDs. Reasoned company items must include a reasoning chain and grounded event/claim/entity derivedFrom IDs.
9. Never invent sources, URLs, dates, figures, images, actors, or certainty. Use explicit insufficient-evidence states.
10. Keep the previous ACTIVE snapshot available until the full replacement validates and publishes atomically.
11. Configure daily refresh: 86400 seconds, web research enabled, maximum 8 sources per shift.
12. Keep paid search and AI calls efficient using stable caches, low reasoning effort, and leaf-level filtering before retries.
13. Run the complete backend tests, frontend production build, and diff checks.
14. Run one real refresh and audit every shift for both personas. Report per-shift counts for context, timeline, actors, facts, exposures, relationships, scenarios, evidence, and images.
15. Do not claim completion if only Armed Conflict is rich, if other shifts use deterministic placeholders, or if the real provider refresh was not inspected.

Return:
- files changed
- exact tests and results
- refresh run ID and final status
- daily configuration returned by the API
- per-shift/persona audit table
- any remaining evidence gaps, provider failures, or unverified boundaries
```

## Completion definition

The task is complete only when:

1. Shared backend and frontend contracts support the full briefing.
2. Every shift receives that structure without hard-coded shift-specific facts.
3. Finance and Tech are materially different interpretations of the same news.
4. Daily refresh configuration is persisted and visible in the UI.
5. Automated tests and frontend build pass.
6. A real provider refresh publishes successfully.
7. Every shift and both personas pass the published-data audit.
8. Any genuine evidence gaps are visible to the reader rather than hidden by generic text.
