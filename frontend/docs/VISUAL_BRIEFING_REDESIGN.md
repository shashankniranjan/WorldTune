# WorldTune visual briefing

The running app uses `WorldTune-BE/frontend`. This redesign builds on its existing editorial changes and snapshot-aware loading.

## Reading order and placement

1. The header establishes the topic and shows the refresh time in IST. A compact topic menu replaces the permanent left navigation column.
2. The 30-second brief presents a linked development and its interpretation together. It occupies the first desktop screen.
3. One Perspective selector controls both sector effects and personal relevance under **Impact for you**. Existing `tab=domain` links remain supported by the combined view.
4. A diagram shows one stored mechanism and its possible effect, with an explicit conditional-inference label. It never invents links between separate pathways.
5. Numbered developments show linked event titles where the event mapping is unambiguous, reporting dates, explanations, and source buttons.
6. Figures retain their full context, including attribution such as “claimed.” A vertical chronology exposes the first three events and expands to retain the rest.
7. The desktop rail holds a context image, source coverage, places mentioned in reporting, and watch items. On smaller screens the image follows the quick brief and rail information follows the analysis. Related shifts finish the page.

## Components and data boundaries

- `briefing-visuals.tsx`: quick briefing, publisher-image fallback, pathway diagram, and chronology.
- `briefing-model.ts`: IST date formatting, source preview cleanup, headline grouping, image eligibility, and event/source matching.
- `visual-briefing.css`: responsive hierarchy, type scale, focus states, and visual treatments.
- `renderers.tsx`: developments, combined impact, quantitative context, outlook, and grouped source records.
- `layout.tsx`: compact topic browser, one perspective selector, contextual rail, and accessible tab navigation.

Every original source record remains accessible. Identical headlines are grouped to reduce repeated reading; headline and publisher-family counts do not assert independent corroboration. Primary source records are presented first. Confidence and corroboration assessments remain explicitly attributed to the dataset. Numeric-only titles receive an honest unavailable label, and raw Markdown image/link markup is removed from previews.

Source publication dates, stored event dates, and briefing refresh times are distinct. A shared source alone does not assign a date: automatic event captions require a unique exact source-set match. The existing snapshot boundary prevents previous-topic or previous-persona data from being presented after navigation.

No backend schema or research refresh is required. Where the contract has no geographic coordinates, measured time series, or image-rights metadata, the UI does not invent maps, charts, or licensing claims. Images use supplied publisher URLs and source attribution; known logos/placeholders are omitted. The publisher credit and rights still need checking for publication. Image loading failures have a text fallback.

## Validation

- TypeScript type check and ESLint.
- Isolated production build, without replacing the live development build directory.
- Eight focused tests: title fallback, Markdown cleanup, duplicate preservation, primary-source ordering, IST midnight conversion, nonmatching source/event sets, ambiguous event dates, and logo exclusion.
- Live browser review on the sanctions briefing and AI infrastructure, including tech and finance perspectives.
- Desktop and 390px/320px mobile reflow checks, with no horizontal page overflow on the checked views.
- Source modal opens in place and restores focus on closing.
- Arrow-key tab navigation updates selection, and selected tabs remain visible after resizing.
- Desktop, mobile, and analysis preview screenshots saved alongside the chat.

These are implementation and browser checks, not a full WCAG certification or a user comprehension study. The backend's factual reporting, inference quality, and source timestamp accuracy were not re-researched by this frontend change.

## Comprehension-focused iteration (6 October 2026)

The briefing now leads with four labelled visual categories: change (blue), meaning (purple), possible opportunity (teal), and risk (amber). Icons and written labels repeat the colour meaning. Long excerpts retain a full-context disclosure. Analysis navigation comes before these cards so mobile readers can reach Connections immediately.

Connections now has three selectable views: cross-shift diagrams, entity relationships with search and selection, and numbered personal pathways. The map shows six links initially, with an explicit show-all control. The selected explanation sits beside the desktop diagram and below it on narrow screens. All entity records remain available in a disclosure. Relationship lines use solid/dashed patterns as well as colour. Generic associations never gain causal arrowheads; a conservative verb allowlist controls directional arrows. Confidence remains explicitly a dataset assessment, and missing snapshot evidence is reported instead of presenting misleading clickable source counts.

Design rationale: [visual hierarchy](https://www.nngroup.com/articles/visual-hierarchy-ux-definition/) determines placement; [recognition over recall](https://www.nngroup.com/articles/recognition-and-recall/) supports labelled diagrams; [reducing cognitive load](https://www.nngroup.com/articles/minimize-cognitive-load/) supports bounded initial views and expandable detail. [WCAG use of colour](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color) motivates redundant labels, icons, line styles and selection outlines. This is an implemented design hypothesis; improved comprehension has not been established through user testing.

Validation: connection-model tests cover missing endpoints, conservative arrow direction, search, provenance retention, cross-shift exclusion and snapshot immutability. Live checks cover selection, empty search, show-all, personal pathways, evidence dialog behaviour and responsive layouts. Current AI Infrastructure data contains unresolved evidence references; the new cards and graph disclose these gaps. No backend facts or evidence IDs were rewritten.
