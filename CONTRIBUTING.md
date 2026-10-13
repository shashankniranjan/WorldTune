# Contributing to WorldTune

Thanks for your interest in improving WorldTune. Bug reports, ideas, docs fixes and
pull requests are all welcome.

## Ground rules

- Be kind. This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
- Open an issue before starting a large change so we can agree on the approach.
- Keep pull requests focused: one logical change per PR.
- Never commit secrets. `.env` is gitignored; put new settings in the relevant
  `.env.example` with a comment instead.

## Development setup

```bash
git clone https://github.com/shashankniranjan/WorldTune.git
cd WorldTune
./start-worldtune.sh        # creates .venv, installs deps, starts API + UI
./stop-worldtune.sh
```

See the [README](README.md) for prerequisites and options.

## Running the checks

Run these before opening a pull request.

```bash
# Prediction engine (offline, no network)
.venv/bin/pytest -q

# World Shifts API
.venv/bin/pytest -q worldtune/backend/tests

# Frontend
cd frontend
pnpm typecheck
pnpm lint
pnpm test
```

## Pull requests

1. Fork the repo and create a branch from `main`.
2. Add or update tests for any behaviour change.
3. Update docs (`README.md`, `docs/`) when you change setup, config or contracts.
4. Write a clear PR description: what changed, why, and how you tested it.

## Reporting bugs

Open a GitHub issue with:

- what you expected and what happened instead,
- steps to reproduce,
- relevant logs (`.worldtune-run/backend.log`, `.worldtune-run/frontend.log`),
- your OS, Python and Node versions.

Security issues should not be filed publicly; see [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
