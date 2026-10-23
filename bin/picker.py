#!/usr/bin/env python3
"""herder picker — one popup, two modes.

Default mode: move pane to... (the frequent micro-action).
Tab flips between "move pane to..." and "move tab to...".
Enter executes; Esc aborts.
"""
import json, os, socket, subprocess, sys, tempfile

HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")
SOCK = os.environ.get("HERDR_SOCKET_PATH",
                      os.path.expanduser("~/.config/herdr/herdr.sock"))

def rpc(method, params):
    req = json.dumps({"id": "herder", "method": method, "params": params}) + "\n"
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.settimeout(5)
    s.connect(SOCK)
    s.sendall(req.encode())
    resp = json.loads(s.recv(1 << 20).decode().splitlines()[0])
    s.close()
    if "error" in resp:
        raise RuntimeError(f"{method}: {resp['error']}")
    return resp.get("result", {})

def cli(*args):
    return subprocess.run([HERDR, *args], capture_output=True, text=True)

def cli_json(*args):
    try:
        return json.loads(cli(*args).stdout).get("result", {})
    except Exception:
        return {}

# --- context (forwarded by the opener; fallbacks for direct runs)
src_pane = os.environ.get("HERDER_SRC_PANE") or os.environ.get("HERDR_PANE_ID")
src_tab = os.environ.get("HERDER_SRC_TAB") or os.environ.get("HERDR_TAB_ID")
src_ws = os.environ.get("HERDER_SRC_WS") or os.environ.get("HERDR_WORKSPACE_ID")
if not src_tab and not src_pane:
    pane = cli_json("pane", "current").get("pane", {})
    src_pane, src_tab, src_ws = (pane.get("pane_id"), pane.get("tab_id"),
                                 pane.get("workspace_id"))
if src_pane and not src_tab:
    src_tab = cli_json("pane", "get", src_pane).get("pane", {}).get("tab_id")
if src_tab and not src_ws:
    src_ws = cli_json("tab", "get", src_tab).get("tab", {}).get("workspace_id")

ws_labels = {w["workspace_id"]: (w.get("label") or w["workspace_id"])
             for w in cli_json("workspace", "list").get("workspaces", [])}

def rows(mode):
    out = []
    if mode == "pane":
        for t in cli_json("tab", "list").get("tabs", []):
            if t["tab_id"] == src_tab:
                continue
            lbl = ws_labels.get(t["workspace_id"], t["workspace_id"])
            out.append(f"tab\t{t['tab_id']}\t"
                       f"{lbl} › {t.get('label') or t['tab_id']} "
                       f"(#{t.get('number')}, {t.get('pane_count')} pane(s))")
        out.append("new-tab\t-\tmove to a brand-new tab in this workspace")
    else:
        for wid, lbl in ws_labels.items():
            if wid == src_ws:
                continue
            out.append(f"workspace\t{wid}\t{lbl}")
    out.append("new-workspace\t-\tmove to a brand-new workspace")
    return out

def pick(mode, rws):
    """Run fzf; returns (flipped, selection) — flipped=True means Tab pressed."""
    hdr = (f"move pane {src_pane or ''} to... · Tab: move tab instead · Enter: move"
           if mode == "pane" else
           f"move tab {src_tab or ''} to... · Tab: move pane instead · Enter: move")
    with tempfile.NamedTemporaryFile("w", delete=False) as rf:
        rf.write("\n".join(rws) + "\n"); rp = rf.name
    sp = rp + ".sel"
    r = subprocess.run(
        ["sh", "-c",
         f'fzf --header "{hdr}" --delimiter "\\t" --with-nth 3 --no-sort '
         f'--expect tab < "{rp}" > "{sp}"'])
    lines = open(sp).read().splitlines() if os.path.exists(sp) else []
    os.unlink(rp)
    if os.path.exists(sp):
        os.unlink(sp)
    if r.returncode != 0 or len(lines) < 2:
        sys.exit(0)
    return lines[0] == "tab", lines[1]

