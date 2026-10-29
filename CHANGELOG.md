# herder changelog

Versioning: semver, 0.x conventions — features bump the minor, fixes bump the
patch, behavior/binding changes are called out explicitly. The manifest's
`version` is the source of truth; this file is the record.

## 0.7.0 — 2026-10-23
### Changed
- **`herder.even` even rule rewritten: equal columns/rows** (tmux
  `even-horizontal`/`even-vertical` semantics, generalized to mixed binary
  trees). A right-split now targets its first child's *column* share; a
  down-split targets its first child's *row* share. Consequences per shape:
  - 2 vertical → 50/50 (unchanged)
  - 3 flat panes → exact thirds (was ½/¼/¼ under the old per-split 50/50 rule)
  - 4 flat panes / 4 rows → quarters (was ½/¼/⅛ chains)
  - tall pane + 2 stacked → 50/50 columns with 50/50 rows (unchanged — no
    lone-pane 1/N slivers, the original design goal)
  - mixed trees → equal column widths, equal row heights within columns
- `herdr-plugin.toml` action title updated to match.
### Tests
- Fixture suite extended to 28 cases: flat-row thirds, 4-flat, 4-rows,
  stacked-column no-sliver, and the corrected first-child-share expectations.

## 0.6.1 — 2026-10-23
### Fixed
- Bundled `even-panes`: `-n`/`--dry-run` is now honored in any argument position —
  `even-panes <pane> -n` previously filtered the flag but still applied changes
  live. Empty pane-id args (unset `HERDR_ACTIVE_PANE_ID` in a shell binding)
  fall back to the focused pane instead of dying with a confusing
  `pane layout failed`.
- Bundled `even-panes` docstring documented the retired leaf-share even rule; now
  describes the shipped 50/50-per-split rule (flat rows nest to ½/¼/¼).

### Added
- `tests/test-even-panes.sh` — 19-case stub-`herdr` fixture suite for the plan
  logic and arg handling (hermetic: dry-run only, `HERDR_SOCKET_PATH` points
  nowhere).

## 0.6.0 — 2026-10-23
### Added
- Extracted to its own repo (`herdr-herder`). First tagged release.
- even-panes (even pane widths, 50/50 per split) ships as `herder.even` for
  portability; retires when an upstream `even_panes` core action lands
  (shrwnsan/herdr issue #1). Hosts already binding `prefix+e` directly to
  even-panes via `type = "shell"` can keep that binding unchanged.

## 0.5.3 — 2026-10-23
### Fixed
- Existing-workspace tab moves: `tab.create` also spawns a root shell pane —
  evict it like the new-workspace auto shell (verify caught it: destination
  tab counted one extra pane).

## 0.5.2 — 2026-10-23
### Fixed
- New-workspace tab moves: evict the auto shell and verify by **destination
  membership count** — pane ids are workspace-scoped, so matching moved panes
  by their source ids misclassified them as strays and closed them (caught in
  3/3 headless regressions; the earlier silent-CLI-close fix had introduced it).
- Stability gate before moving into a fresh workspace (observed live: a fresh
  workspace's auto root shell can die within ~100ms, auto-closing the space
  and destroying in-flight moves). Aborts with nothing lost if it collapses.

## 0.5.1 — 2026-10-22
### Fixed
- Capture the source tab's label before moving panes; the emptied source tab
  auto-closes and the lookup fell back to "moved" for new-workspace names.

## 0.5.0 — 2026-10-22
### Changed
- **Unified picker**: `prefix+o` opens "move pane to..." by default; Tab flips
  to "move tab to..." (and back); Enter executes. `prefix+O` retired.
- picker.py replaces organize.sh + move_tab.py (superseded, in git history).

## 0.4.2 — 2026-10-22
### Fixed
- Rebuilt manifest after a scripted edit consumed a `[[panes]]` header
  (duplicate TOML key — plugin failed to load, "plugin action not found").

## 0.4.1 — 2026-10-22
### Fixed
- move_tab rewritten in Python: reliable new-workspace path (reuse auto tab,
  evict root shell, rename space), abort-before-create on empty source tabs.
- Popup fzf pattern: rows via file, UI on the pane tty, selection via stdout —
  capturing fzf's output rendered popups blank.
- Shebang restored (a debug wrapper had displaced it; panes exec'd via sh).

## 0.4.0 — 2026-10-22
### Added
- `prefix+O` — move tab to another space (composition: tab.create +
  pane.move xN; herdr has no single cross-space tab.move verb).

## 0.3.x — 2026-10-21/22
### Added / Changed
- 0.3.0 — revived as organize: move pane to tab / new tab / new workspace.
- 0.3.1 — popup opens via plugin pane open (actions run detached, no TTY);
  source pane id forwarded via --env (pane context is the popup's own).
- 0.3.2 — rows show space › tab names; verb rows pinned last (--no-sort).

## 0.2.x — 2026-10-21 (retired surface)
- 0.2.0 — identify overlay; numbered picker rows; sort cycling; rich previews.
- 0.2.1 — plugin panes/actions get HERDR_PANE_ID (HERDR_ACTIVE_PANE_ID is
  shell-binding-only) — root cause of two crash classes.

## 0.1.0 — 2026-10-21
- Initial experiment: pane-map picker (prefix+m), identify (prefix+i),
  even (prefix+shift+e). map retired (core prefix+g supersedes), identify
  retired (needs a core transient overlay; see shrwnsan/herdr issue #2).
