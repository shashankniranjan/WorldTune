# Security Policy

## Reporting a vulnerability

Please do **not** open a public issue for security problems.

Report vulnerabilities privately through GitHub's
[private vulnerability reporting](https://github.com/shashankniranjan/WorldPulse/security/advisories/new)
for this repository. Include a description, reproduction steps and the impact you
expect. You should get an acknowledgement within a few days.

## Scope notes

- WorldTune is a self-hosted prototype. It has no authentication and is meant to run
  on `localhost`; do not expose the API or UI to the public internet as-is.
- API keys (for example `OPENROUTER_API_KEY`) live in your local `.env`, which is
  gitignored. Never commit it.
