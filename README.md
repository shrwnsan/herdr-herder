# herdr-herder 🐕

> **herder** — one who herds. A [herdr](https://herdr.dev) plugin that moves your herd of panes.

One picker, two moves:

- **`prefix+o`** (herder.organize) opens a popup: **move pane to...** by default;
  **Tab** flips to **move tab to...**; Enter executes, Esc aborts.
- **`herder.even`** evens pane widths to equal columns and rows (tmux
  `even-horizontal`/`even-vertical` semantics generalized to mixed trees:
  2 panes → 50/50, 3 flat → thirds, 4 → quarters, stacked columns keep equal
  column widths with 50/50 rows — no lone-pane slivers), via the bundled
  `even-panes` script — bind it to a chord or call it directly.

Works alongside herdr's built-ins: navigation stays `prefix+g`, same-tab swaps
stay `prefix+shift+h/j/k/l`, manual resize stays `prefix+r`. Herder owns the
verbs core doesn't have yet.

## Install

```bash
herdr plugin install shrwnsan/herdr-herder
```

Then bind (in herdr's `config.toml`):

```toml
[[keys.command]]
key = "prefix+o"
type = "plugin_action"
command = "shrwnsan.herder.organize"
description = "herder: move pane/tab to..."

[[keys.command]]
key = "prefix+e"
type = "plugin_action"
command = "shrwnsan.herder.even"
description = "even pane widths in this tab"
```

Requires: herdr >= 0.8.0, `fzf`, `jq`, `python3` on PATH.

## Versioning

Semver, 0.x conventions; the manifest `version` is the source of truth and
[CHANGELOG.md](CHANGELOG.md) is the record. `herder.even` sunsets when an
upstream `even_panes` core action exists.

## License

MIT
