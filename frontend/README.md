# WorldTune FE

Dynamic intelligence presentation layer for versioned `WorldShiftSnapshot` JSON. It deliberately does not generate claims: all observed evidence, inferred relationships, scenarios, and persona interpretation are received as data and rendered through six semantic tabs.

## Contract boundary

`src/types/worldShift.ts` and `src/schemas/worldShift.schema.ts` define the frozen frontend contract. Every response includes `snapshotId`, `generatedAt`, and `validUntil`; the query client refuses mismatched snapshot IDs so a page cannot combine data from different runs.

The real API adapter is the default. Set `NEXT_PUBLIC_WORLDTUNE_DATA_SOURCE=mock` only for
isolated UI work. The complete backend/frontend low-level design is documented at
`/Users/shashankniranjan/IdeaProjects/WorldTune-BE/docs/WORLDTUNE_FE_BE_LLD.md`.

The refresh control in the dashboard is persisted by the backend. It defaults to five minutes
during validation and can be changed to twelve hours from the UI after sign-off. Bounded web
research can be enabled independently; disabling it keeps deterministic source-only refreshes.

## World Shift detail pages

Six semantic tabs (Overview, Market/Tech Impact, Your Lens, Relationships, What Happens Next,
Evidence) render every World Shift for both personas through **one** component set in
`src/components/renderers.tsx`. There is no per-shift branching in the frontend.

**Section headings arrive as data.** `Overview.timelineKicker` / `timelineHeading` and
`Impact.kicker` / `headline` / `exposureHeadline` / `exposureBlurb` / `lensTitle` / `lensBlurb`
are supplied per shift and per persona. This exists because headings written for one shift were
previously rendering on all of them — the timeline read *"How the escalation unfolded"* on every
page. Each site keeps its original literal as a `??` fallback, which is what leaves the
reference shift's page unchanged for snapshots that supply no headings.

**Evidence classes drive visual treatment.** `observed | calculated | inferred | associated |
reasoned` are toned differently, and `reasoned` renders as *"Inference · not observed"* with its
reasoning chain in a disclosure. A reader must never mistake a reasoned company exposure for
something the corpus established.

The backend design behind these pages is documented in
`WorldTune-BE/docs/WORLD_SHIFT_HLD.md` and `WorldTune-BE/docs/WORLD_SHIFT_LLD.md`.

## Run

```sh
pnpm install
pnpm dev
```

Open `/world-shifts/ai-infrastructure?persona=tech&tab=overview`, and switch `persona` between
`tech` and `finance` and `tab` between the six semantic tabs to exercise the full contract.

```sh
npx tsc --noEmit      # contract types
npx next lint
```
