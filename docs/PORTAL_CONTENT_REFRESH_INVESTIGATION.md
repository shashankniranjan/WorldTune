# Portal content refresh: findings and implementation plan

Investigation: 23 September 2026. Planning only; no runtime code changed during this investigation.

## Finding

The evidence list, overview and persona content have different construction paths. A newly published snapshot does not guarantee a newly generated overview. The previous evidence-preservation patch corrects lost source records, but does not preserve a successful overview when a later persona stage fails. Armed Conflict additionally has explicit editorial overrides at both snapshot construction and API read time.

## Evidence from the completed run

Run: `run_41d1d7e07e5c4d4aaae4bcd4c640ce00`.
Active snapshot inspected: `snap_9f753b4cce1d4a6892b0`.
Finance and Tech use the same overview behavior in each row below.

| Shift | Published narrative | Accepted overview saved for this run | Saved AI quickTake equals published quickTake |
|---|---|---|---|
| Armed Conflict and Military Escalation | Fixed editorial text | Yes | No |
| Inflation and Rates | Knowledge-pack fallback | No | N/A |
| AI Infrastructure | Knowledge-pack fallback | Yes | No |
| Semiconductors | AI synthesis | Yes | Yes |
| Cybersecurity | AI synthesis | Yes | Yes |
| Sanctions and Economic Warfare | Knowledge-pack fallback | No | N/A |
| Crypto Regulation | Knowledge-pack fallback | No | N/A |
| India Digital Policy | Knowledge-pack fallback | No | N/A |
| Cloud Infrastructure | Knowledge-pack fallback | No | N/A |

Absence of an accepted cache record is not proof that no API request occurred: rejected responses are not stored as accepted generations. Six fallback shifts contain zero web_research entries in the active snapshot, despite eight citations each being saved by research in that run. Armed Conflict, Semiconductors and Cybersecurity each already contain eight web_research entries.

## Confirmed failure paths

### 1. Successful overview discarded after a persona failure

`worldtune/backend/app/services/world_shift_refresh.py`, `RefreshService._run`:

- Research, extraction, overview, Finance and Tech are enclosed by one exception handler.
- An accepted overview is committed to the generation cache before Finance begins.
- Finance failure jumps to `_compose(row, rows, "tech", meta)`, discards that accepted overview for publication, and prevents Tech generation from being attempted for that shift.
- The same Tech fallback object is relabeled for Finance and Tech, rather than composing each persona independently.
- The previous patch changes `fallback.evidence` only. It does not change `fallback.shift.overview` or `quickTake`.

The restarted run `run_51d1e365ab334cf0b92c7d6180faf2b1` reproduces this exactly for AI Infrastructure. Its overview was accepted and cached. Finance then failed schema validation (`near_term` is outside the horizon enum) and subsequently grounding validation (`forbidden causal/predictive language in mechanism`). At 02:09:59 IST the log records fallback retaining 18 sources, eight from web research. That is evidence preservation, not preservation of the successful story.

### 2. Armed Conflict explicitly excludes dynamic narrative

`_snapshot_payload` assigns AI summary, overview and persona content only when `base.shift.id != CONFLICT_ID`. Consequently this shift can be marked with the Gemini model while still containing editorial narrative.

`world_shift_contract.get_contract_shift` then calls `editorial_bundle(shift_id)` and overwrites the persisted summary, overview and content again on GET. Correcting just the writer would therefore be insufficient. Read-time recomposition also allows content to change without changing the snapshot ID.

### 3. Fallback short versions are fixed knowledge-pack prose

`world_shift_contract._compose` delegates to `world_shift_intelligence.compose_parts`, which loads a separate `shift_intelligence.json` artifact and a declarative knowledge pack. `build_overview` assigns:

- `whatHappened = pack.what_it_is`
- `whyItMatters = pack.why_it_matters`
- `quickTake = pack.system_framing`

This produces repeatable background explanations such as “Follow the chain from commitment to consequence…”, even when research has collected new sources. The fallback composer does not receive the current run's evidence as its narrative input.

### 4. The frontend renders these stored fields directly

`WorldTune-FE/src/components/layout.tsx` renders “The short version” from `shift.overview.quickTake`, falling back to `shift.summary`. `OverviewRenderer` renders `contextBrief.latest` and the other overview fields. The Evidence tab independently renders `data.evidence`. Adding citations cannot automatically rewrite those narrative fields.

The related-reporting sidebar takes the first three eligible evidence entries without sorting by verified recency. Appended new sources can therefore remain below older records.

### 5. Completion and timestamps conceal partial success

The worker publishes after per-shift fallback and reports `completed`/49 of 49. Its `validating` stage mainly updates counters; it is not a full narrative freshness/coverage acceptance gate. The completed run's `validation_failures=382` includes objects removed by filtering; it is not 382 failed requests.

`generatedAt` is allocated near run start. It describes snapshot construction, not article publication or successful narrative refresh. Web citation `publishedAt` is currently set to retrieval time when citations are parsed. That must not be treated as proof of source publication date.

### 6. Downloaded data is not automatically incorporated

Refresh loads the configured processed World Shift artifact. The fallback composer reads a different intelligence artifact. Downloading raw GDELT data does not rebuild either artifact automatically in this path. The new live-GDELT option remains disabled by default; the previous bounded probe received HTTP 429. Research can still add sources through OpenRouter, but those sources must flow into the actual narrative builder.