# --- selection (headless hook: HERDER_DEST + HERDER_MODE bypass the picker)
mode = os.environ.get("HERDER_MODE", "pane")
dest = os.environ.get("HERDER_DEST")
if not dest:
    while True:
        flipped, dest = pick(mode, rows(mode))
        if not flipped:
            break
        mode = "tab" if mode == "pane" else "pane"

kind, _, rest = dest.partition("\t")

# --- pane mode: move the pane
if mode == "pane":
    if not src_pane:
        sys.exit("herder: no source pane")
    if kind == "new-tab":
        cli("pane", "move", src_pane, "--new-tab")
    elif kind == "new-workspace":
        cli("pane", "move", src_pane, "--new-workspace")
    elif kind == "tab":
        cli("pane", "move", src_pane, "--tab", rest.split("\t")[0],
            "--split", "right", "--ratio", "0.5")
    sys.exit(0)

# --- tab mode: move the whole tab (all panes)
if not src_tab:
    sys.exit("herder: no source tab")
dest_tab = new_ws = root_pane = None
if kind == "new-workspace":
    # herdr races observed live: a fresh workspace's auto root shell can die
    # within ~100ms, auto-closing the empty workspace and destroying panes
    # from in-flight moves. Never move into an unverified destination.
    import time
    stable = False
    for _ in range(3):
        res = rpc("workspace.create", {})
        new_ws = res["workspace"]["workspace_id"]
        dest_tab = res["tab"]["tab_id"]
        root_pane = res.get("root_pane", {}).get("pane_id")
        stable = True
        for _ in range(3):
            time.sleep(0.15)
            still = [w["workspace_id"] for w in
                     cli_json("workspace", "list").get("workspaces", [])]
            if new_ws not in still:
                stable = False
                break
        if stable:
            break
    if not stable:
        sys.exit("herder: new workspace kept auto-closing — aborted before "
                 "moving anything; nothing was lost. Try again.")
elif kind == "workspace":
    dest_ws = rest.split("\t")[0]
    created = cli_json("tab", "create", "--workspace", dest_ws,
                       "--label", "moved")
    dest_tab = created.get("tab", {}).get("tab_id")
    # tab.create also spawns a root shell pane — evict it like the
    # new-workspace auto shell
    root_pane = created.get("root_pane", {}).get("pane_id")
    if not dest_tab:
        sys.exit("herder: tab create failed")
else:
    sys.exit(0)

# capture the label before the move — the source tab auto-closes once emptied
label = (cli_json("tab", "get", src_tab).get("tab", {}) or {}).get("label") or "moved"

panes = [p for p in cli_json("pane", "list").get("panes", [])
         if p["tab_id"] == src_tab]
if not panes:
    if new_ws:
        rpc("workspace.close", {"workspace_id": new_ws})
    sys.exit(f"herder: tab {src_tab} has no panes — nothing to move")

for p in panes:
    rpc("pane.move", {"pane_id": p["pane_id"],
                      "destination": {"type": "tab", "tab_id": dest_tab,
                                      "split": "right", "ratio": 0.5},
                      "focus": False})

# Evict the destination's auto shell and verify the outcome. Pane ids are
# workspace-scoped — moved panes get NEW ids in the destination — so verify
# by membership count in the destination tab, never by source ids.
post = [q for q in cli_json("pane", "list").get("panes", [])
        if q["tab_id"] == dest_tab]
if root_pane and len(post) > len(panes):
    # (evict the auto root shell — fresh tab/workspace path)
    try:
        rpc("pane.close", {"pane_id": root_pane})
    except RuntimeError as e:
        print(f"herder: (shell evict failed: {e})")
post = [q for q in cli_json("pane", "list").get("panes", [])
        if q["tab_id"] == dest_tab]
if len(post) != len(panes):
    print(f"herder: WARNING — expected {len(panes)} panes in {dest_tab}, "
          f"found {len(post)}; check pane/workspace lists.")
    sys.exit(1)

if new_ws:
    try:
        rpc("workspace.rename", {"workspace_id": new_ws, "label": label})
    except RuntimeError as e:
        print(f"herder: (rename skipped: {e})")
cli("tab", "focus", dest_tab)
print(f"herder: moved {len(panes)} pane(s) of {src_tab} -> {dest_tab}")
