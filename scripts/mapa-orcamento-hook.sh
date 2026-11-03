#!/usr/bin/env bash
#
# mapa-orcamento-hook.sh — the MAP BUDGET reported ON TOUCH, not at commit.
#
# The case: three new clauses in layer 1 pushed the load to 6 slices and only the COMMIT guard
# caught it — tokens burned writing what the revolving door would then order to shrink.
# The front ruler comes BEFORE: PostToolUse on Edit|Write|Bash; if the touch changed docs/mapa/,
# it runs THE SAME computation as the guard (the mapa-hook selftest) and returns the budget as
# context. A single instrument — no second truth about slices.
#
# Bash (2026-11-03): an agent edited docs/mapa/ through a python script run from Bash; this hook
# only read tool_input.file_path, stayed silent, and the pre-commit blocked twice. On Bash the
# trigger is the EFFECT: the command mentions "mapa", the map is dirty against HEAD, and its
# content changed since this session's last warning. Reading does not warn, and the same state
# does not warn twice.
. "$(dirname "${BASH_SOURCE[0]}")/hipo-config.sh"

REPO="${MAPA_REPO:-$HIPO_REPO}"
CACHE="${MAPA_ORC_CACHE:-$HIPO_STATE_DIR/mapa-orcamento}"
MAPA_HOOK="${MAPA_HOOK:-$HIPO_REPO/scripts/mapa-hook.sh}"

_should_warn() {
  local p tool f cmd sess h st
  p=$(cat)
  tool=$(printf '%s' "$p" | jq -r '.tool_name // empty' 2>/dev/null)
  if [ "$tool" = "Bash" ]; then
    cmd=$(printf '%s' "$p" | jq -r '.tool_input.command // empty' 2>/dev/null)
    case "$cmd" in *mapa*) : ;; *) return 1 ;; esac
    git -C "$REPO" diff --quiet HEAD -- docs/mapa 2>/dev/null && return 1
    h=$(cat "$REPO"/docs/mapa/*.md 2>/dev/null | cksum | cut -d' ' -f1)
    sess=$(printf '%s' "$p" | jq -r '.session_id // "no-session"' 2>/dev/null)
    mkdir -p "$CACHE" 2>/dev/null
    st="$CACHE/${sess//\//_}"
    [ "$(cat "$st" 2>/dev/null)" = "$h" ] && return 1
    printf '%s\n' "$h" > "$st"
    return 0
  fi
  f=$(printf '%s' "$p" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
  case "$f" in */docs/mapa/*) return 0 ;; esac
  return 1
}

_emit() {
  local saida pre
  # no `head`: the verdict ("initial load in N slices") comes AFTER one line per slice; the old
  # `head -6` cut exactly that line once the map reached 4 slices, so the 🚨 never fired on overflow
  saida=$(MAPA_REPO="$REPO" bash "$MAPA_HOOK" --selftest 2>&1 \
          | grep -E '^  [✓✗] slice [0-9]|initial load|BUDGET|measured pace')
  [ -n "$saida" ] || return 0
  if printf '%s' "$saida" | grep -q '✗'; then
    pre="🚨 [map-budget] OVER on touch — revolving door NOW (for something to enter, something LEAVES; docs/mapa/5_COMO_MANTER.md §5):"
  else
    pre="📏 [map-budget] after this touch:"
  fi
  jq -cn --arg ctx "$pre
$saida" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$ctx}}'
}

_selftest() {
  local t ok=0 ruim=0 r
  # 🚨 the test repo must NOT inherit the caller's repo: inside the pre-commit of a
  # `git commit --only`, GIT_INDEX_FILE is absolute and `git add -A` here would write the fixture
  # INTO THE COMMIT'S INDEX
  unset GIT_INDEX_FILE GIT_DIR GIT_WORK_TREE GIT_PREFIX GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES
  t=$(mktemp -d); trap 'rm -rf "$t"' RETURN
  mkdir -p "$t/repo/docs/mapa" "$t/bin"
  printf '# fixture map\n' > "$t/repo/docs/mapa/2_ONDE.md"   # hermetic: never reads the real map
  git -C "$t/repo" init -q && git -C "$t/repo" add -A \
    && git -C "$t/repo" -c user.name=t -c user.email=t@t commit -qm base
  # the real mapa-hook takes seconds; the doubles only say it ran — what is proven is the TRIGGER
  printf '#!/bin/sh\necho "  ✓ slice 1/5: 1 B"\necho "  · BUDGET: x"\necho "  ✓ initial load in 5 slice(s) — maximum 5"\n' > "$t/bin/v"
  # the overflow double mimics the REAL output: determinism + 6 slice lines BEFORE the verdict
  { printf '#!/bin/sh\necho "  ✓ determinism: identical cut (9 slices on the fixture)"\n'
    for i in 1 2 3 4 5 6; do printf 'echo "  ✓ slice %s/6: 1 B — under the ceiling 9500"\n' "$i"; done
    printf 'echo "  ✗ initial load in 6 slices — past 5"\n'; } > "$t/bin/x"
  chmod +x "$t/bin/v" "$t/bin/x"
  _case() {  # name · expected (yes|no|over) · double · payload
    r=$(printf '%s' "$4" | MAPA_REPO="$t/repo" MAPA_ORC_CACHE="$t/cache" MAPA_HOOK="$t/bin/$3" "$0")
    local got=no
    [ -n "$r" ] && got=yes
    printf '%s' "$r" | grep -q 'OVER on touch' && got=over
    if [ "$got" = "$2" ]; then echo "  ✓ $1"; ok=$((ok+1)); else echo "  ✗ $1 (expected $2, got $got)"; ruim=$((ruim+1)); fi
  }
  local E='{"tool_name":"Edit","tool_input":{"file_path":"'"$t"'/repo/docs/mapa/2_ONDE.md"}}'
  local B='{"tool_name":"Bash","session_id":"s1","tool_input":{"command":"python3 ed.py docs/mapa/2_ONDE.md"}}'
  _case "Edit on the map warns" yes v "$E"
  _case "Edit outside the map is silent" no v '{"tool_name":"Edit","tool_input":{"file_path":"/x/docs/other/A.md"}}'
  _case "Edit on the map with 6 slices is OVER (the verdict arrives)" over x "$E"
  _case "Bash on a CLEAN map is silent (a read)" no v "$B"
  echo "new line" >> "$t/repo/docs/mapa/2_ONDE.md"
  _case "Bash that EDITED the map warns" yes v "$B"
  _case "Bash again, same state, is silent" no v "$B"
  _case "Bash without 'mapa' in the command is silent" no v '{"tool_name":"Bash","session_id":"s1","tool_input":{"command":"ls"}}'
  _case "Bash from ANOTHER session in the same state warns it" yes v "${B/s1/s2}"
  echo "another" >> "$t/repo/docs/mapa/2_ONDE.md"
  _case "Bash that overflowed is OVER" over x "$B"
  echo "== $ok ok · $ruim failure(s) =="
  [ "$ruim" -eq 0 ]
}

if [ "${1:-}" = "--selftest" ]; then _selftest; exit; fi
_should_warn && _emit
exit 0
