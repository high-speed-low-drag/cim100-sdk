"""Fetch the pinned CGMES profile OWL files into build/profiles/.

Usage: fetch_profiles.py [--force] [--dest DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codegen.profile_source import DEFAULT_DEST, ProfileFetchError, ensure_profiles


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    args = ap.parse_args()
    try:
        paths = ensure_profiles(args.dest, force=args.force)
    except ProfileFetchError as exc:
        print(f"error: could not fetch profiles: {exc}", file=sys.stderr)
        return 1
    for keyword, path in paths.items():
        print(f"{keyword:5} {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
