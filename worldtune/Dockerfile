# WorldTune backend image.
#
# Build context is `worldtune/` (NOT worldtune/backend), because the entity
# taxonomy in worldtune/config/ is a sibling of the backend and Docker cannot
# copy from outside the build context:
#
#     docker build -f worldtune/Dockerfile worldtune/
#
# Separate from WorldPulse's Dockerfile: the two products share no code and no
# dependency set.
FROM python:3.11-slim

WORKDIR /worldtune

# Build deps for psycopg2 (the Postgres extra used by the compose topology).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# The layout mirrors the repo so app/entities/graph.py resolves
# ../../../config/entity_graph.yaml exactly as it does in development.
COPY config ./config
COPY backend/pyproject.toml ./backend/
COPY backend/app ./backend/app

WORKDIR /worldtune/backend
RUN pip install --no-cache-dir -e ".[postgres]"

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
