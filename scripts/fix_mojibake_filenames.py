#!/usr/bin/env python3
"""
One-shot: rename business/*.html and ar/business/*.html files whose names were
corrupted by interpreting Arabic UTF-8 bytes as CP437 characters.

Round-trip: current Unicode name -> encode as CP437 bytes -> decode as UTF-8
recovers the original Arabic name.

Safe: only renames files whose names have non-ASCII characters AND whose
CP437 round-trip yields a clean UTF-8 string. Prints a plan first.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

def fix_name(name: str) -> str | None:
    """Return the corrected name, or None if no correction needed/possible."""
    if all(ord(c) < 128 for c in name):
        return None  # pure ASCII, no fix needed
    try:
        recovered = name.encode("cp437").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None
    # Sanity: if the result is identical, don't rename
    if recovered == name:
        return None
    return recovered


def main(apply: bool) -> int:
    renames: list[tuple[Path, Path]] = []
    for d in ("business", "ar/business"):
        dp = ROOT / d
        if not dp.exists():
            continue
        for f in sorted(dp.glob("*.html")):
            new_name = fix_name(f.name)
            if new_name:
                renames.append((f, f.with_name(new_name)))

    print(f"Files to rename: {len(renames)}")
    if not renames:
        return 0

    for old, new in renames[:8]:
        print(f"  {old.relative_to(ROOT)}")
        print(f"    -> {new.relative_to(ROOT)}")
    if len(renames) > 8:
        print(f"  ... and {len(renames) - 8} more")

    if not apply:
        print("\n(dry run — pass --apply to perform renames)")
        return 0

    done = 0
    for old, new in renames:
        if new.exists():
            print(f"SKIP (target exists): {new.relative_to(ROOT)}")
            continue
        old.rename(new)
        done += 1
    print(f"\nRenamed {done} files.")
    return 0


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    sys.exit(main(apply))
