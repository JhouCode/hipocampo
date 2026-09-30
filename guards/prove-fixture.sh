#!/usr/bin/env bash
#   PROVE-FIXTURE -- proves a guard of guards/memory-guards.sh FAILING on a NAMED mutant.
#
#   WHY IT EXISTS: a guard proved red with a mutant made by hand in /tmp loses its proof when /tmp is
# cleaned. A guard's mutant is a NAMED, versioned FIXTURE: `fixtures/guards/<guard>/{controle,mutante-N}/`.
#
#   FORMAT OF A CASE:
#     arvore/    -- the files the guard reads, at the paths it reads them (relative to the repo root);
#                   a `memory/` folder in it is the memory store of the case (MEM_DIR)
#     esperado   -- line 1: `verde` (green) or `vermelho` (red) · line 2: fragment (grep -F) of the
#                   guard's message
#     mutacao    -- (mutant only) what was broken, and where it came from
#     comando    -- (optional) command run in the tree instead of the guards (a script's selftest)
#
#   HOW IT PROVES: each case becomes a temporary git repo holding `arvore/`, this repo's
# `memory-guards.sh` runs in it (`--tree`), and the guard's verdict is read from its MESSAGE:
# `✓ <fragment>` for green, `✗ <fragment>` for red. The CONTROL must come out green -- without it, a
# red mutant may just be a broken guard that always shouts.
#   The control is a FROZEN copy of the target on the day the fixture was born: when the guard or the
# target change, the control may age -- then it turns RED here, and that is the warning.
#   MEM_DIR always points inside the temporary tree (`<tmp>/memory`, present or not), so a case never
# reads the real memory store of whoever runs it.
#   The lab version also checked that the file a mutant changes falls inside the guard's declared
# "radius" (its router). The public battery ships no router -- every guard runs every time -- so that
# check is not here.
#
#   usage: prove-fixture.sh <guard>        · one guard
#          prove-fixture.sh --todas        · every folder in fixtures/guards/
#   rc 0: every case gave the expected verdict · rc 1: some did not · rc 2: usage
set -uo pipefail
#   THE PROVER ONLY TOUCHES TEMPORARY REPOS -- and so it must not inherit the repo of its caller.
# Called from a pre-commit, it inherits the commit's `GIT_INDEX_FILE`. In `git commit --only` that
# path is ABSOLUTE (`.git/next-index-*.lock`), and each case's `git add -A` wrote the FIXTURE's tree
# into the user's commit index: a real `commit --only` of 4 paths came out with 1 fixture file and
# 1506 deletions. In a normal commit the path is relative (`.git/index`), falls inside the temp dir,
# and that is why nobody had seen it.
unset GIT_INDEX_FILE GIT_DIR GIT_WORK_TREE GIT_PREFIX GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="$ROOT/fixtures/guards"
GUARDAS="$ROOT/guards/memory-guards.sh"

provar_caso() {
  local caso="$1" esp trecho tmp saida achou=0
  esp="$(sed -n 1p "$caso/esperado")"; trecho="$(sed -n 2p "$caso/esperado")"
  tmp="$(mktemp -d)"
  cp -a "$caso/arvore/." "$tmp/"
  git -C "$tmp" init -q && git -C "$tmp" add -A && \
    git -C "$tmp" -c user.name=fixture -c user.email=fixture@local commit -qm fixture >/dev/null 2>&1
  #   `comando` (optional): the case proves a script's SELFTEST, not a guard. It runs in the copied
  # tree, with ROOT = this repo (to find large fixtures without duplicating them in each case).
  # Without `comando`, it is the usual memory-guards --tree.
  if [ -f "$caso/comando" ]; then
    saida="$(cd "$tmp" && ROOT="$ROOT" MEM_DIR="$tmp/memory" bash -c "$(cat "$caso/comando")" 2>&1)"
  else
    saida="$(cd "$tmp" && MEM_DIR="$tmp/memory" bash "$GUARDAS" --tree 2>&1)"
  fi
  rm -rf "$tmp"
  #   No `grep -q` after a pipe: with pipefail, SIGPIPE buries the 0. It is counted instead.
  local marca='✓'; [ "$esp" = vermelho ] && marca='✗'
  achou="$(printf '%s\n' "$saida" | sed 's/\x1b\[[0-9;]*m//g' | grep -F -c -- "$marca $trecho")"
  if [ "${achou:-0}" -gt 0 ]; then
    printf '  ✓ %-12s -> %s as expected (%s %s...)\n' "$(basename "$caso")" "$esp" "$marca" "$trecho"
    return 0
  fi
  printf '  ✗ %-12s -> did NOT give %s (looked for "%s %s")\n' "$(basename "$caso")" "$esp" "$marca" "$trecho"
  printf '%s\n' "$saida" | sed 's/\x1b\[[0-9;]*m//g' | grep -F -- "$trecho" | head -3 | sed 's/^/        /'
  return 1
}

provar_guarda() {
  local g="$1" d f=0 n=0 mut=0
  [ -d "$BASE/$g" ] || { echo "no fixture for '$g' in $BASE" >&2; return 2; }
  echo "── $g"
  [ -d "$BASE/$g/controle" ] || { echo "  ✗ no CONTROL -- a red mutant alone proves nothing"; return 1; }
  for d in "$BASE/$g/controle" "$BASE/$g"/mutante-*; do
    [ -d "$d" ] || continue
    n=$((n+1)); case "$(basename "$d")" in mutante-*) mut=$((mut+1)) ;; esac
    provar_caso "$d" || f=$((f+1))
  done
  [ "$mut" -gt 0 ] || { echo "  ✗ no mutant -- the guard was never seen red"; f=$((f+1)); }
  echo "   $((n-f)) of $n case(s) as expected · $mut mutant(s)"
  [ "$f" -eq 0 ]
}

case "${1:-}" in
  --todas)
    rc=0
    for g in "$BASE"/*/; do provar_guarda "$(basename "$g")" || rc=1; done
    exit "$rc" ;;
  ""|-h|--help) sed -n '2,29p' "$0" | sed 's/^#\s\?//'; exit 2 ;;
  *) provar_guarda "$1"; exit $? ;;
esac
