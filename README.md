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
