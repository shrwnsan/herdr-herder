# RESEARCH-001: Grid mode via `layout.apply` — spike findings

- **Date:** 2026-10-29
- **Status:** Concluded — no-go for live-pane reshaping; findings recorded to prevent re-trying
- **Scope:** herdr `layout.apply` / `layout.export` socket RPC (protocol 22), herdr ≥ 0.8.0
- **Method:** Sacrificial tabs in a scratch workspace (`wQ`), dummy `sleep 600` panes,
  `layout.export` snapshot before each apply, bisected probes (1-pane, then exact-matching
  2-pane trees). Backups preserved at `/tmp/grid-spike/backup*.json` (ephemeral).

## Motivation

`herder.even` (0.7.0) only tweaks split **ratios** (`layout.set_split_ratio`), so it can
never change the tree's *shape*: a `down` split stays `down`, deep nesting produces
sliver panes (observed 22x7 cells at 17 panes), and a side-by-side pair inside one
column can never be promoted to top-level columns. A `--grid N` mode would rebuild the
tab as a canonical N-column grid. `layout.apply` is the only RPC that accepts an
arbitrary tree — this spike tested whether it re-parents live panes.

## Findings

| # | Question | Result |
|---|----------|--------|
| 1 | Does `layout.apply` reuse `pane_id`? | **No.** Even with an exact matching tree (same pane ids, same count), all panes came back with brand-new ids (`wQ:pD,pE` → `wQ:pF,pG`). The `pane_id` field on a `pane` leaf is effectively ignored at spawn time. |
| 2 | Do pane processes survive? | **No.** All `sleep 600` processes died in both probes. Apply recreates panes from the leaf's `command`/`cwd` (or the default shell when absent). |
| 3 | Panes present in the tab but absent from the tree? | **Destroyed silently.** A 1-pane tree applied to a 6-pane tab closed the other five — no validation error, no warning. |
| 4 | `layout.export` as an undo? | Captures the tree faithfully (including per-pane `cwd`), but since apply never re-parents, "restore" also recreates panes rather than resurrecting processes. It is a template snapshot, not a state backup. |
| 5 | Tab identity | Tab id was renumbered after apply (`t2`→`t3`, `t4`→`t5`). |
| 6 | Error surface | Shape errors surface as `invalid_request` (e.g. wrong node types); a stale `tab_id` returns `tab_not_found`. Neither guards against the destructive behaviors in 1–3. |

## Conclusion

`layout.apply` is a **template spawner, not a re-arranger**. It is suitable for
bootstrapping a fresh workspace layout from a definition file; it is unsuitable for
`--grid N` on a tab with running agents, because every pane is recreated and every
process killed.

## Alternative path (not built)

The non-destructive route to grid reshaping is the existing pane verbs:
`herdr pane move <pane_id> --split right|down --target-pane <id> --ratio <f>`
re-parents a live pane without touching its process. A grid mode could walk panes in
order and move each into position. Deferred: 0.7.0's ratio-equalizer already covers the
fairness job; shape rebuilds are aesthetics and can wait for real sliver pain.

## Reproduction sketch

```python
# 1. snapshot
rpc({"id":"x","method":"layout.export","params":{"tab_id":"<TAB>"}})
# 2. apply — note: panes recreated, processes killed, missing panes closed
rpc({"id":"x","method":"layout.apply",
     "params":{"tab_id":"<TAB>",
               "root":{"type":"split","direction":"down","ratio":0.5,
                       "first":{"type":"pane","pane_id":"<EXISTING_ID>"},
                       "second":{"type":"pane","pane_id":"<EXISTING_ID>"}}}})
# 3. observe: herdr pane list → all-new pane ids; processes gone
```
