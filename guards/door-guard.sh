#!/usr/bin/env bash
# door-guard.sh -- the REVOLVING DOOR at commit time: the resident map may not grow past its tare.
#
#   guarda_mapa_orcamento   the layer that loads in every session (docs/mapa/, cut into slices by
#                           scripts/mapa-hook.sh) stays inside its budget: no slice over the emission
#                           ceiling, at most MAPA_MAX_FATIAS slices (default 5), the core under the
#                           ceiling and under the amortized cost per turn.
#
# WHY SLICES AND NOT BYTES. A first version of this guard capped layers 1-3 at 20 KB, and was dropped
# before its commit: measured on the day, the slack was 5 laws against 26 laws born in 4 weeks -- a
# byte cap only dates the expiry. With the automatic slicing of the map hook, a bigger doc is one more
# slice, not truncation. What does NOT scale is a session that opens by reading 5, 6 blocks before any
# work. So the real ceiling is in SLICES, and past it the answer is the revolving door
# (docs/mapa/5_COMO_MANTER.md §5, docs/PORTA.md): for something to enter, something LEAVES, to one of
# the written destinations. "Raise the ceiling" is not one of them.
#
# IT DOES NOT RECOUNT. It delegates to `scripts/mapa-hook.sh --selftest`: two implementations of the
# same budget would be two truths drifting apart by themselves.
#
# The other half of the resident layer, the memory INDEX (bytes and lines), is judged by
# guarda_memoria_indice_integro in guards/memory-guards.sh; this file does not repeat it.
#
# WHAT IT JUDGES
#   The map of the repository it runs in (`MAPA_REPO=<repo root>`), never the configured HIPO_REPO:
# otherwise a commit would be judged by the disk of another checkout.
#   The map hook: the judged repo's scripts/mapa-hook.sh when it has one, else this checkout's.
#   The hook registration the selftest also checks (a slice without a registered command does not
# arrive): `MAPA_SETTINGS` when you set it (your live settings.json); otherwise the judged repo's
# `settings.example.json`, whose commands are written as `<YOUR_FOLDER>/scripts/mapa-hook.sh`; with
# neither, the selftest's own default (HIPO_SETTINGS).
#   It reads no transcript and no history: every behavioural check of the selftest runs on throwaway
# state in temporary directories.
#
# Gate: runs only where `docs/mapa/` exists -- a repo without a map is not failed for lacking one.
# Cost: the selftest takes ~15 s (its determinism control renders the map under 3 locales).
#
# Usage:
#   door-guard.sh           # judges the repo of the current directory
#   door-guard.sh --help
# rc 1 if red, 0 otherwise. Conscious bypass: git commit --no-verify (and own the debt).

set -uo pipefail

case "${1:-}" in
  --help|-h) sed -n '2,40p' "$0" | sed 's/^# \?//'; exit 0 ;;
  "") ;;
  *) echo "door-guard: unknown option '$1' (use --help)" >&2; exit 2 ;;
esac

PUB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "door-guard: outside a git repo" >&2; exit 2; }
cd "$ROOT" || exit 2

FALHAS=0; AVISOS=0; RODADOS=0
_titulo()  { printf '\033[%sm%s %s\033[0m\n' "$1" "$2" "$3"; shift 3; for l in "$@"; do printf '    %s\n' "$l"; done; }
vermelho() { _titulo 31 '✗' "$@"; FALHAS=$((FALHAS+1)); }
amarelo()  { _titulo 33 '!' "$@"; AVISOS=$((AVISOS+1)); }
verde()    { printf '\033[32m✓ %s\033[0m\n' "$1"; }
detalhe() {
  local todas n; todas="$(grep -v '^$')"; n=$(printf '%s\n' "$todas" | grep -c '' )
  printf '%s\n' "$todas" | head -6 | while IFS= read -r l; do printf '      %s\n' "$l"; done
  [ "$n" -gt 6 ] && printf '      ... and %s more\n' "$((n-6))"
  return 0
}

guarda_mapa_orcamento() {
  RODADOS=$((RODADOS+1))
  local hook saida
  if [ -f "$ROOT/scripts/mapa-hook.sh" ]; then hook="$ROOT/scripts/mapa-hook.sh"; else hook="$PUB/scripts/mapa-hook.sh"; fi
  #   EXECUTABLE, not only present: the selftest calls itself through `$0` for its determinism
  # control, so a non-executable hook would break the instrument, not the map.
  if [ ! -x "$hook" ]; then
    amarelo "map: $hook missing or not executable -- budget NOT measured" \
      "without it the map does not load; and a map that does not load is an orphan doc (docs/mapa/0_MAPA.md)"
    return
  fi
  local -a amb=("MAPA_REPO=$ROOT")
  if [ -z "${MAPA_SETTINGS:-}" ] && [ -f "$ROOT/settings.example.json" ]; then
    amb+=("MAPA_SETTINGS=$ROOT/settings.example.json" "MAPA_SCRIPT=${MAPA_SCRIPT:-<YOUR_FOLDER>/scripts/mapa-hook.sh}")
  fi
  if saida=$(env "${amb[@]}" "$hook" --selftest 2>&1); then
    verde "map: $(printf '%s' "$saida" | grep -m1 'initial load in' | sed 's/^ *✓ *//')"
    printf '%s\n' "$saida" | grep -E 'BUDGET' | sed 's/^ *·* */      /'
  else
    vermelho "map: budget blown or instrument broken" \
      "rule: docs/mapa/5_COMO_MANTER.md §5 -- the REVOLVING DOOR: for something to enter, something LEAVES" \
      "the way out has written destinations (docs/PORTA.md); 'raise the ceiling' is not one of them" \
      "run: MAPA_REPO=$ROOT bash $hook --selftest"
    printf '%s\n' "$saida" | grep -E '✗' | detalhe
  fi
}

if [ -d docs/mapa ]; then
  guarda_mapa_orcamento
else
  echo "door-guard: no docs/mapa/ in $ROOT -- nothing to judge"
fi

printf '── %s guard(s) · %s failure(s) · %s warning(s)\n' "$RODADOS" "$FALHAS" "$AVISOS"
[ "$FALHAS" -eq 0 ] || { echo "   (conscious bypass: git commit --no-verify -- and the debt is yours)" >&2; exit 1; }
exit 0
