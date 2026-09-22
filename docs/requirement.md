WorldTune — Signal Intelligence Engine

1. Product Objective

We are building WorldTune, not a news aggregator.

WorldTune’s purpose is:

Measure how the world is changing, identify unusual shifts early, determine what is driving those shifts, connect related developments, provide supporting evidence, and eventually personalize those changes to different user interests.

The core questions WorldTune should answer are:

1. What is happening?
2. What has changed relative to normal?
3. How unusual is the change?
4. Is it accelerating, persistent, or just a one-day spike?
5. What topics/entities/events are driving the change?
6. What evidence supports the signal?
7. Are independent data sources showing the same shift?
8. What other world signals are moving with it?
9. Why might the development matter?
10. Which developments matter to a particular user/persona?

WorldTune must distinguish between:

* normal news activity,
* temporary spikes,
* persistent trends,
* emerging trends,
* historically unusual activity,
* cross-source confirmed shifts.

Do not claim causality unless supported by appropriate evidence.

⸻

2. Product Model

The conceptual pipeline is:

WORLD DATA
↓
Historical Baseline
↓
What changed?
↓
How unusual is it?
↓
What specifically is driving it?
↓
Is it persistent/accelerating?
↓
Do independent sources confirm it?
↓
What developments appear connected?
↓
World State
↓
Persona relevance
↓
WorldTune

The final product should eventually expose four major concepts.

World State

What matters in the world right now?

Example:

AI Infrastructure          ↑↑↑
Crypto Regulation          ↑↑
Gold / Safe Haven Demand   ↑↑
India Digital Policy       ↑
Cloud Infrastructure       ↑

World Shifts

What is changing unusually quickly relative to historical behaviour?

Example:

AI Agents                    +184%
Semiconductor Infrastructure +112%
Crypto Regulation             +83%

World Connections

Which independently detected signals appear related?

Example:

Middle East tensions
↓
Oil attention
↓
Inflation discussion
↓
Interest-rate expectations
↓
Technology/market sentiment

This represents correlation/association unless causal evidence exists.

My Tune

Which World Shifts matter to a particular persona?

Example personas:

Financial
Technology
India
Executive

The underlying World State should remain canonical.

Personas should change relevance/ranking/explanation, not rewrite reality.

⸻

3. Current Data Source

The initial source is GDELT GKG.

Available information includes:

* timestamp
* article URL
* title
* domain/source
* themes
* people
* organizations
* locations
* tone/sentiment

A 15-day dataset has already been downloaded, processed and deduplicated.

Current approximate size:

Raw:       6.1 GB
Processed: 1.2 GB

⸻

4. Current Pipeline

The following pipeline already exists:

GDELT
↓
raw ingestion
↓
cleaning
↓
deduplication
↓
processed Parquet
↓
gold_daily_topic_metrics.parquet
↓
gold_signal_candidates.parquet

Current signal candidate output:

{
"rows": 96,
"entities": [
"all",
"crypto",
"india",
"macro_policy",
"metals",
"technology"
],
"causal_rule": "prior_7d_mean and prior_7d_zscore exclude the current day's value",
"limitations": [
"signals are news-volume candidates",
"no price alignment or causal effect is established",
"first three days are history-ineligible"
]
}

This is the current development position.

Do NOT rebuild existing ingestion or candidate generation unless a defect is discovered.

⸻

5. Interpretation of Current Output

gold_signal_candidates.parquet is NOT a final WorldTune signal.

It only answers:

Is news activity for this category behaving unusually relative to its recent baseline?

For example:

technology
today             = 9,800
prior_7d_mean     = 4,200
zscore            = 4.6

This tells us something unusual happened.

It does NOT tell us:

* what happened,
* which topic drove it,
* which companies/people drove it,
* whether it is persistent,
* whether it represents one event or multiple events,
* whether other sources confirm it.

Those are the next problems to solve.

⸻

6. Next Milestone — Signal Evidence Layer

Build:

gold_signal_evidence.parquet

Input:

gold_signal_candidates.parquet

For each history-eligible candidate, join back to the underlying processed GDELT records.

Example:

candidate:
date   = 2026-09-19
entity = technology
zscore = 4.3

Retrieve the GDELT records contributing to that candidate.

Calculate:

article_count
unique_domain_count
domain_diversity
top_themes
top_organizations
top_people
top_locations
top_domains

Keep the top 20 values for each where appropriate.

Also select approximately 20 representative:

article titles
article URLs

Representative articles should maximize useful coverage and avoid selecting many near-duplicate stories.

⸻

7. Persistence and Acceleration

A one-day anomaly should not automatically become a major WorldTune signal.

Calculate:

consecutive_abnormal_days
days_above_baseline_3d
days_above_baseline_7d
anomaly_3d
anomaly_7d
peak_zscore
volume_growth_1d
volume_growth_3d
volume_growth_7d
acceleration

