# WorldTune frontend

Next.js (App Router, TypeScript) + Tailwind v4 + TanStack Query + Recharts.
Dark-only editorial intelligence UI over the WorldTune FastAPI backend.

## Run it

```bash
# 1. backend (from worldtune/backend) — DEMO_MODE is on, zero config
rm -f worldtune.db && python3 -m uvicorn app.main:app --port 8090

# 2. frontend
cp .env.example .env.local     # NEXT_PUBLIC_API_BASE_URL=http://localhost:8090
npm install
npm run dev                    # http://localhost:3000
```

Under `docker compose up worldtune-web` the API is published on **8100**, so the
compose service passes `NEXT_PUBLIC_API_BASE_URL=http://localhost:8100`.

## Shape

| Path | What |
| --- | --- |
| `lib/api.ts` | The only module that knows the backend JSON. Typed client + interfaces hand-written against a live `/api/dashboard`. |
| `lib/score.ts` | Frontend-only score → state mapping (`VERY HOT` ≥ 65, `HOT` ≥ 55, `NEUTRAL` ≥ 45, `COOLING` ≥ 35, else `COLD`) and the colour system. |
| `lib/format.ts` | Percent / tabular number / relative-time formatting. |
| `app/page.tsx` | Home: header, YOUR WORLD TODAY strip, Financial Pulse, Career Pulse (skills + jobs), Today's Tune. |
| `app/signal/[entityType]/[entityId]/page.tsx` | Detail: overview, why it matters, full score breakdown, evidence, trend history, news, trajectory by horizon, confidence, risks, recommended action, related signals. |
| `app/persona/page.tsx` | Persona editor → `PUT /api/persona`, invalidates the dashboard query. |
| `components/` | Cards, badges, score breakdown, trend chart, tag input, shadcn-style primitives in `components/ui/`. |

## Honesty notes

- The API returns **no historical series** — only point-in-time `change_30d` /
  `change_7d` / `change_24h`. The "Trend history" chart is an explicit
  reconstruction from those anchors and says so under the chart.
- `demo_mode` and the `disclaimer` string are rendered verbatim from the API in
  the footer on every page.
