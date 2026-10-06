# WorldTune frontend (Next.js). Build context is ./frontend.
#
# NEXT_PUBLIC_* values are inlined into the browser bundle at build time, so the
# API URL must be the address the *browser* uses (the host-published API port),
# not the compose-internal service name.
FROM node:22-alpine

WORKDIR /app
RUN corepack enable && corepack prepare pnpm@10 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

ARG NEXT_PUBLIC_WORLDTUNE_API_URL=http://localhost:8100
ARG NEXT_PUBLIC_WORLDTUNE_DATA_SOURCE=api
ENV NEXT_PUBLIC_WORLDTUNE_API_URL=$NEXT_PUBLIC_WORLDTUNE_API_URL \
    NEXT_PUBLIC_WORLDTUNE_DATA_SOURCE=$NEXT_PUBLIC_WORLDTUNE_DATA_SOURCE \
    NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

ENV NODE_ENV=production
EXPOSE 3000
CMD ["pnpm", "exec", "next", "start", "-p", "3000"]