Example:

0.4
1.1
2.8
4.3
4.9

is potentially much more meaningful than:

0.4
0.2
0.3
5.1
0.4

WorldTune must preserve this distinction.

⸻

8. Signal Strength

Create a deterministic and explainable signal_strength.

Initial heuristic can be approximately:

signal_strength =
0.40 * anomaly_score
+ 0.25 * volume_growth_score
+ 0.20 * persistence_score
+ 0.15 * source_diversity_score

Exact normalization and implementation should be documented.

Do NOT hide the calculation behind an LLM.

Every score must be explainable from stored input metrics.

Store component scores separately:

anomaly_score
volume_growth_score
persistence_score
source_diversity_score
signal_strength

The weights are V1 heuristics and should be configurable.

⸻

9. Evidence Output

The resulting record should conceptually resemble:

{
"date": "2026-09-19",
"entity": "technology",
"metrics": {
"article_count": 14820,
"prior_7d_mean": 7210,
"volume_ratio": 2.06,
"zscore": 4.31
},
"persistence": {
"consecutive_abnormal_days": 4,
"peak_zscore": 4.31,
"acceleration": 0.72
},
"sources": {
"unique_domains": 1428,
"domain_diversity": 0.86
},
"top_themes": [],
"top_organizations": [],
"top_people": [],
"top_locations": [],
"top_domains": [],
"representative_articles": [],
"scores": {
"anomaly": 0.94,
"volume_growth": 0.87,
"persistence": 0.78,
"source_diversity": 0.86,
"signal_strength": 0.88
}
}

The actual Parquet schema should remain analytical and efficient rather than blindly storing deeply nested JSON if a better relational representation is appropriate.

⸻

10. Next Stage — Event Discovery

Do NOT implement this until the Signal Evidence Layer is validated.

The broad categories currently include:

crypto
india
macro_policy
metals
technology

These are too broad to represent final WorldTune events.

For example:

technology ↑ 130%

is not useful enough.

WorldTune should eventually discover:

AI Infrastructure
Cybersecurity
Semiconductors
Apple/Product Launch
Quantum Computing
Cloud Infrastructure

within the technology signal.

The intended architecture is:

Technology candidate
↓
Relevant GDELT articles
↓
Embeddings
↓
Semantic clustering
↓
Cluster 1 — AI Infrastructure
Cluster 2 — Cybersecurity
Cluster 3 — Apple
Cluster 4 — Quantum

Each cluster can become a candidate World Event.

⸻

11. Future World Event Model

A future World Event could resemble:

{
"event_id": "evt_20260919_ai_infrastructure",
"category": "technology",
"topic": "AI Infrastructure",
"signal_strength": 0.91,
"persistence": 0.78,
"source_diversity": 0.86,
"entities": [
"NVIDIA",
"Microsoft",
"OpenAI"
],
"countries": [
"United States",
"China",
"India"
],
"evidence_count": 4210
}

Event discovery should be data-driven.

Do not ask an LLM to invent events from the complete raw dataset.

⸻

12. Future Cross-Source Confirmation

After GDELT signals work correctly, additional sources will be introduced.

Likely sources include:

GitHub
Hacker News
CoinGecko
RBI
data.gov.in
PIB
job datasets
YouTube

Example:

                    AI Agents
GDELT               ↑↑↑
GitHub               ↑↑
Hacker News          ↑↑↑
Job postings         ↑

This should create a stronger WorldTune signal than GDELT alone.

Future metrics should include:

cross_source_count
cross_source_score
source_agreement
source_disagreement

WorldTune should explicitly distinguish:

media attention
from
real-world/developer/economic/market activity

where data permits.

⸻

13. Future World Connections

WorldTune should eventually identify relationships between independently detected signals.

Example:

AI Infrastructure ↑↑↑
Semiconductors ↑↑
Data Centers ↑↑
Electricity Demand ↑
Cloud Capex ↑↑

This can become a signal graph:

AI Infrastructure
│
├── Semiconductors
│
├── Data Centers
│
├── Cloud
│
└── Energy

Relationships must initially be described as:

associated with
correlated with
moving together
co-occurring

Do NOT describe them as causal unless causal evidence exists.

⸻

14. Future LLM Layer

LLMs should NOT process the complete historical GDELT dataset.

The pipeline should reduce the data first:

Hundreds of GB historical data
↓
Parquet / DuckDB
↓
Metrics
↓
Statistical detection
↓
Candidate signals
↓
Evidence
↓
Event discovery
↓
Top World Events
↓
LLM

The LLM receives structured events and representative evidence.

Its responsibility is:

* summarization,
* explanation,
* connecting evidence,
* identifying plausible implications,
* generating persona-specific explanations.

It should NOT calculate the underlying statistical signal.

⸻

15. LLM Output Contract

Eventually an LLM should receive something like:

