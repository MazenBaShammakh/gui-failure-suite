---
configs:
  - config_name: default
    data_files:
      - split: test
        path: jsonl/*.jsonl
---

# GUI Failure Analysis — Task Suite

Consolidated benchmark suite of **2,821 GUI agent tasks** spanning mobile, web, and desktop platforms. Duplicate tasks across benchmarks have been removed. Includes 128 hand-authored custom tasks (`GUIFailureSuite` benchmark) on top of the 2,693 source-benchmark tasks.

---

## Getting started

The suite is data only — there's no code to run, just files to load. It
ships as three parallel, always-in-sync serializations of the same 2,821
records (`csv/`, `json/`, `jsonl/`), split into the three chunks below;
concatenate them for the full set.

Load the full suite with pandas:

```python
import pandas as pd
import glob

df = pd.concat(pd.read_csv(f) for f in sorted(glob.glob("csv/gui_suite_*.csv")))
print(len(df))  # 2821
```

Or line-by-line from the JSONL chunks:

```python
import json
from pathlib import Path

records = []
for chunk in sorted(Path("jsonl").glob("gui_suite_*.jsonl")):
    with open(chunk, encoding="utf-8") as f:
        records.extend(json.loads(line) for line in f)
```

---

## Files

The suite is distributed across **3 chunks of up to 1,000 records** each, available in three formats:

| File          | Records | ID range                                             |
| ------------- | ------- | ---------------------------------------------------- |
| `gui_suite_1` | 1,000   | `aitw-mobile-0001` → `mind2web-web-1000`             |
| `gui_suite_2` | 1,000   | `mind2web-web-1001` → `mind2web-web-2000`            |
| `gui_suite_3` | 821     | `mind2web-web-2001` → `gui-failure-suite-mobile-2821` |

Each chunk exists in three formats under the corresponding subdirectory: `json/`, `jsonl/`, and `csv/`.

---

## Record schema

| Field           | Type           | Description                                                             |
| --------------- | -------------- | ----------------------------------------------------------------------- |
| `id`            | string         | Unique task ID — `{benchmark}-{platform}-{XXXX}` (4-digit counter)      |
| `benchmark_id`  | string         | Sub-split identifier within the source benchmark                        |
| `benchmark`     | string         | Source benchmark name                                                   |
| `split`         | string         | Dataset split (always `test`)                                           |
| `app`           | string \| null | Target software application or website; `null` for AITW (not annotated) |
| `platform_type` | string         | Platform: `mobile`, `web`, `desktop`, or `desktop_windows`              |
| `task`          | string         | Natural-language task instruction                                       |

---

## The `app` field

`app` is a machine-launchable identifier for the task's target, in one of
four formats depending on `platform_type`. Multi-app entries are
comma-separated with the primary app first (e.g.
`"com.android.chrome, com.google.android.googlequicksearchbox"`); a
consuming harness should open the first one, falling back to the next if it
fails to launch. `app` is `null` only for AITW mobile tasks, where the source
benchmark doesn't annotate a target app.

| `platform_type`   | `app` format                | Example                                                    |
| ------------------ | ---------------------------- | ------------------------------------------------------------ |
| `web`               | HTTPS URL                     | `https://www.seatgeek.com`                                    |
| `mobile`            | Android package name           | `com.google.android.apps.tasks`                                 |
| `desktop`           | Linux shell command              | `libreoffice --calc`                                              |
| `desktop_windows`   | Windows executable path/command    | `C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE`          |

---

## Composition

### By benchmark

| Benchmark  |     Tasks | Platform                  | `app` field                      |
| ---------- | --------: | ------------------------- | -------------------------------- |
| AITW       |       497 | mobile                    | `null` (not available in source) |
| LlamaTouch |       477 | mobile                    | app name string                  |
| Mind2Web   |     1,341 | web                       | website name string              |
| OSWorld    |       378 | desktop / desktop_windows | app name(s), comma-separated     |
| GUIFailureSuite |    128 | mobile / web / desktop_windows | app/package name, default per platform |
| **Total**  | **2,821** |                           |                                  |

### By platform

| Platform        | Tasks |
| --------------- | ----: |
| mobile          | 1,064 |
| web             | 1,375 |
| desktop         |   358 |
| desktop_windows |    24 |

---

## Source datasets

| Benchmark  | Full name           | Platform                  | Reference                                                                         |
| ---------- | ------------------- | ------------------------- | --------------------------------------------------------------------------------- |
| AITW       | Android in the Wild | mobile                    | He et al., 2023 — [arxiv.org/abs/2307.10088](https://arxiv.org/abs/2307.10088)    |
| LlamaTouch | LlamaTouch          | mobile                    | Zhang et al., 2024 — [arxiv.org/abs/2404.16054](https://arxiv.org/abs/2404.16054) |
| Mind2Web   | Mind2Web            | web                       | Deng et al., 2023 — [arxiv.org/abs/2306.06070](https://arxiv.org/abs/2306.06070)  |
| OSWorld    | OSWorld             | desktop (Linux & Windows) | Xie et al., 2024 — [arxiv.org/abs/2404.07972](https://arxiv.org/abs/2404.07972)   |
| GUIFailureSuite | GUI Failure Suite (custom) | mobile / web / desktop_windows | Hand-authored tasks targeting known GUI failure modes |

---

## License & attribution

This suite is a derivative aggregation of four external benchmarks — AITW,
LlamaTouch, Mind2Web, and OSWorld — deduplicated and normalized to a common
schema, plus 128 hand-authored tasks. It is provided as-is for research use;
consult each source benchmark's own license and terms (linked above) before
redistributing tasks drawn from it. If you use this suite, please also credit
the original benchmark authors for any tasks sourced from their work.
