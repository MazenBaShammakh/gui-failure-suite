"""
build_custom_tasks.py

Compiles hand-written custom task definitions into the full GUIFailureSuite
record schema and patches them into the existing gui_suite_<N> chunks under
csv/, json/, and jsonl/.

You only supply `task` + `platform` (and optionally `app`); this script fills
in the constant fields and the auto-incrementing id:

    benchmark      = GUIFailureSuite
    benchmark_id   = gui-failure-suite
    split          = test
    platform_type  = <platform>
    id             = gui-failure-suite-<platform>-<NNNN>   (global running counter,
                     continues after the highest id already in the suite)
    app            = per-entry override, else the platform default:
                       web              -> http://localhost:3000
                       mobile           -> com.mazenbashammakh.mobile
                       desktop_windows  -> desktop.exe

Custom tasks are appended after all the source-benchmark records, and the whole
suite is re-packed into chunks of up to 1,000 records (gui_suite_1, gui_suite_2,
…). The original benchmark chunks are preserved; new chunks are created as
needed. Duplicates are never added — a task is a duplicate when its
(task, app, platform_type) combination already exists in the suite.

Definitions live in this folder as YAML (or JSON). Every *.yaml / *.yml / *.json
file is read (sorted by name), except *.example.* files. Either a flat list...

    - platform: web
      task: Log in with a valid email and password
    - platform: desktop_windows
      task: Open the Settings window
      app: MyApp.exe                       # optional override

...or grouped by platform:

    web:
      - task: Log in with a valid email and password
    mobile:
      - task: Add the first item to favorites

Usage:
    python build_custom_tasks.py                 # append new (non-duplicate) tasks
    python build_custom_tasks.py --reset         # wipe all custom tasks, then rebuild
    python build_custom_tasks.py --delete-all    # wipe all custom tasks, add nothing
    python build_custom_tasks.py --dry-run       # preview, write nothing
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import yaml

# ── paths ─────────────────────────────────────────────────────────────────────

DEF_DIR   = Path(__file__).parent
BASE_DIR  = DEF_DIR.parent
JSONL_DIR = BASE_DIR / "jsonl"
JSON_DIR  = BASE_DIR / "json"
CSV_DIR   = BASE_DIR / "csv"

CHUNK_PREFIX = "gui_suite_"
CHUNK_SIZE   = 1000

# ── constants from the suite schema ───────────────────────────────────────────

BENCHMARK    = "GUIFailureSuite"
BENCHMARK_ID = "gui-failure-suite"
SPLIT        = "test"

# Per-platform default `app`; also the set of accepted platforms.
PLATFORM_DEFAULTS: dict[str, str] = {
    "web":             "http://localhost:3000",
    "mobile":          "com.mazenbashammakh.mobile",
    "desktop_windows": "desktop.exe",
}

# Convenience aliases accepted in definition files.
PLATFORM_ALIASES: dict[str, str] = {
    "desktop": "desktop_windows",
}

# Field order — matches the rest of the suite (see preprocessing/update_apps.py).
FIELDS = ["id", "benchmark_id", "benchmark", "split", "app", "platform_type", "task"]


# ── definition loading ────────────────────────────────────────────────────────

def load_definitions(directory: Path) -> list[dict]:
    """
    Read every definition file in `directory` (sorted by name) and return a
    flat list of normalized entries: {"platform": str, "task": str, "app": str|None}.

    Skips this script and any *.example.* files.
    """
    entries: list[dict] = []

    def_files = sorted(
        p for p in directory.iterdir()
        if p.suffix.lower() in (".yaml", ".yml", ".json")
        and ".example." not in p.name.lower()
    )

    if not def_files:
        sys.exit(
            f"ERROR: no definition files (*.yaml / *.yml / *.json) found in {directory}.\n"
            f"       Create one, e.g. {directory / 'tasks.yaml'}."
        )

    for path in def_files:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            sys.exit(f"ERROR: could not parse {path.name}: {exc}")

        if data is None:
            continue

        entries.extend(_normalize(data, path.name))

    return entries


def _normalize(data, source: str) -> list[dict]:
    """Expand one parsed definition file into normalized entries."""
    out: list[dict] = []

    if isinstance(data, list):
        # Flat list — each item must declare its own platform.
        for i, item in enumerate(data, 1):
            out.append(_normalize_item(item, source, i, platform=None))

    elif isinstance(data, dict):
        # Grouped by platform key.
        for platform, items in data.items():
            if not isinstance(items, list):
                sys.exit(
                    f"ERROR: in {source}, value of '{platform}' must be a list of tasks."
                )
            for i, item in enumerate(items, 1):
                out.append(_normalize_item(item, source, i, platform=platform))
    else:
        sys.exit(f"ERROR: {source} must contain a list or a platform-keyed mapping.")

    return out


def _normalize_item(item, source: str, idx: int, platform: str | None) -> dict:
    """Validate and normalize a single task entry."""
    # Allow a bare string when the platform is known from the grouping key.
    if isinstance(item, str) and platform is not None:
        item = {"task": item}

    if not isinstance(item, dict):
        sys.exit(f"ERROR: {source} entry #{idx} must be a mapping (got {type(item).__name__}).")

    plat = item.get("platform", platform)
    task = item.get("task")
    app  = item.get("app")  # optional override of the launchable app/package
    # Any other keys (target_app, start_route, target_screen, defect, …) are
    # intentionally ignored — generated records use the suite's 7-field schema.

    if plat is None:
        sys.exit(f"ERROR: {source} entry #{idx} is missing 'platform'.")

    plat = PLATFORM_ALIASES.get(plat, plat)
    if plat not in PLATFORM_DEFAULTS:
        sys.exit(
            f"ERROR: {source} entry #{idx} has unknown platform '{item.get('platform', platform)}'. "
            f"Valid: {', '.join(PLATFORM_DEFAULTS)} (alias: {', '.join(PLATFORM_ALIASES)})."
        )
    if not task or not str(task).strip():
        sys.exit(f"ERROR: {source} entry #{idx} ({plat}) is missing a non-empty 'task'.")

    return {
        "platform": plat,
        "task": str(task).strip(),
        "app": str(app).strip() if app not in (None, "") else None,
    }


# ── suite chunk I/O ───────────────────────────────────────────────────────────

def numeric_chunks(directory: Path, ext: str) -> list[tuple[int, Path]]:
    """Return [(index, path), …] for gui_suite_<int>.<ext>, sorted by index."""
    out: list[tuple[int, Path]] = []
    for p in directory.glob(f"{CHUNK_PREFIX}*.{ext}"):
        m = re.fullmatch(rf"{re.escape(CHUNK_PREFIX)}(\d+)", p.stem)
        if m:
            out.append((int(m.group(1)), p))
    return sorted(out)


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_all_records() -> list[dict]:
    """Load every record across all numeric chunks (jsonl is the source of truth)."""
    chunks = numeric_chunks(JSONL_DIR, "jsonl")
    if not chunks:
        sys.exit(f"ERROR: no {CHUNK_PREFIX}<N>.jsonl chunks found in {JSONL_DIR}")
    records: list[dict] = []
    for _, path in chunks:
        records.extend(load_jsonl(path))
    return records


def save_jsonl(records: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def save_json(records: list[dict], path: Path) -> None:
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=None) + "\n",
        encoding="utf-8",
    )


def save_csv(records: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


# ── helpers ───────────────────────────────────────────────────────────────────

def is_custom(rec: dict) -> bool:
    return rec.get("benchmark_id") == BENCHMARK_ID


def dup_key(rec: dict) -> tuple[str, str | None, str | None]:
    """Duplicate identity: (task, app, platform_type)."""
    return (rec.get("task"), rec.get("app"), rec.get("platform_type"))


def id_counter(rec: dict) -> int:
    """Parse the trailing 4-digit counter from any suite id (…-<NNNN>)."""
    try:
        return int(rec["id"].rsplit("-", 1)[-1])
    except (KeyError, ValueError):
        return 0


def chunked(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


# ── main ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Patch custom task definitions into the GUIFailureSuite chunks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--reset",
        action="store_true",
        help="Remove ALL existing custom tasks first, then rebuild from definitions.",
    )
    mode.add_argument(
        "--delete-all",
        action="store_true",
        help="Remove ALL existing custom tasks and add nothing (pure reset).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing any files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    records = load_all_records()
    base   = [r for r in records if not is_custom(r)]
    custom = [r for r in records if is_custom(r)]

    # Reset / delete-all wipe the existing custom tasks.
    kept_custom = [] if (args.reset or args.delete_all) else custom

    new_records: list[dict] = []
    skipped: list[dict] = []

    if not args.delete_all:
        entries = load_definitions(DEF_DIR)

        existing_keys = {dup_key(r) for r in base + kept_custom}
        # Single global running counter — continues after the highest id in the
        # suite (matches the source-benchmark numbering, which runs 1..N across
        # all benchmarks/platforms).
        next_num = max((id_counter(r) for r in base + kept_custom), default=0) + 1

        for entry in entries:
            platform = entry["platform"]
            app = entry["app"] if entry["app"] is not None else PLATFORM_DEFAULTS[platform]
            rec = {
                "id":            "",  # assigned below
                "benchmark_id":  BENCHMARK_ID,
                "benchmark":     BENCHMARK,
                "split":         SPLIT,
                "app":           app,
                "platform_type": platform,
                "task":          entry["task"],
            }
            key = dup_key(rec)
            if key in existing_keys:
                skipped.append(rec)
                continue
            rec["id"] = f"{BENCHMARK_ID}-{platform}-{next_num:04d}"
            next_num += 1
            existing_keys.add(key)
            new_records.append(rec)

    final_custom = kept_custom + new_records
    all_records  = base + final_custom
    out_chunks   = list(chunked(all_records, CHUNK_SIZE))

    # ── report ────────────────────────────────────────────────────────────────
    if args.reset:
        mode_label = "RESET (wipe custom, then rebuild)"
    elif args.delete_all:
        mode_label = "DELETE-ALL (wipe custom)"
    else:
        mode_label = "APPEND (add new, non-duplicate)"

    print(f"Definitions dir : {DEF_DIR}")
    print(f"Mode            : {mode_label}{'  [DRY RUN]' if args.dry_run else ''}")
    print(f"Base records    : {len(base)}")
    print(f"Custom before   : {len(custom)}  ->  kept: {len(kept_custom)}, "
          f"new: {len(new_records)}, skipped dups: {len(skipped)}")
    print(f"Total records   : {len(all_records)}  ->  {len(out_chunks)} chunk(s) of <= {CHUNK_SIZE}\n")

    for rec in new_records:
        print(f"  + {rec['id']}  [{rec['app']}]  {rec['task']}")
    for rec in skipped:
        print(f"  = dup [{rec['platform_type']}] {rec['task']}")
    if new_records or skipped:
        print()

    if args.dry_run:
        print("(dry run — no files were modified)")
        return

    # ── write ─────────────────────────────────────────────────────────────────
    for d in (JSONL_DIR, JSON_DIR, CSV_DIR):
        d.mkdir(parents=True, exist_ok=True)

    for i, chunk in enumerate(out_chunks, start=1):
        save_jsonl(chunk, JSONL_DIR / f"{CHUNK_PREFIX}{i}.jsonl")
        save_json(chunk,  JSON_DIR  / f"{CHUNK_PREFIX}{i}.json")
        save_csv(chunk,   CSV_DIR   / f"{CHUNK_PREFIX}{i}.csv")

    # Remove stale chunk files left over from a larger previous layout.
    n = len(out_chunks)
    for directory, ext in ((JSONL_DIR, "jsonl"), (JSON_DIR, "json"), (CSV_DIR, "csv")):
        for idx, path in numeric_chunks(directory, ext):
            if idx > n:
                path.unlink()
                print(f"  removed stale {path.relative_to(BASE_DIR)}")

    print(f"Written: {n} chunk(s) across jsonl/, json/, csv/.")


if __name__ == "__main__":
    main()
