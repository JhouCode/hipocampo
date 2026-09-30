#!/usr/bin/env bash
#
# mapa-orcamento-hook.sh — the MAP BUDGET reported ON TOUCH, not at commit.
#
# The case: three new clauses in layer 1 pushed the load to 6 slices and only the COMMIT guard
# caught it — tokens burned writing what the revolving door would then order to shrink.
# The front ruler comes BEFORE: PostToolUse on Edit|Write; if the touched file lives in
# docs/mapa/, it runs THE SAME computation as the guard (the mapa-hook selftest) and returns the
# budget as context. A single instrument — no second truth about slices.
. "$(dirname "${BASH_SOURCE[0]}")/hipo-config.sh"

f=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)
case "$f" in
  */docs/mapa/*) : ;;
  *) exit 0 ;;
esac

saida=$(bash "$HIPO_REPO/scripts/mapa-hook.sh" --selftest 2>&1 \
        | grep -E 'initial load|slice|BUDGET|measured pace' | head -6)
[ -n "$saida" ] || exit 0

if printf '%s' "$saida" | grep -q '✗'; then
  pre="🚨 [map-budget] OVER on touch — revolving door NOW (for something to enter, something LEAVES; docs/mapa/5_COMO_MANTER.md §5):"
else
  pre="📏 [map-budget] after this touch:"
fi

jq -cn --arg ctx "$pre
$saida" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$ctx}}'
