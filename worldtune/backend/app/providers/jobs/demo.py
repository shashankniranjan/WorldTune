"""Deterministic demo job postings -- the DEMO_MODE=true path.

Generates 48 postings across Data Engineering / AI-ML / Platform at varying
seniority, location and salary, so Career Pulse always has a real ranking
problem to solve rather than a handful of rows.

Two design points that make the demo data *useful* rather than merely
present:

  1. Postings are spread over the last 60 days with a skill mix that
     **drifts**: Iceberg / LLM / agents / vector-database appear with rising
     probability toward the present, Hadoop-era and plain-batch vocabulary
     with falling probability. That is what gives the trend engine a genuine
     7d-vs-30d signal instead of noise around a constant.
  2. Locations deliberately include Bengaluru, Remote-India, Remote-Global
     and US/EU hubs, so the persona's location-relevance sub-score
     discriminates rather than saturating.

Everything is drawn from a seeded generator, so the same day produces the
same board.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from app.providers.base import JobsProvider
from app.schemas.canonical import CanonicalJob

# (title, role_family_hint, core skills always present)
TITLE_POOL: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Senior Data Engineer", ("Python", "Spark", "SQL", "Airflow")),
    ("Staff Data Engineer", ("Python", "Spark", "Kafka", "dbt", "SQL")),
    ("Data Platform Engineer", ("Kubernetes", "Spark", "Airflow", "Terraform-free stack")),
    ("AI Data Engineer", ("Python", "LLM", "vector database", "embeddings")),
    ("ML Platform Engineer", ("Python", "MLOps", "Kubernetes", "PyTorch")),
    ("Analytics Engineer", ("dbt", "SQL", "Snowflake")),
    ("Lead Data Engineer", ("Spark", "Kafka", "Databricks", "Delta Lake")),
    ("Principal Data Engineer", ("Spark", "Iceberg", "distributed systems", "SQL")),
    ("Data Engineer II", ("Python", "SQL", "Airflow")),
    ("Senior Machine Learning Engineer", ("PyTorch", "MLOps", "Python")),
    ("LLM Infrastructure Engineer", ("LLM", "RAG", "vector database", "Kubernetes")),
    ("Senior Platform Engineer, Data", ("Kubernetes", "Docker", "AWS", "Airflow")),
)

COMPANIES = (
    "Flipkart", "Swiggy", "Razorpay", "PhonePe", "Zomato", "Meesho",
    "Thoughtworks", "Databricks", "Snowflake", "Confluent", "Atlassian",
    "Walmart Global Tech", "Target India", "Goldman Sachs Engineering",
    "Stripe", "Datadog", "Cloudflare", "Canva",
)

# (display, country, remote)
LOCATIONS = (
    ("Bengaluru, India", "India", False),
    ("Bengaluru, India", "India", False),
    ("Bengaluru, India", "India", False),
    ("Hyderabad, India", "India", False),
    ("Pune, India", "India", False),
    ("Remote - India", "India", True),
    ("Remote - Global", "", True),
    ("Gurugram, India", "India", False),
    ("London, UK", "United Kingdom", False),
    ("Berlin, Germany", "Germany", False),
    ("San Francisco, CA", "United States", False),
)

# Skills whose prevalence RISES toward the present (emerging demand).
RISING_SKILLS = ("Apache Iceberg", "LLM", "RAG", "vector database", "LangGraph",
                 "agents", "embeddings", "Delta Lake", "Flink")
# Skills whose prevalence FALLS toward the present (cooling demand).
FALLING_SKILLS = ("Redshift", "TensorFlow", "Azure")
# Skills with roughly flat prevalence (the stable core).
STABLE_SKILLS = ("Python", "SQL", "Spark", "Kafka", "Airflow", "dbt", "AWS", "GCP",
                 "Kubernetes", "Docker", "Snowflake", "Databricks", "BigQuery", "MLOps")

DESCRIPTION_TEMPLATE = (
    "{company} is hiring a {title} to join our data platform group in {location}.\n\n"
    "You will design and operate large-scale pipelines, own data quality and "
    "reliability, and partner with analytics and ML teams.\n\n"
    "What we look for:\n{core_bullets}\n\n"
    "Nice to have:\n{extra_bullets}\n\n"
    "We work with {stack}. {seniority_line}"
)


class DemoJobsProvider(JobsProvider):
    name = "demo:jobs"
    is_live = False

    def __init__(self, as_of: datetime | None = None, count: int = 48, seed: int = 2025):
        self._as_of = as_of or datetime.now(timezone.utc)
        self._count = count
        self._seed = seed

    def is_available(self) -> bool:
        return True

    def fetch_jobs(self, *, query: str = "", location: str = "",
                   limit: int = 50) -> list[CanonicalJob]:
        jobs = self._generate()
        needle = (query or "").strip().lower()
        if needle:
            jobs = [j for j in jobs if needle in j.title.lower()
                    or needle in j.description.lower()]
        if location:
            jobs = [j for j in jobs if location.lower() in j.location.lower()]
        return jobs[:limit]

    # -- generation ----------------------------------------------------------
    def _generate(self) -> list[CanonicalJob]:
        rng = np.random.default_rng(self._seed)
        window_days = 60
        jobs: list[CanonicalJob] = []
        for i in range(self._count):
            title, core = TITLE_POOL[int(rng.integers(len(TITLE_POOL)))]
            company = COMPANIES[int(rng.integers(len(COMPANIES)))]
            loc, country, remote = LOCATIONS[int(rng.integers(len(LOCATIONS)))]

            days_ago = int(rng.integers(0, window_days))
            # recency in [0, 1]: 0 == oldest posting, 1 == posted today.
            recency = 1.0 - days_ago / float(window_days)

            extras: list[str] = []
            for skill in RISING_SKILLS:
                # 8% floor at the window start rising to ~55% today.
                if rng.random() < 0.08 + 0.47 * recency:
                    extras.append(skill)
            for skill in FALLING_SKILLS:
                if rng.random() < 0.45 - 0.35 * recency:
                    extras.append(skill)
            for skill in STABLE_SKILLS:
                if rng.random() < 0.30:
                    extras.append(skill)

            core_list = list(core)
            extra_list = [s for s in extras if s not in core_list][:6]
            salary_min, salary_max, currency = _salary_for(title, country, rng)

            description = DESCRIPTION_TEMPLATE.format(
                company=company,
                title=title,
                location=loc,
                core_bullets="\n".join(f"  - Strong hands-on {s}" for s in core_list),
                extra_bullets="\n".join(f"  - Exposure to {s}" for s in extra_list) or "  - Curiosity",
                stack=", ".join(core_list + extra_list),
                seniority_line=(
                    "This is a senior individual-contributor role with architecture ownership."
                    if any(w in title.lower() for w in ("senior", "staff", "lead", "principal"))
                    else "This role suits engineers building depth in data systems."
                ),
            )
            posted = self._as_of - timedelta(days=days_ago,
                                             hours=int(rng.integers(0, 24)))
            jobs.append(
                CanonicalJob(
                    external_id=f"demo-job-{i:04d}",
                    title=title,
                    company=company,
                    description=description,
                    location=loc,
                    country=country,
                    remote=remote,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=currency,
                    url=f"https://jobs.worldtune.local/demo/{i:04d}",
                    source="demo:jobs",
                    posted_at=posted,
                )
            )
        jobs.sort(key=lambda j: j.posted_at, reverse=True)
        return jobs


def _salary_for(title: str, country: str, rng) -> tuple[float, float, str]:
    """Plausible bands. India in INR lakhs-equivalent absolute INR, else USD."""
    lowered = title.lower()
    if "principal" in lowered:
        tier = 2.1
    elif "staff" in lowered or "lead" in lowered:
        tier = 1.7
    elif "senior" in lowered:
        tier = 1.35
    elif " ii" in lowered:
        tier = 0.9
    else:
        tier = 1.0
    if country == "India":
        base = 2_600_000 * tier * float(1.0 + rng.normal(0, 0.08))
        return round(base, -4), round(base * 1.35, -4), "INR"
    base = 145_000 * tier * float(1.0 + rng.normal(0, 0.08))
    return round(base, -3), round(base * 1.3, -3), "USD"