Event:
AI Infrastructure
Historical anomaly: 4.3 sigma
Volume change: +106%
Persistence: 4 days
Unique sources: 1,428
Entities:
NVIDIA
OpenAI
Microsoft
Themes:
AI
Semiconductors
Data Centers
Representative evidence:
...

and return structured JSON similar to:

{
"headline": "...",
"summary": "...",
"what_changed": "...",
"possible_drivers": [],
"why_it_matters": "...",
"evidence_for": [],
"evidence_against": [],
"uncertainties": [],
"confidence": "high"
}

Use possible_drivers, not causes, unless causality is established.

⸻

16. World State

Eventually WorldTune should produce one canonical daily World State.

Example:

WORLD STATE
20 September 2026
AI Infrastructure        ↑↑↑
Crypto Regulation        ↑↑
Gold / Safe Haven        ↑↑
India Digital Policy     ↑
Cloud Infrastructure     ↑

Each signal should be backed by:

signal_strength
attention
momentum
persistence
historical_anomaly
source_diversity
cross_source_confirmation
evidence

⸻

17. Persona Layer

World State should exist independently from personalization.

Architecture:

WORLD STATE
↓
Relevance Engine
↓
┌───────────┬───────────┬───────────┐
│ Financial │Technology │   India   │
└───────────┴───────────┴───────────┘

Example:

World Event:

AI Infrastructure ↑↑↑

Financial persona might emphasize:

NVIDIA
AMD
TSMC
Microsoft
data-center investment
energy demand
semiconductor supply chain

Technology persona might emphasize:

GPU infrastructure
CUDA
distributed inference
AI agents
cloud infrastructure
developer activity

The underlying evidence must remain identical.

Only relevance and explanation change.

⸻

18. Storage Architecture

Current recommended architecture:

RAW
↓
compressed source files
SILVER
↓
Parquet
ANALYTICS
↓
DuckDB + dbt
SIGNALS
↓
Parquet
APPLICATION STATE
↓
PostgreSQL
SEMANTIC SEARCH
↓
pgvector or dedicated vector DB later

Do NOT move the complete GDELT history into PostgreSQL.

Do NOT introduce a vector database until semantic event discovery/retrieval actually requires one.

⸻

19. Development Principles

Follow these principles strictly.

Explainability

Every WorldTune signal must be traceable to:

source records
→ metrics
→ baseline
→ anomaly
→ score
→ evidence
→ event
→ explanation

Reproducibility

Running the pipeline against identical inputs should produce identical statistical signals.

No fake causality

Correlation, attention and co-occurrence are not causation.

Historical comparison

WorldTune should increasingly answer:

Is this unusual relative to history?

rather than merely:

Is this large today?

Data before LLM

Use SQL/Python/statistics for calculations.

Use LLMs for interpretation.

Avoid premature infrastructure

Do not add Spark, Kafka, Kubernetes, vector databases, or complex distributed infrastructure unless scale measurements demonstrate that they are required.

⸻

20. Immediate Implementation Task

We are currently here:

gold_daily_topic_metrics
↓
gold_signal_candidates
↓
★ CURRENT POSITION ★

Implement ONLY the next layer:

gold_signal_evidence

Requirements:

1. Read gold_signal_candidates.parquet.
2. Select history-eligible candidates.
3. Join candidates to the underlying processed GDELT records.
4. Calculate:
    * article count
    * unique domains
    * domain diversity
    * top themes
    * top organizations
    * top people
    * top locations
    * top domains
5. Select up to 20 representative articles per signal.
6. Calculate:
    * consecutive abnormal days
    * abnormal days in previous 3/7 days
    * 3-day anomaly
    * 7-day anomaly
    * peak z-score
    * volume growth
    * acceleration
7. Calculate transparent component scores:
    * anomaly_score
    * volume_growth_score
    * persistence_score
    * source_diversity_score
8. Calculate configurable signal_strength.
9. Write:

gold_signal_evidence.parquet

10. Produce a validation summary containing:

* input rows
* eligible candidates
* generated evidence rows
* strongest signals
* weakest signals
* missing evidence counts
* representative examples
* limitations

⸻

21. Explicitly Out of Scope for This Iteration

Do NOT yet implement:

* LLM summarization
* embeddings
* vector database
* semantic clustering
* GitHub integration
* Hacker News integration
* CoinGecko integration
* persona personalization
* UI
* causal inference
* prediction
* Spark
* Kafka
* Kubernetes

First prove:

GDELT candidate
↓
Explainable evidence
↓
Reliable WorldTune signal

Once this layer is validated, the next milestone will be:

Signal Evidence
↓
Semantic Event Discovery
↓
World Events

The goal of this iteration is therefore not to add more data.

The goal is to prove that WorldTune can reliably answer:

Something changed. How unusual is it, what specifically changed, how long has it been changing, and what evidence supports that conclusion?