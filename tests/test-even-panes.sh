#!/usr/bin/env bash
# Fixture tests for bin/even-panes's plan logic, run against a stub `herdr` on PATH.
# Hermetic: every success-path run is dry-run and HERDR_SOCKET_PATH points
# nowhere, so a live herdr server is never touched.
# Usage: test-even-panes.sh
# Exit code: number of failures.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PICK="$ROOT/bin/even-panes"

PASS=0
FAIL=0

report() { # desc expected actual
  if [ "$2" = "$3" ]; then
    PASS=$(( PASS + 1 ))
  else
    FAIL=$(( FAIL + 1 ))
    echo "FAIL: $1"
    printf '  expected: %q\n  actual:   %q\n' "$2" "$3"
  fi
}

assert_contains() { # desc needle haystack
  case "$3" in
    *"$2"*) PASS=$(( PASS + 1 )) ;;
    *) FAIL=$(( FAIL + 1 )); echo "FAIL: $1 — missing: $2" ;;
  esac
}

assert_not_contains() { # desc needle haystack
  case "$3" in
    *"$2"*) FAIL=$(( FAIL + 1 )); echo "FAIL: $1 — unexpectedly present: $2" ;;
    *) PASS=$(( PASS + 1 )) ;;
  esac
}

# --- stub herdr: serves canned JSON, never touches a real socket -----------

STUB_DIR="$(mktemp -d)"
trap 'rm -rf "$STUB_DIR"' EXIT

cat > "$STUB_DIR/herdr" <<'EOF'
#!/usr/bin/env bash
case "$1 $2" in
  "pane layout") printf '%s' "$STUB_LAYOUT" ;;
  "pane list")   printf '%s' "$STUB_LIST" ;;
  *) echo "stub herdr: unexpected call: $*" >&2; exit 3 ;;
esac
EOF
chmod +x "$STUB_DIR/herdr"

run_even() { # layout_json list_json even-panes_args...
  export STUB_LAYOUT="$1" STUB_LIST="$2" HERDR_SOCKET_PATH="$STUB_DIR/no.sock"
  PATH="$STUB_DIR:$PATH" OUT="$(python3 "$PICK" "${@:3}" 2>&1)"
  RC=$?
}

# --- fixture builders ------------------------------------------------------

pane() { # id focused x y w h
  printf '{"pane_id":"%s","focused":%s,"rect":{"x":%s,"y":%s,"width":%s,"height":%s}}' \
    "$1" "$2" "$3" "$4" "$5" "$6"
}

split() { # id direction ratio
  printf '{"id":"%s","direction":"%s","ratio":%s,"rect":{"x":0,"y":0,"width":200,"height":100}}' \
    "$1" "$2" "$3"
}

layout() { # tab_id zoomed panes_joined splits_joined
  printf '{"id":"stub","result":{"layout":{"tab_id":"%s","zoomed":%s,"area":{"x":0,"y":0,"width":200,"height":100},"panes":[%s],"splits":[%s]}}}' \
    "$1" "$2" "$3" "$4"
}

plist() { # panes — first one is focused
  local out="" p
  for p in "$@"; do
    out+="${out:+,}{\"pane_id\":\"$p\",\"focused\":$([ "$p" = "$1" ] && echo true || echo false)}"
  done
  printf '{"id":"stub","result":{"panes":[%s]}}' "$out"
}

# --- 1. mixed tree: leaf-share root ratio is re-planned to 50/50 -----------

L1=$(layout tA false \
  "$(pane pL true 0 0 67 100),$(pane pT false 67 0 133 50),$(pane pB false 67 50 133 50)" \
  "$(split split_0_root right 0.335),$(split split_1_1 down 0.5)")
run_even "$L1" "$(plist pL)" -n pL
report "mixed tree exits cleanly" 0 "$RC"
assert_contains "leaf-share root re-planned to 50/50" "split_0_root: ratio 0.335 -> 0.500" "$OUT"
assert_not_contains "already-50/50 nested split untouched" "split_1_1: ratio" "$OUT"
assert_contains "dry-run notice present" "(dry-run" "$OUT"
assert_not_contains "no geometry-after in dry-run" "geometry after" "$OUT"

# --- 2. flat row of 3 as nested 50/50 splits: already even (½/¼/¼) ---------

L2=$(layout tB false \
  "$(pane p1 true 0 0 100 100),$(pane p2 false 100 0 50 50),$(pane p3 false 100 50 50 50)" \
  "$(split split_0_root right 0.5),$(split split_1_1 down 0.5)")
run_even "$L2" "$(plist p1)" -n p1
report "nested 50/50 row exits cleanly" 0 "$RC"
assert_contains "flat 3-row already even under 50/50 semantics" "already even" "$OUT"
assert_not_contains "no plan lines for even tree" "ratio" "$OUT"

# --- 3. empty pane-id arg falls back to the focused pane --------------------
# (the prefix+e binding sends "" when HERDR_ACTIVE_PANE_ID is unset)

run_even "$L2" "$(plist p1)" -n ""
report "empty arg falls back to focused pane" 0 "$RC"
assert_contains "resolved focused pane via pane list" "already even" "$OUT"

# --- 4. -n after the pane id still means dry-run ----------------------------
# (a positional-only DRY check would reach the socket and apply changes)

L4=$(layout tD false \
  "$(pane p1 true 0 0 80 100),$(pane p2 false 80 0 120 100)" \
  "$(split split_0_root right 0.4)")
run_even "$L4" "$(plist p1)" p1 -n
report "flag after pane id exits cleanly" 0 "$RC"
assert_contains "trailing -n honored as dry-run" "(dry-run" "$OUT"
assert_contains "uneven root planned" "split_0_root: ratio 0.400 -> 0.500" "$OUT"

# --- 5. zoomed tab refuses ---------------------------------------------------

L5=$(layout tE true \
  "$(pane p1 true 0 0 200 100),$(pane p2 false 0 0 200 100)" \
  "$(split split_0_root right 0.4)")
run_even "$L5" "$(plist p1)" -n p1
report "zoomed tab exits non-zero" 1 "$RC"
assert_contains "zoomed message" "tab is zoomed" "$OUT"

# --- 6. tree mismatch refuses ------------------------------------------------

L6=$(layout tF false \
  "$(pane p1 true 0 0 100 100),$(pane p2 false 100 0 100 100)" \
  "$(split split_0_root right 0.5),$(split split_1_0 down 0.5)")
run_even "$L6" "$(plist p1)" -n p1
report "tree mismatch exits non-zero" 1 "$RC"
assert_contains "mismatch message" "tree mismatch" "$OUT"

# --- 7. single pane: nothing to even -----------------------------------------

L7=$(layout tG false "$(pane p1 true 0 0 200 100)" "")
run_even "$L7" "$(plist p1)" -n p1
report "single pane exits 0" 0 "$RC"
assert_contains "nothing-to-even message" "nothing to even" "$OUT"

# --- summary -----------------------------------------------------------------

echo "even-panes: $PASS passed, $FAIL failed"
exit "$FAIL"
