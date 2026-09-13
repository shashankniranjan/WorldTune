"""CLI: python -m app.seed [--force]

Creates the schema if needed and seeds the demo dataset.
"""
from __future__ import annotations

import argparse
import json
import logging

from app.db import init_db, session_scope
from app.seed.demo import seed_demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed WorldTune demo data")
    parser.add_argument("--force", action="store_true",
                        help="re-seed even if demo data is already present")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    init_db()
    with session_scope() as session:
        result = seed_demo(session, force=args.force)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
