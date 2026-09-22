# World Shift Detail Pages — High-Level Design

**Scope.** How a WorldTune World Shift detail page is produced, for every shift
and both personas (Finance & Investing, Tech & Career). Companion document:
[`WORLD_SHIFT_LLD.md`](./WORLD_SHIFT_LLD.md) for module-level detail.

---

## 1. The problem this design solves

WorldTune had one excellent World Shift page and eight thin ones. The excellent
one — `armed-conflict-and-military-escalation` — was not the output of a
pipeline. It was a hand-written exception:

```python
# app/services/world_shift_editorial.py
CONFLICT_ID = "armed-conflict-and-military-escalation"

def editorial_bundle(shift_id: str) -> dict | None:
    if shift_id != CONFLICT_ID:
        return None          # ← every other shift got nothing
```

Every other shift fell through to a templated fallback in
`world_shift_contract.py::_compose` that produced one claim per section, an
empty `exposureMap`, no imagery, and finance/tech payloads differing by 37
bytes out of 29 KB.

| Measure (per shift) | Reference | Others (before) |
|---|---|---|
| Evidence records | 27 | 10 |
| Company exposures | 7 | **0** |
| Relationship nodes / edges | 4 / 3 | 4 / 3 |
| Named actors | 5 | 0 |
| Facts & figures | 3 | 0 |
| Payload | 75 KB | 29 KB |

**The design goal was explicitly not to write eight more editorial bundles.**
It was to make the reference's *quality bar* reachable by a pipeline, so that
depth is a property of the architecture rather than of how much prose someone
hand-wrote for one topic.

---

