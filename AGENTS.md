# AGENTS.md

Guidance for AI coding agents working on herdr-herder.

## Project overview

herdr-herder is a [herdr](https://herdr.dev) terminal plugin ("herder") that
adds pane/tab organization verbs herdr's core doesn't have yet:

- `herder.organize` — one popup picker (fzf) with two modes: "move pane to..."
  (default) and "move tab to..." (Tab toggles). Enter executes, Esc aborts.
- `herder.even` — evens pane widths at 50/50 per split (tmux even semantics).

There is **no build step and no dependency manager**: everything is plain
scripts shipped as-is.

## Repo layout

- `herdr-plugin.toml` — plugin manifest: id, version, actions, popup pane.
  The `version` here is the **source of truth** for releases.
- `bin/open.sh` — action entrypoint; opens the picker popup, forwarding
  invoking pane/tab/workspace ids via `HERDER_SRC_*` env vars.
- `bin/picker.py` — interactive picker (Python 3 stdlib only); talks to herdr
  over its Unix socket (`HERDR_SOCKET_PATH`) and via the `herdr` CLI.
- `bin/even-panes` — even-widths script (Python 3 stdlib only); `-n/--dry-run`
  prints the plan without applying it.
- `tests/test-even-panes.sh` — fixture tests for `even-panes` plan logic.
- `CHANGELOG.md` — release record (Keep-a-Changelog-ish style).

## Commands

Run tests (hermetic — uses a stub `herdr` and dry-runs only; never touches a
live herdr server):

```bash
tests/test-even-panes.sh
```

Exit code equals the number of failures; expect 0. Run this before committing
any change to `bin/` or `tests/`.

Manual smoke test of the picker/even-panes requires a live herdr session —
do not run live herdr commands from an agent; ask the user to verify.

## Conventions

- **Scripts:** `bin/open.sh` is POSIX `sh`; `bin/picker.py` and
  `bin/even-panes` are Python 3 **stdlib only** (json, os, socket,
  subprocess, sys, tempfile). No third-party packages.
- **Python style:** compact, comment-heavy, module docstring explaining
  behavior. Keep that style; update docstrings when behavior changes
  (a stale docstring was a real past bug — see 0.6.1).
- **Versioning:** semver with 0.x conventions — features bump the minor,
  fixes bump the patch. Every user-visible change bumps
  `herdr-plugin.toml` `version` **and** adds a `CHANGELOG.md` entry.
- **Actions/manifest:** action ids are `even` and `organize`; full command
  ids are `shrwnsan.herder.<id>`. Keep contexts, popup placement, and
  `min_herdr_version` accurate when touching the manifest.
- **Safety in scripts:** `even-panes` mutations must stay reachable only via
  explicit apply paths; keep `-n`/`--dry-run` honored in any argument
  position and keep empty pane-id args falling back to the focused pane.
  Tests assert both — don't regress them.
- **Docs:** README is user-facing (install, bindings); put agent/dev-facing
  detail here. Update README if user-visible behavior or bindings change.
- Platform targets: linux and macos (`platforms` in the manifest). Avoid
  bashisms in `open.sh`; avoid non-portable Python.
