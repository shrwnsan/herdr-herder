#!/bin/sh
# herder action entry — open the unified picker popup, forwarding context.
exec "${HERDR_BIN_PATH:-herdr}" plugin pane open --plugin shrwnsan.herder \
  --entrypoint organize --placement popup \
  --env "HERDER_SRC_PANE=$HERDR_PANE_ID" \
  --env "HERDER_SRC_TAB=$HERDR_TAB_ID" \
  --env "HERDER_SRC_WS=$HERDR_WORKSPACE_ID"