### 7. Cache and browser behavior are secondary factors

AI cache identity already includes input, stage, persona, model, prompt and schema versions. A cache hit can legitimately reuse unchanged evidence. Successful cache hits retain their original generation run ID, so querying only the current run misses reused results.

Frontend list polling follows the configured refresh interval and run tracking is held in page memory. This can delay discovery of a completed snapshot, but cannot explain the stale overview text already present in the published database payload.

## Implementation plan

### P0 — preserve valid content and remove overwrites

1. Separate the common overview pipeline from each persona pipeline. Persist an accepted common overview and assemble it independently of Finance/Tech success. Catch failures per persona and attempt Tech even if Finance fails.
2. Compose persona-specific fallback separately. Reuse a prior validated persona section only with its original provenance and complete evidence references; otherwise show a bounded unavailable state.
3. Remove the Armed Conflict exclusion and read-time editorial overwrite behind a reversible content-policy flag. Preserve editorial background as explicitly dated background, not as the current story. Serve the persisted snapshot consistently on every GET.
4. Publish successful common content even when persona content is degraded. When common synthesis fails, retain the previous accepted common section with its original update date and a clear degraded status; if absent, build a modest evidence-derived latest-developments list. Never label knowledge-pack background as the latest update.

### P1 — establish one source set and accurate freshness

5. Pass the run's normalized evidence into all composition paths, including fallback. Preserve any prior evidence referenced by retained sections. Validate every evidenceId/claimId/entityId before promotion; replacing the evidence array alone can orphan references in old narrative sections.
6. Separate verified publication time, GDELT observation time, retrieval time, narrative generation time and snapshot publication time. Unknown publication dates remain unknown. Normalize legacy web citations without pretending their retrieval timestamps were publisher dates.
7. Make source ingestion explicit: record the input artifact version, its coverage cutoff, new source URLs and evidence digest per shift. Rebuild/consume downloaded artifacts through one documented pipeline. Bound GDELT requests, honor rate limits and expose ingestion failure rather than stamping old content as current.
8. Align research with current developments: request dated recent reporting separately from background sources, fetch usable source text within bounded limits, and preserve source attribution. Search citations alone do not prove the existence of a fresh event.

### P1 — validation, retries and publication quality

9. Keep schema and grounding checks. Schema mode is already requested; merely adding JSON-schema mode will not fix this. Record exact field-path failures and provider mode; use targeted repair for invalid fields, and only normalize aliases where semantics are unambiguous. Do not silently convert `near_term` into an arbitrary numeric horizon or weaken grounding rules.
10. Record stage outcome, attempts, accepted output ID, reused generation ID, evidence digest, rejection reason and duration per shift/persona. Distinguish removed objects, rejected responses and failed stages.
11. Add section-level provenance/status to the FE/BE contract compatibly. Distinguish fully refreshed, partially refreshed, retained and unavailable sections. A publication may complete with degraded content, but the UI must say so.
12. Use real stage accounting, including failed/skipped work. The existing fallback calculation uses four units per shift even when web research makes five; replace it with recorded stage outcomes. Validate content/reference integrity before atomic promotion.

### P2 — portal presentation

13. Render “Latest” and “The short version” from the accepted common narrative. Keep background visibly separate. Show evidence cutoff and narrative status where they help the reader assess freshness.
14. Sort recent reporting by verified publication/observation date, distinguish background research, and give unknown dates an explicit label. Maintain coherent snapshot selection across list, overview, impact and evidence.
15. Persist/discover the active or most recent run across reloads and offer the completed snapshot consistently. This improves visibility without hiding backend composition failures behind browser refresh behavior.

## Verification and acceptance

- Replay the existing stored generations into a candidate snapshot in an isolated database before making new paid calls.
- Inject Finance failure after successful common synthesis: both personas retain the accepted overview; Tech is still attempted; evidence references resolve.
- Inject overview failure: retained story keeps its original generation time and degraded status; newly retrieved evidence does not imply a new overview.
- Armed Conflict uses a supplied changed AI summary/quickTake; persisted payload, GET response and rendered page agree.
- Run all nine shifts and both personas through schema validation, source-reference checks and API-to-renderer comparisons. Changes in evidence should trigger reevaluation; identical factual evidence need not force cosmetic rewording.
- Confirm publication/observation/retrieval date handling, cache reuse attribution, fallback counts, snapshot promotion and reload behavior.
- Perform one bounded live canary after replay passes, then verify all nine shifts on a full refresh. Record actual provider errors, usage and remaining degraded sections.

## Reversibility

Use a single documented policy switch for legacy versus new narrative assembly, with related defaults and cache/prompt versions recorded together. Keep original snapshots and database backup before migrations. New sections/provenance should be additive where possible. Roll back code policy and atomically select the previous valid snapshot without deleting evidence or resetting unrelated changes. The existing evidence-preservation switch alone does not revert or solve the narrative issue.

## Runtime boundary observed

The newer run was last recorded at 27/49 during this investigation. A subsequent live API comparison received connection refused; the log shows graceful shutdown of backend process 84720. Database and code findings above are verified, but no fresh browser/API comparison was possible after that shutdown. No service restart, new paid refresh, or implementation change was performed for this planning request.
