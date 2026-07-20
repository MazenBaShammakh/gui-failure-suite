# Custom Tasks

Define your own GUIFailureSuite tasks here and patch them into the suite.

You supply only `task` + `platform` (optionally `app`); `build_custom_tasks.py`
fills in the constant schema fields and an auto-incrementing id, then **appends**
the records into the existing `gui_suite_<N>` chunks under `../csv`, `../json`,
and `../jsonl`, re-packing into chunks of up to **1,000 records** each (new
chunks are created as needed).

## Define tasks

Edit `tasks.yaml` (or add any other `*.yaml` / `*.yml` / `*.json` file in this
folder — they are all read, sorted by name; `*.example.*` files are ignored).

Grouped by platform:

```yaml
web:
  - task: Log in with a valid email and password.
mobile:
  - task: Add the first item to favorites.
    app: com.mazenbashammakh.mobile.dev   # optional per-task override
desktop_windows:
  - task: Open the Settings window.
```

…or a flat list (each entry carries its own `platform`):

```yaml
- platform: web
  task: Log in with a valid email and password.
- platform: desktop_windows
  task: Open the Settings window.
```

## Build

```bash
python build_custom_tasks.py              # append new (non-duplicate) tasks
python build_custom_tasks.py --reset      # wipe all custom tasks, then rebuild
python build_custom_tasks.py --delete-all # wipe all custom tasks, add nothing
python build_custom_tasks.py --dry-run    # preview, write nothing
```

- **Append (default):** adds only tasks that aren't already in the suite.
- **`--reset`:** removes every existing custom task, then rebuilds from the
  current definitions (ids are reassigned from the base-suite max, e.g. `2694`).
  Use this when you've changed/reordered tasks and want a clean rebuild.
- **`--delete-all`:** removes every custom task and adds nothing, restoring the
  suite to just its source-benchmark records.

### Idempotency & de-duplication

Re-running never duplicates work. A task is a **duplicate** when its
`(task, app, platform_type)` combination already exists in the suite, and
duplicates are skipped. The source-benchmark chunks (`gui_suite_1`, `gui_suite_2`,
…) are reproduced byte-for-byte; only the tail chunks that hold custom tasks
change.

## Generated record

| Field           | Value                                                                |
| --------------- | -------------------------------------------------------------------- |
| `id`            | `gui-failure-suite-<platform>-<NNNN>` (global counter, continues after the suite max) |
| `benchmark_id`  | `gui-failure-suite`                                                  |
| `benchmark`     | `GUIFailureSuite`                                                    |
| `split`         | `test`                                                               |
| `platform_type` | `<platform>` (`web` / `mobile` / `desktop_windows`)                 |
| `app`           | per-task override, else the platform default below                   |
| `task`          | your task text                                                       |

### Platforms & default `app`

| Platform          | Default `app`                | Environment                         |
| ----------------- | ---------------------------- | ----------------------------------- |
| `web`             | `http://localhost:3000`      | localhost web app                   |
| `mobile`          | `com.mazenbashammakh.mobile` | Expo React Native app, Android emu  |
| `desktop_windows` | `desktop.exe`                | WPF desktop app                     |

`desktop` is accepted as an alias for `desktop_windows`.

The custom records follow the same schema as the rest of the suite, so
`preprocessing/update_apps.py` (which globs `*.jsonl`) picks them up
automatically.