## 2. Target architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  A. DATA ENGINEERING  (offline, deterministic, no AI)                │
│                                                                      │
│   GDELT GKG bulk  →  Bronze  →  Silver  →  Gold metrics              │
│        (35 GB)       parquet    1.41 M     daily topic/entity/source │
│                                 articles                             │
│                                     │                                │
│                     ┌───────────────┴────────────────┐               │
│                     ▼                                ▼               │
│            gold_signal_candidates            gold_signal_evidence     │
│                     │                                │               │
│                     └───────────────┬────────────────┘               │
│                                     ▼                                │
│                          gold_world_shifts.parquet   ← ranking       │
│                          shift_intelligence.json     ← briefing      │
└──────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────┐
│  B. INTERPRETATION (request time)  │                                 │
│                                    ▼                                 │
│      shift_knowledge/packs/*.py ──► world_shift_intelligence.py      │
│      (declarative domain model)     (one composer, persona-aware)    │
│                                    │                                 │
│  B'. AI PATH (background, optional, currently dormant)               │
│      world_shift_refresh.py ──► world_shift_ai.py ──► DB snapshots   │
└────────────────────────────────────┼─────────────────────────────────┘
                                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│  C. CONTRACT & UI                                                    │
│      app/schemas/world_shift.py  (one versioned contract)            │
│                    ▼                                                 │
│      GET /world-shifts/{id}?persona=…                                │
│                    ▼                                                 │
│      WorldTune-FE src/components/renderers.tsx  (one component set)  │
│      6 semantic tabs × 2 personas                                    │
└──────────────────────────────────────────────────────────────────────┘
```

### The load-bearing separation

The design turns on splitting two things that the old code conflated:

| | **Source artifact** | **Knowledge pack** |
|---|---|---|
| Answers | "What is being reported, by whom, when?" | "What is this subject, and how does it transmit?" |
| Changes | Every rebuild | Rarely — only when the domain changes |
| Built by | `scripts/build_shift_intelligence.py` | A human, declaratively |
| Contains | Publishers, headlines, dates, counts, entities | Mechanisms, actors, exposures, scenarios, headings |
| Contains **no** | Interpretation | Facts about the current news cycle |

Because a pack holds no time-bound facts, it stays valid as the reporting
changes. Because the artifact holds no interpretation, it can be rebuilt daily
without anyone reviewing prose. One composer joins them.

---

## 3. Why three interpretation paths coexist

| Path | Used for | Status |
|---|---|---|
| **Editorial** (`world_shift_editorial.py`) | The reference shift only | Frozen by instruction |
| **Knowledge** (`world_shift_intelligence.py`) | All 8 other live shifts | **Primary** |
| **AI** (`world_shift_ai.py`) | Any shift, when a snapshot exists | Built, dormant |

This is deliberate, not accumulated debt:

- The **editorial** path is the quality reference the others are measured
  against. A regression test asserts it still serves its curated content.
- The **knowledge** path is deterministic and offline-capable. It produces
  reference-grade depth with no API key, no cost and no latency.
- The **AI** path (three-stage, schema-validated, grounding-enforced) is the
  scaling answer for topics nobody has written a pack for. It is dormant only
  because no LLM key is configured — `world_shift_snapshots` is empty, so every
  request currently falls through to the knowledge path.

Resolution order in `get_contract_shift()`:

```
ACTIVE DB snapshot (AI)  →  editorial (reference only)  →  knowledge  →  generic
```

A shift with no pack still renders: `shift_knowledge/generic.py` produces a
category-shaped interpretation that states plainly that no dedicated analysis
exists, rather than an empty page.

---

## 4. Result

| Measure (per shift) | Reference | Others (before) | Others (after) |
|---|---|---|---|
| Evidence records | 27 | 10 | 25 |
| Company exposures | 7 | 0 | 6 |
| Lens groups | 1 | 1 | 3 |
| Relationship nodes / edges | 4 / 3 | 4 / 3 | 8–9 / 7–8 |
| Named actors | 5 | 0 | 6 |
| Facts & figures | 3 | 0 | 3 |
| Payload | 75 KB | 29 KB | 84–95 KB |
| Shared claim titles across personas | — | ~all | **0 of 19** |

Reference unchanged: 27 records, editorial spine intact, no headings supplied
(so the frontend renders its original wording).

---

## 5. Cross-cutting design rules

**Evidence classes are a first-class concept.** Every rendered statement
carries one of `observed | calculated | inferred | associated | reasoned`, and
the UI gives `reasoned` a visually distinct treatment. A company exposure is
always `reasoned` — the corpus establishes that a subject is being reported,
never that a named company is affected. The reasoning chain is the product: it
is what lets a reader disagree.

**Headings are data, not constants.** Section headings travel in the payload.
This exists because headings written for the reference were rendering on all
nine shifts — the timeline read *"How the escalation unfolded"* on every page.
The frontend falls back to its previous wording when a snapshot supplies none,
which is what keeps the reference byte-identical in appearance.

**Provider terminology never reaches a reader.** Theme codes are mapped to
plain English or dropped; entity strings are decoded out of offset encoding.
A test asserts no composed payload contains provider vocabulary.

**Claims cite rotating evidence windows.** Different claims cite different
publishers, so the evidence drawer is informative rather than showing the same
four records for everything on the page.

**Honest degradation over invented precision.** A single-day evidence window
says so instead of implying a chronology. A recovered headline says it was
recovered. A shift with no pack says no analysis exists yet.

---

## 6. Quality enforcement

`tests/test_world_shift_intelligence.py` (20 tests) asserts the bar per shift ×
persona, because the failure mode here is silent — a shift renders fine while
being far thinner than the reference:

- minimum claim, exposure, actor, timeline and fact counts
- a stated mechanism and cited evidence on every claim
- a reasoning chain and verification hint on every exposure
- no dangling evidence references
- **zero** shared claim titles between personas
- distinct, shift-specific headings
- no reference-shift wording leaking into another shift
- no provider terminology in any composed payload
- the reference still serves editorial content and supplies no headings

Full suite: **322 passing.**

---

## 7. Known limitations

1. **The frozen reference still leaks provider terminology** on its
   Relationships tab (`"GDELT-derived topic node"`) and in the tail of its
   evidence list (a `gdelt` tag). Pre-existing; fixing it would change the
   reference's rendered content, so it was left alone. ~3-line fix.
2. **Detector false positives.** Recovered headlines occasionally match on a
   substring — a story about a ship incident matched Semiconductors on the word
   "Intel". Every record states its headline was recovered from the URL, but
   tightening the detector vocabulary would be a real improvement.
3. **Source titles are absent upstream.** GKG metadata carries empty titles in
   this extract, so headlines are reconstructed from publisher URLs.
4. **The AI path is unexercised end-to-end** against live infrastructure. Its
   validators are unit-tested; the full three-stage run needs an LLM key.
5. **Packs are hand-written.** Eight exist. A ninth topic gets the generic
   fallback until someone writes one — which is the AI path's purpose.
