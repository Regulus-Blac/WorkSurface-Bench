#!/usr/bin/env python3
"""Verify a WorkSurface source/public tree against its JSON lock file."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> tuple[int, str]:
    raw = path.read_bytes()
    return len(raw), hashlib.sha256(raw).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lock", type=Path)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.lock.read_text(encoding="utf-8"))
    recorded_root = payload.get("root") or payload.get("source_profile")
    if not recorded_root and not args.root:
        raise ValueError("lock has neither root nor source_profile")
    root = (args.root or Path(recorded_root)).resolve()

    expected = {row["path"]: row for row in payload.get("files", [])}
    actual_paths = {
        str(path.relative_to(root)): path
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
    missing = sorted(set(expected) - set(actual_paths))
    unexpected = sorted(set(actual_paths) - set(expected))
    mismatches = []
    actual_hashes = []
    for relative in sorted(set(expected) & set(actual_paths)):
        size, sha256 = digest(actual_paths[relative])
        actual_hashes.append(sha256)
        row = expected[relative]
        if size != row["size"] or sha256 != row["sha256"]:
            mismatches.append(relative)

    aggregate = hashlib.sha256("".join(actual_hashes).encode("ascii")).hexdigest()
    aggregate_matches = (
        not missing
        and not unexpected
        and not mismatches
        and aggregate == payload.get("aggregate_sha256")
    )
    result = {
        "state": "passed" if aggregate_matches else "failed",
        "lock": str(args.lock.resolve()),
        "root": str(root),
        "files": len(actual_paths),
        "missing": missing,
        "unexpected": unexpected,
        "mismatches": mismatches,
        "aggregate_sha256": aggregate,
        "expected_aggregate_sha256": payload.get("aggregate_sha256"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not aggregate_matches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
