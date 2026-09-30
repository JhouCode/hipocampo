#!/usr/bin/env bash
# mapa-hook.sh — loads the MAP (docs/mapa/) into Claude Code's context.
#
# WHAT IT IS FOR
#   The map is a DISTILLATE: it exists to be LOADED, not opened. Without this hook it is one more
#   doc waiting for someone to remember it — which is exactly how "read this before deciding" docs
#   die. This script is the difference between the two.
#
# HOW IT IS CALLED
#   As a Claude Code hook (`UserPromptSubmit`, and `SessionStart` with matcher `compact`). It gets
#   JSON on stdin (session_id, prompt, cwd…) and whatever it prints on STDOUT enters the context next
#   to the user's message.
#
# WHY IT DOES NOT INJECT EVERYTHING EVERY TIME — measured, not estimated
#   The stdout of UserPromptSubmit becomes PERMANENT conversation history: injecting on every turn
#   ACCUMULATES. On real sessions (median 19 turns, p90 141, max 579) a full load on every turn
#   would have repeated 84k / 624k / 2.5M tokens — the longest session fills the window by itself.
#   So:
#      turn 1 of the session → FULL load (layers 1-3), ALL slices at once
#      every N turns         → only the CORE: what degrades, not what is reference
#
# THE WHOLE LOAD GOES IN TURN 1
#   Stopping and resuming a conversation changes the `session_id`, and a new session starts from
#   zero. Spread over several turns, a session that dies early never sees the later layers. So the
#   hook is registered once per slice (`--parte N`) and all slices arrive with the first message.
#   N processes racing on ONE counter would lose a layer silently (the first to increment makes the
#   others believe they already delivered). So each part owns its OWN marker (`<sid>.pN`): the race
#   does not exist by construction, not by lock.
#
# THE CORE IS EXTRACTED, NEVER COPIED
#   A copy would be a second truth that drifts by itself. The core comes out of the layers by
#   ANCHOR. If an anchor disappears the script SHOUTS in the context instead of emitting less and
#   staying quiet — silent absence is the failure mode this map exists to kill.
#
# MANUAL USE
#   mapa-hook.sh --selftest   proves the anchors exist and measures what comes out
#   mapa-hook.sh --full       prints the full load
#   mapa-hook.sh --nucleo     prints only the core
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/hipo-config.sh"

REPO="${MAPA_REPO:-$HIPO_REPO}"
MAPA="$REPO/docs/mapa"
ESTADO_DIR="${MAPA_ESTADO:-$HIPO_STATE_DIR/mapa}"
#   How many turns between two core reminders. The ceiling below is on AMORTIZED cost (core bytes ÷
# CADA_N), so when the core grows past it the selftest offers two levers: cut the core, or space the
# reminder. Spacing it is not "raising the ceiling": the ceiling measures cost per turn; CADA_N says
# how often the core returns, and the price of spacing is written here — it returns less often.
#   The right fix is the revolving door (docs/mapa/5_COMO_MANTER.md §5): a law whose guard is PROVEN
# becomes a pointer and leaves the reminder, because the guard enforces it.
CADA_N="${MAPA_CADA_N:-10}"     # every how many turns the core comes back
# Where Claude Code reads the hook registration. A variable (not a fixed path) because the
# registration guard of --selftest MUST be pointable at a broken settings file — a guard that cannot
# fail proves nothing.
SETTINGS="${MAPA_SETTINGS:-$HIPO_SETTINGS}"
# THE PATH THAT MUST BE REGISTERED — and NOT `$0`. The first version of this guard compared with
# `$0`, and CI failed it at once: CI runs the selftest from a STAGED COPY, at another path, so `$0`
# never matched the settings and the guard shouted "not registered" with everything registered.
# `$0` answers "is THIS file registered?"; the question is "is the path the RUNTIME will invoke
# registered?". Only the second one breaks silently.
SCRIPT_REGISTRADO="${MAPA_SCRIPT:-$HIPO_REPO/scripts/mapa-hook.sh}"
# THE CEILING IS ON AMORTIZED COST (bytes per turn), not on the size of the core. Size alone is not
# what costs: `core ÷ CADA_N` is. The same core every 8 turns costs twice as much as every 16; a
# ceiling that only looks at size ignores half of the bill. (A ceiling guessed before the content
# existed was wrong twice in a row — estimation by eye does not replace measurement.)
TETO_BYTES_POR_TURNO=500
# CEILING PER EMISSION — the defect that almost shipped as "works".
#   The Claude Code runtime does NOT inject a large hook output: above the limit it PERSISTS it to a
# file and sends the context only a preview + the path. The preview is 2,000 UTF-16 units, cut back
# to the last newline when that newline falls after unit 1,000 (`bastao-entrega.py` emulates it and
# checks the emulation against real previews). Measured on the first real run:
# the hook emitted 18,057 B and the context received ~2 KB — half of layer 1 and ZERO of the laws.
#   And it FAILED SILENTLY: the heartbeat said "complete", the runtime said `hook success`, the
# selftest was green. It only showed up when comparing BYTE BY BYTE what reached the context with
# what the script produces. Hence the load goes in SLICES.
#   The limit is 10,000 characters (measured: an output of 9,586 units arrived whole, one of 10,057
# became a preview; not configurable by env var or settings key), and it is PER REGISTERED COMMAND,
# not per turn. The ceiling is 9,500: a 5% margin over an EXACT limit, because the number belongs to
# one runtime version and can change on an upgrade.
TETO_EMISSAO=9500
# What the slice count measures now that all slices arrive in the first turn:
#   (a) how many commands must be registered BY HAND in settings — a new slice needs a new line,
#       and outdated settings lose a layer SILENTLY (the coverage guard exists to catch that);
#   (b) how many separate blocks are read at once when the session opens.
# Past the ceiling the answer is not "raise the number": it is the REVOLVING DOOR of
# docs/mapa/5_COMO_MANTER.md §5 — for something to enter, something leaves, with a written
# destination.
MAX_FATIAS="${MAPA_MAX_FATIAS:-5}"   # growth of this number must be registered in the hooks (one --parte per slice)
# Session lengths (in turns) the selftest prices the load against. The default is an EXAMPLE: the
# median, p90 and max of one measured sample. Put your own here.
SESSOES_REF="${MAPA_SESSOES_REF:-19 141 579}"

C1="$MAPA/1_CONTRATO.md"; C2="$MAPA/2_ONDE.md"; C3="$MAPA/3_DECIDIDO.md"

# ── extract a "## title" section up to the next "## " ──────────────────────
secao() {  # $1=file  $2=anchor (start of the title, not the whole title)
  awk -v anc="$2" '
    /^## / { if (dentro) exit; if (index($0, anc)) { dentro=1; print; next } }
    dentro { print }
  ' "$1"
}

# ── the laws IN FORCE, only the bold statement (the prose stays in the doc) ──
leis_vigentes() {
  #   A LAW WHOSE GUARD DECLARES TO COVER IT DOES NOT RETURN IN THE CORE — cascade step 2 ("and then
  # it LEAVES the ruler") and revolving-door destination 1.
  #   And the ⚙ glyph is NOT enough: it says a guard exists, not that it covers the WHOLE statement
  # (guards borrowed from another purpose and cited as proof are common). The predicate is the same
  # as the door's: WITHOUT A CITATION, IT STAYS. Only a law the guard NAMES leaves — the guard's
  # `# @guard` header comment saying "... covers the law P14". To leave the core, a law's guard must
  # declare that it covers it.
  local ci="${MAPA_GUARDAS:-$REPO/guards/memory-guards.sh}"   # the guard battery whose headers name laws
  grep '^|.*IN FORCE' "$C3" 2>/dev/null | while IFS= read -r l; do
    local id dec
    id=$(printf '%s' "$l" | awk -F'|' '{gsub(/ /,"",$2); print $2}')
    # does the guard name this law? then the machine already enforces it and it pays no rent here
    #   The `[[:space:]]` BEFORE the article is not decoration: without it, a word ending in "the"
    # followed by the id would match and the law would leave the core through another word.
    if [ -f "$ci" ] && grep -qE "^[[:space:]]*# @(guard|GD[0-9]+) .*[[:space:]](the law |the )$id[[:space:]:,.]" "$ci" 2>/dev/null; then
      continue
    fi
    # 4th field = the decision; from it, the FIRST **bold** span
    dec=$(printf '%s' "$l" | awk -F'|' '{print $4}' | grep -oE '\*\*[^*]+\*\*' | head -1 | tr -d '*')
    [ -n "$dec" ] || dec=$(printf '%s' "$l" | awk -F'|' '{print substr($4,1,90)}')
    printf -- '- **%s** — %s\n' "$id" "$dec"
  done
}

faltou() {  # an anchor vanished: shout, do not go quiet
  printf '\n> 🚨 **MAPA-HOOK: anchor missing — `%s`.** The core came out INCOMPLETE.\n' "$1"
  printf '> Someone renamed a map section without adjusting `scripts/mapa-hook.sh`. Treat the core\n'
  printf '> below as partial and read `docs/mapa/` in full before deciding anything.\n\n'
}

nucleo() {
  local aut nao ler leis
  aut=$(secao "$C1" "What is ALREADY AUTHORIZED")
  nao=$(secao "$C1" "What I do NOT do without the owner")
  # From this section the core takes only the TITLE and the BLOCKQUOTE — which is the rule. The
  # paragraph after it is the measurement that justifies it, and justification is reference: it
  # lives in the doc, not in the reminder that returns every N turns.
  ler=$(secao "$C1" "How I read what the owner writes" | grep -E '^(#|>|$)')
  leis=$(leis_vigentes)

  printf '<!-- mapa-hook: CORE (extracted from docs/mapa/, not copied) -->\n'
  printf '# MAP — core\n\n'
  printf 'Periodic reminder of layers 1 and 3. The whole map is in `docs/mapa/`; **in a conflict,\n'
  printf 'the detailed doc wins**.\n\n'

  [ -n "$aut" ]  && printf '%s\n\n' "$aut"  || faltou "1_CONTRATO ## What is ALREADY AUTHORIZED"
  [ -n "$nao" ]  && printf '%s\n\n' "$nao"  || faltou "1_CONTRATO ## What I do NOT do without the owner"
  [ -n "$ler" ]  && printf '%s\n\n' "$ler"  || faltou "1_CONTRATO ## How I read what the owner writes"
  if [ -n "$leis" ]; then
    printf '## Product laws IN FORCE (statement; the proof is in `docs/mapa/3_DECIDIDO.md`)\n\n'
    printf '%s\n' "$leis"
  else
    faltou "3_DECIDIDO table | … | IN FORCE |"
  fi
}

# ── initial load in AUTOMATIC SLICES ────────────────────────────────────────
#   THIS EXISTS BECAUSE THE MAP WAS ABOUT TO BE BORN WITH AN EXPIRY DATE. With a fixed ceiling the
# slack was ~5 laws, and laws were being born at ~6 per week: the map would have expired within a
# week, SILENTLY, exactly like the old docs did.
#   The answer is not a bigger ceiling; it is letting the doc GROW without breaking anything: the
# number of slices adjusts itself to the size, breaking at section boundaries (`## `). A bigger doc
# means one more slice, not truncation — and the selftest says how far that is, IN LAWS.
#   Order by MEASURED USE, not by number: contract first (a forgotten authorization becomes friction
# on the first command), laws next (they rule the work), WHERE last — it is the least invoked.

plano() {  # one line per slice: file <TAB> start <TAB> end <TAB> label
  local spec f rot
  for spec in "$C1|WHO WE ARE (working contract)" \
              "$C3|WHAT WAS ALREADY DECIDED (product laws)" \
              "$C2|WHERE WE ARE (machine coordinates)"; do
    f="${spec%%|*}"; rot="${spec#*|}"
    [ -f "$f" ] || { printf 'AUSENTE\t0\t0\t%s\n' "$rot"; continue; }
    # TWO BREAK RULES, and the second exists because the first alone IS DECORATIVE.
    #   Preferred: pack with an EYE ON THE NEXT section — close the slice only when the next section
    # does not fit. (Breaking at the first `## ` after 70% of the ceiling produced tiny slices and
    # extra turns of load.)
    #   FORCED: on reaching the ceiling, break wherever it is. Without it slicing does not protect
    # the REAL growth case — tested with +180 synthetic laws: layer 3 grows as TABLE ROWS inside the
    # SAME section, no `## ` appears to break on, and the slice went to 41,657 B. It would have
    # truncated silently with slicing "working".
    #   `util` discounts the header that fatia() prints on top of the excerpt.
    #   `LC_ALL=C` IS NOT A DETAIL — IT IS THE UNIT OF MEASUREMENT.
    #   gawk's `length()` counts CHARACTERS under a UTF-8 locale and BYTES under locale C; the ceiling
    # is in BYTES (the runtime truncates bytes). Without fixing it the planner measured in one unit
    # and promised another: the same content gave 4 slices in one shell and 5 under `env -i`. And
    # `mawk` / `busybox awk` count bytes ALWAYS — Ubuntu Server ships `mawk`, not `gawk`.
    LC_ALL=C awk -v f="$f" -v rot="$rot" -v teto="$TETO_EMISSAO" '
      BEGIN { util = teto - 700; ini = 1; acc = 0; nsec = 0 }
      { linha[NR] = length($0) + 1
        if (/^## /) { sec[++nsec] = NR }
        total = NR }
      END {
        # size of each section (from the anchor to the line before the next one)
        for (i = 1; i <= nsec; i++) {
          fimsec = (i < nsec ? sec[i+1] - 1 : total)
          tam[i] = 0
          for (j = sec[i]; j <= fimsec; j++) tam[i] += linha[j]
        }
        acc = 0
        for (j = 1; j < (nsec ? sec[1] : total + 1); j++) acc += linha[j]   # preamble
        ini = 1
        for (i = 1; i <= nsec; i++) {
          fimsec = (i < nsec ? sec[i+1] - 1 : total)
          if (acc > 0 && acc + tam[i] > util) {          # the next section does NOT fit: close here
            print f"\t"ini"\t"sec[i]-1"\t"rot; ini = sec[i]; acc = 0
          }
          if (tam[i] > util) {                            # section bigger than a slice: FORCED break
            corte = 0
            for (j = sec[i]; j <= fimsec; j++) {
              corte += linha[j]
              if (corte > util && j > ini) { print f"\t"ini"\t"j"\t"rot; ini = j + 1; corte = 0 }
            }
            acc = corte
          } else acc += tam[i]
        }
        if (total >= ini) print f"\t"ini"\t"total"\t"rot
      }
    ' "$f"
  done
}
n_fatias() { plano | grep -c . ; }

fatia() {  # $1 = slice index (1..N)
  local linha f ini fim rot tot parte
  tot=$(n_fatias)
  linha=$(plano | sed -n "${1}p"); [ -n "$linha" ] || return 0
  f=$(printf '%s' "$linha" | cut -f1); ini=$(printf '%s' "$linha" | cut -f2)
  fim=$(printf '%s' "$linha" | cut -f3); rot=$(printf '%s' "$linha" | cut -f4)
  # how many parts this layer has, and which one this is
  parte=$(plano | grep -n -F "	$rot" | grep -c "^[0-9]*:" )
  printf '<!-- mapa-hook: INITIAL LOAD · part %s of %s · %s -->\n' "$1" "$tot" "$rot"
  printf '# THE MAP — %s   *(part %s of %s of the load)*\n\n' "$rot" "$1" "$tot"
  if [ "$1" = 1 ]; then
    printf 'The map arrives in **%s parts, all in this message** — in separate blocks because the runtime\n' "$tot"
    printf 'truncates a big block (see `scripts/mapa-hook.sh`). **THE ORDER OF ARRIVAL IS NOT GUARANTEED:**\n'
    printf 'orient yourself by the label *"part N of %s"*, never by position.\n' "$tot"
    printf 'Index of the fronts and the maintenance rule in `docs/mapa/4_FRENTES.md`\n'
    printf 'and `docs/mapa/5_COMO_MANTER.md` — **open them when the subject asks**.\n'
    printf '**In a conflict between this distillate and the detailed doc, the DOC wins.**\n\n'
  fi
  printf -- '---\n\n'
  if [ "$f" = AUSENTE ]; then
    printf '\n> 🚨 **MAPA-HOOK: layer missing (%s).** INCOMPLETE load.\n' "$rot"
  else
    sed -n "${ini},${fim}p" "$f"
  fi
}

completo() { local i t; t=$(n_fatias); i=1; while [ "$i" -le "$t" ]; do fatia "$i"; i=$((i+1)); done; }

# ── selftest ────────────────────────────────────────────────────────────────
if [ "${1:-}" = "--selftest" ]; then
  ok=0; ruim=0
  echo "== mapa-hook --selftest =="
  for f in "$C1" "$C2" "$C3"; do
    if [ -f "$f" ]; then echo "  ✓ exists $(basename "$f") ($(wc -c <"$f") B)"; ok=$((ok+1))
    else echo "  ✗ MISSING $f"; ruim=$((ruim+1)); fi
  done
  for a in "What is ALREADY AUTHORIZED" "What I do NOT do without the owner" "How I read what the owner writes"; do
    n=$(secao "$C1" "$a" | wc -l)
    if [ "$n" -gt 2 ]; then echo "  ✓ anchor '$a' → $n lines"; ok=$((ok+1))
    else echo "  ✗ anchor '$a' DOES NOT RESOLVE (only $n lines)"; ruim=$((ruim+1)); fi
  done
  #   DETERMINISM CONTROL — the output cannot depend on WHO called.
  #   The `LC_ALL=C` in `plano()` fixes the unit; THIS control is what stops someone from removing it
  # without noticing. A guard without a regression lock lasts until the next refactor.
  #   It runs on a SYNTHETIC map, not the real one: on real content `char` and `byte` often give the
  # SAME cut, so removing `LC_ALL=C` passed GREEN — a guard that depends on luck is not a guard.
  #   And the fixture is DERIVED FROM THE CEILING, not fixed: with a fixed size, moving TETO_EMISSAO
  # made the fixture stop discriminating and the selftest byte-identical with and without the
  # `LC_ALL=C`. Each line is pure 2-byte characters, and the total is ~70% of the usable size in
  # CHARACTERS — ~140% in BYTES. Under character counting it fits; under byte counting it does not.
  _det_util=$(( TETO_EMISSAO - 700 ))
  _det_chars=$(( _det_util * 7 / 10 ))
  _det_lin=$(( _det_chars / 80 )); [ "$_det_lin" -lt 4 ] && _det_lin=4
  _det_dir=$(mktemp -d) || _det_dir=""
  if [ -z "$_det_dir" ]; then
    echo "  ✗ determinism: could not create a temp dir — control DID NOT RUN"
    ruim=$((ruim+1))
  else
  mkdir -p "$_det_dir/docs/mapa"
  _det_acento=$(printf 'ñ%.0s' $(seq 1 80))
  { echo "# synthetic"; echo; echo "## single section"; echo
    i=0; while [ $i -lt "$_det_lin" ]; do echo "- $_det_acento"; i=$((i+1)); done; } \
    > "$_det_dir/docs/mapa/3_DECIDIDO.md"
  cp "$_det_dir/docs/mapa/3_DECIDIDO.md" "$_det_dir/docs/mapa/1_CONTRATO.md"
  cp "$_det_dir/docs/mapa/3_DECIDIDO.md" "$_det_dir/docs/mapa/2_ONDE.md"

  #   COMPARE THE CUT, NOT ONLY THE COUNT. `--n-fatias` is strictly weaker: a review measured 16 of 39
  # fixture sizes where the number matches and the cuts do not. The `cksum` of `--full` catches the
  # whole emission (~2.5 s — cheap, and it separates "counted the same" from "cut the same").
  _assina() { MAPA_REPO="$_det_dir" "$0" --full 2>/dev/null | cksum; }
  _det_ref=$(_assina)
  _det_ok=1; _det_amb=""
  #   FAIL-CLOSED: without a usable reference the control FAILS. A previous version compared empty
  # strings with each other and printed a green line with the number blank.
  case "$_det_ref" in
    ''|*[!0-9\ ]*) _det_ok=0; _det_amb=" unreadable reference" ;;
  esac
  for _amb in "LC_ALL=C" "LC_ALL=en_US.UTF-8" "LC_ALL=POSIX"; do
    _n=$(env "$_amb" MAPA_REPO="$_det_dir" "$0" --full 2>/dev/null | cksum)
    [ "$_n" = "$_det_ref" ] || { _det_ok=0; _det_amb="$_det_amb $_amb"; }
  done
  #   The other axis: the awk IMPLEMENTATION. Only tested if a second awk exists on the host —
  # declaring it could not be tested is a valid answer; faking coverage is not.
  _mawk=$(command -v mawk 2>/dev/null || true)
  if [ -n "$_mawk" ]; then
    _tmpd=$(mktemp -d); ln -sf "$_mawk" "$_tmpd/awk"
    _n=$(PATH="$_tmpd:$PATH" MAPA_REPO="$_det_dir" "$0" --full 2>/dev/null | cksum)
    [ "$_n" = "$_det_ref" ] || { _det_ok=0; _det_amb="$_det_amb mawk"; }
    rm -rf "$_tmpd"
  fi
  #   CONTROL OF THE CONTROL: the fixture only counts if it DISCRIMINATES. If both units give the
  # same cut on it, this test proves nothing and cannot say it proved.
  _det_nc=$(MAPA_REPO="$_det_dir" "$0" --n-fatias 2>/dev/null)
  _det_nb=$(MAPA_REPO="$_det_dir" LC_ALL=C awk 'BEGIN{u='"$_det_util"'} {b+=length($0)+1} END{print (b>u)?"maior":"menor"}' \
            "$_det_dir/docs/mapa/3_DECIDIDO.md" 2>/dev/null)
  _det_cc=$(MAPA_REPO="$_det_dir" LC_ALL=en_US.UTF-8 awk 'BEGIN{u='"$_det_util"'} {c+=length($0)+1} END{print (c>u)?"maior":"menor"}' \
            "$_det_dir/docs/mapa/3_DECIDIDO.md" 2>/dev/null)
  if [ "$_det_nb" = "$_det_cc" ]; then
    echo "  ✗ determinism: the FIXTURE DOES NOT DISCRIMINATE at ceiling $TETO_EMISSAO (byte and character"
    echo "      fall on the same side: $_det_nb) — the result below proves nothing; recalibrate its size"
    ruim=$((ruim+1))
  elif [ "$_det_ok" = 1 ]; then
    echo "  ✓ determinism: identical cut ($_det_nc slices on the fixture) in 3 locales$([ -n "$_mawk" ] && echo ' + mawk' || echo '; mawk ABSENT, not tested')"
    ok=$((ok+1))
  else
    echo "  ✗ determinism BROKEN: the CUT changes with the environment —$_det_amb"
    echo "      the planner measures in a unit that depends on locale/awk again; check the LC_ALL=C"
    ruim=$((ruim+1))
  fi
  rm -rf "$_det_dir"
  fi

  nl=$(leis_vigentes | wc -l)
  if [ "$nl" -ge 5 ]; then echo "  ✓ laws IN FORCE extracted: $nl"; ok=$((ok+1))
  else echo "  ✗ laws IN FORCE: only $nl — extraction broke"; ruim=$((ruim+1)); fi
  # NO EMISSION may pass the ceiling — above it the runtime persists to a file and injects only a
  # 2 KB preview. That is how an 18 KB load reached the context half-way, in silence.
  NFT=$(n_fatias); i=1
  while [ "$i" -le "$NFT" ]; do
    tf=$(fatia "$i" | wc -c)
    if [ "$tf" -le "$TETO_EMISSAO" ]; then echo "  ✓ slice $i/$NFT: $tf B (~$((tf/4)) tok) — under the ceiling $TETO_EMISSAO"; ok=$((ok+1))
    else echo "  ✗ slice $i/$NFT: $tf B OVER the ceiling — the runtime will truncate SILENTLY"; ruim=$((ruim+1)); fi
    i=$((i+1))
  done
  # ── GROWTH BUDGET ─────────────────────────────────────────────────────────
  # Old docs expired SILENTLY. This is the alarm they never had: it says, in LAWS, how much still
  # fits before the map costs one more slice (MAX_FATIAS). The scarce resource is not bytes — it is
  # the patience of whoever reads 3, 4, 5 blocks at the start of a session.
  if [ "$NFT" -le "$MAX_FATIAS" ]; then echo "  ✓ initial load in $NFT slice(s) — maximum $MAX_FATIAS"; ok=$((ok+1))
  else echo "  ✗ initial load in $NFT slices — past $MAX_FATIAS; time for the REVOLVING DOOR (docs/mapa/5_COMO_MANTER.md §5)"; ruim=$((ruim+1)); fi
  nlv=$(leis_vigentes | grep -c .); blei=$(grep '^|.*IN FORCE' "$C3" | wc -c)
  [ "$nlv" -gt 0 ] && custo_lei=$((blei/nlv)) || custo_lei=210
  ult=$(plano | tail -1); uf=$(printf '%s' "$ult" | cut -f1)
  [ "$uf" = AUSENTE ] || folga=$(( TETO_EMISSAO - $(fatia "$NFT" | wc -c) ))
  echo "  · BUDGET: $nlv laws in force at ~$custo_lei B each; +$((folga/custo_lei)) fit before slice $((NFT+1)) is needed"
  echo "            (divide by your own pace of new laws to see how long the current slice count lasts)"
  tn=$(nucleo | wc -c); tc=$(completo | wc -c); bpt=$((tn/CADA_N))
  if [ "$tn" -le "$TETO_EMISSAO" ]; then echo "  ✓ core: $tn B under the ceiling"; ok=$((ok+1))
  else echo "  ✗ core: $tn B OVER the ceiling — would truncate silently"; ruim=$((ruim+1)); fi
  echo "  · core      $tn B (~$((tn/4)) tokens), every $CADA_N turns — $((tn/(nlv>0?nlv:1))) B per law (extract)"
  echo "  · initial load $tc B (~$((tc/4)) tokens), in $NFT slice(s)"
  echo "  · amortized cost: $bpt B/turn — ceiling $TETO_BYTES_POR_TURNO"
  if [ "$bpt" -le "$TETO_BYTES_POR_TURNO" ]; then ok=$((ok+1))
  else echo "  ✗ cost/turn over the ceiling — cut the core OR raise MAPA_CADA_N"; ruim=$((ruim+1)); fi
  # what this would cost on reference session lengths (SESSOES_REF, above)
  for t in $SESSOES_REF; do
    echo "  · session of $t turns: $(( (tc + (t/CADA_N)*tn) / 4 )) tokens  (vs $(( t*tc/4 )) if it injected everything every turn)"
  done
  if nucleo | grep -q 'anchor missing'; then echo "  ✗ core contains an anchor-missing warning"; ruim=$((ruim+1)); else ok=$((ok+1)); fi
  # THE HEARTBEAT MUST SAY WHAT IT EMITTED — it once came out EMPTY (a variable was read before
  # being assigned, and the `2>/dev/null` swallowed the error). A log that records the field blank
  # looks like it works and proves nothing. Exercises the real path, with throwaway state and log.
  hbt=$(mktemp); est=$(mktemp -d)
  printf '{"session_id":"selftest-hb"}' | MAPA_LOG="$hbt" MAPA_ESTADO="$est" "$0" >/dev/null 2>&1
  if grep -qE 'emitted=(slice[0-9]+(-no-transcript)?|already-in-context[0-9]+|core|nothing)$' "$hbt"; then
    echo "  ✓ heartbeat records what it emitted: $(sed -n '1s/.*\(emitted=.*\)/\1/p' "$hbt")"; ok=$((ok+1))
  else
    echo "  ✗ heartbeat with an EMPTY or absent 'emitted' field — the log lies: $(cat "$hbt")"; ruim=$((ruim+1))
  fi
  rm -rf "$hbt" "$est"

  # ── COMPACTION ─────────────────────────────────────────────────────────────
  # THESE GUARDS WERE BORN FROM A REAL DEFECT, found with the hook already live: after a compaction
  # the map vanished from the context and did NOT come back — and every instrument stayed green,
  # because `emitted=nothing` on turn 30 is the CORRECT answer of the old rule. The log did not lie;
  # it answered another question. See the comment block on the real path, below.
  #
  # GUARD 1 — REGISTRATION ON BOTH EVENTS. Claude Code reads settings at BOOT: a missing
  # registration or a wrong schema = a hook that does not run, with no error and no warning. From the
  # outside, "not registered" and "nothing to emit" are identical.
  #   The settings questions are asked in python3 (already required by hipo-config.sh), not jq: on a
  # host without jq these checks failed AND the real path lost the session id and the event source.
  _settings() {  # $1 = question (registered|compact|parts) · $2 = event · reads $SETTINGS
    python3 -c '
import json, re, sys
path, s, q, ev = sys.argv[1:5]
try:
    hooks = json.load(open(path, encoding="utf-8")).get("hooks") or {}
    def cmds(entries):
        return [h.get("command") for e in (entries or []) for h in (e.get("hooks") or [])]
    def is_s(c):
        return isinstance(c, str) and (c == s or c.startswith(s + " "))
    if q == "registered":           # some command of the event is the script (with or without args)
        sys.exit(0 if any(is_s(c) for c in cmds(hooks.get(ev))) else 1)
    if q == "compact":              # a SessionStart entry with matcher "compact" runs the script
        sys.exit(0 if any((e.get("matcher") or "") == "compact" and any(is_s(c) for c in cmds([e]))
                          for e in (hooks.get("SessionStart") or [])) else 1)
    if q == "parts":                # the --parte numbers registered on the event, sorted numerically
        entries = hooks.get(ev) or []
        if ev == "SessionStart":
            entries = [e for e in entries if (e.get("matcher") or "") == "compact"]
        got = [re.sub(r".* --parte +", "", c, count=1) for c in cmds(entries)
               if isinstance(c, str) and c.startswith(s + " --parte ")]
        got.sort(key=float)         # a non-numeric part fails the whole answer (prints nothing)
        print("".join(g + "\n" for g in got), end="")
        sys.exit(0)
except Exception:
    sys.exit(1)
sys.exit(1)
' "$SETTINGS" "$SCRIPT_REGISTRADO" "$1" "${2:-}" 2>/dev/null
  }
  if [ ! -r "$SETTINGS" ]; then
    echo "  ✗ settings UNREADABLE at $SETTINGS — cannot prove the hook is registered"; ruim=$((ruim+1))
  else
    for ev in UserPromptSubmit SessionStart; do
      if _settings registered "$ev" >/dev/null; then
        echo "  ✓ registered on $ev"; ok=$((ok+1))
      else
        echo "  ✗ NOT registered on $ev — the hook will not run on that event (SILENT failure)"; ruim=$((ruim+1))
      fi
    done
    # The matcher matters: SessionStart without `compact` would cover startup/resume and miss exactly
    # the case this work exists to close.
    if _settings compact >/dev/null; then
      echo "  ✓ SessionStart with matcher 'compact'"; ok=$((ok+1))
    else
      echo "  ✗ SessionStart WITHOUT matcher 'compact' — the map does not come back after compacting"; ruim=$((ruim+1))
    fi

    # COVERAGE OF THE PARTS — the guard the rest of the design REQUIRES.
    #   The compact event delivers one slice per registered command. If the map grows to 4 slices and
    # settings keep 3, slice 4 **does not arrive**, the counter is marked as loaded and
    # UserPromptSubmit does not re-emit: silent loss, the exact size of a layer. A duplicated
    # registration (`--parte 2` twice) has the same effect and is even easier to miss.
    #   So the guard does not count: it compares the registered SET with exactly `1..N`.
    esperado=$(seq 1 "$(n_fatias)" | tr '\n' ' ')
    achado=$(_settings parts SessionStart | tr '\n' ' ')
    if [ "$achado" = "$esperado" ]; then
      echo "  ✓ compact covers the $(n_fatias) slice(s): --parte $esperado"; ok=$((ok+1))
    else
      echo "  ✗ compact covers [$achado] but the map has [$esperado] — a slice without a command DOES NOT ARRIVE, silently"; ruim=$((ruim+1))
    fi

    # COVERAGE ON UserPromptSubmit — same loss, other event.
    #   Since the whole load goes in turn 1, UserPromptSubmit also needs one command per slice. The
    # loss here is WORSE than on compact: the slice without a command reaches NO new session, every
    # day, silently — while the rest of the map arrives and makes everything look right.
    achadou=$(_settings parts UserPromptSubmit | tr '\n' ' ')
    if [ "$achadou" = "$esperado" ]; then
      echo "  ✓ UserPromptSubmit covers the $(n_fatias) slice(s): --parte $esperado"; ok=$((ok+1))
    else
      echo "  ✗ UserPromptSubmit covers [$achadou] but the map has [$esperado] — a new session is born WITHOUT that layer"; ruim=$((ruim+1))
    fi
  fi

  # GUARD 2 — THE BEHAVIOUR, not the registration. Exercises the REAL path with throwaway state:
  # plants a high counter (like a long session, which is precisely who compacts), sends the
  # SessionStart/compact JSON and requires BOTH things — counter reset AND empty stdout. "Reset"
  # alone is not enough: emitting here would duplicate slice 1 on the next turn.
  est2=$(mktemp -d); lg2=$(mktemp); printf '30' > "$est2/provac.n"
  saida2=$(printf '{"session_id":"provac","hook_event_name":"SessionStart","source":"compact"}' \
    | MAPA_LOG="$lg2" MAPA_ESTADO="$est2" "$0" 2>/dev/null)
  cont2=$(cat "$est2/provac.n" 2>/dev/null)
  if [ "$cont2" = "0" ] && [ -z "$saida2" ]; then
    echo "  ✓ compact WITHOUT --parte: resets (30→0) and emits nothing — the fallback"; ok=$((ok+1))
  else
    echo "  ✗ compact fallback: counter='$cont2' (expected 0), emitted ${#saida2} B (expected 0)"; ruim=$((ruim+1))
  fi
  # The path that really runs: each --parte delivers ONE slice and marks it as loaded. Checked slice
  # by slice — including that each carries the right label, since THE ORDER OF ARRIVAL IS NOT
  # GUARANTEED (measured with a probe: part 2 arrived before part 1).
  NFP=$(n_fatias); pok=1
  for p in $(seq 1 "$NFP"); do
    rm -f "$est2"/provac.p* 2>/dev/null; printf '30' > "$est2/provac.n"
    sp=$(printf '{"session_id":"provac","hook_event_name":"SessionStart","source":"compact"}' \
      | MAPA_LOG="$lg2" MAPA_ESTADO="$est2" "$0" --parte "$p" 2>/dev/null)
    cp2=$(cat "$est2/provac.n" 2>/dev/null)
    esp=$(fatia "$p")
    [ "$sp" = "$esp" ] || { echo "  ✗ compact --parte $p emitted content != slice $p"; pok=0; }
    [ "$cp2" = "0" ] || { echo "  ✗ compact --parte $p left counter='$cp2' (expected 0 — the core rhythm restarts)"; pok=0; }
    [ -e "$est2/provac.p$p" ] || { echo "  ✗ compact --parte $p did NOT mark slice $p — UserPromptSubmit will re-emit"; pok=0; }
    printf '%s' "$sp" | grep -q "part $p of $NFP" || { echo "  ✗ slice $p is not labelled 'part $p of $NFP' — the order of arrival is not guaranteed"; pok=0; }
  done
  if [ "$pok" = 1 ]; then
    echo "  ✓ compact --parte 1..$NFP: each delivers the right slice, labelled, and marks ITS slice"; ok=$((ok+1))
  else ruim=$((ruim+1)); fi
  # ── THE WHOLE LOAD IN TURN 1 ─────────────────────────────────────────────
  # THE RACE GUARD — it is what justifies the per-slice marker.
  #   The N instances fire IN PARALLEL and in REVERSE order, the worst case of scheduling. With
  # shared state (a single counter) the first to write would make the others believe they had
  # delivered and exit silently. With a marker per slice the N always emit. If someone "simplifies"
  # to a single counter, this guard turns red at once.
  est3=$(mktemp -d); lg3=$(mktemp); carga_ok=1
  for p in $(seq "$NFP" -1 1); do
    ( printf '{"session_id":"prova1","hook_event_name":"UserPromptSubmit"}' \
        | MAPA_LOG="$lg3" MAPA_ESTADO="$est3" "$0" --parte "$p" > "$est3/s.$p" 2>/dev/null ) &
  done
  wait
  for p in $(seq 1 "$NFP"); do
    [ -s "$est3/s.$p" ] || { echo "  ✗ turn 1: part $p did NOT emit — layer lost SILENTLY"; carga_ok=0; continue; }
    [ "$(cat "$est3/s.$p")" = "$(fatia "$p")" ] || { echo "  ✗ turn 1: part $p emitted content != slice $p"; carga_ok=0; }
    grep -q "part $p of $NFP" "$est3/s.$p" || { echo "  ✗ turn 1: part $p is not labelled 'part $p of $NFP'"; carga_ok=0; }
  done
  # the union must be the COMPLETE load — no proxy: compares byte for byte with `completo`
  if [ "$(cat "$est3"/s.* 2>/dev/null | wc -c)" != "$(completo | wc -c)" ]; then
    echo "  ✗ turn 1: the sum of the parts ($(cat "$est3"/s.* 2>/dev/null | wc -c) B) != complete load ($(completo | wc -c) B)"; carga_ok=0
  fi
  if [ "$carga_ok" = 1 ]; then
    echo "  ✓ turn 1 (N instances IN PARALLEL, reverse order): the $NFP slices arrive, labelled, adding up to the whole load"; ok=$((ok+1))
  else ruim=$((ruim+1)); fi

  # NEGATIVE CONTROL OF THE LOAD — without it the test above would pass even if the script ALWAYS
  # emitted, re-injecting the whole map on every message. The 2nd message must be SILENT in all N.
  rep=0
  for p in $(seq 1 "$NFP"); do
    s2=$(printf '{"session_id":"prova1","hook_event_name":"UserPromptSubmit"}' \
      | MAPA_LOG="$lg3" MAPA_ESTADO="$est3" "$0" --parte "$p" 2>/dev/null)
    [ -z "$s2" ] || { echo "  ✗ 2nd message: part $p RE-EMITTED ${#s2} B"; rep=1; }
  done
  if [ "$rep" = 0 ]; then echo "  ✓ 2nd message: no part re-emits"; ok=$((ok+1)); else ruim=$((ruim+1)); fi

  # CORE: a single owner. If every instance counted, the counter would move $NFP per message (the
  # core would return too early) and it would come out $NFP times in a row in the same message.
  nuc_turnos=""; nuc_vezes=0
  t=1  # the 2nd message above was already turn 1
  while [ "$t" -lt "$CADA_N" ]; do
    t=$((t+1)); saiu=0
    for p in $(seq 1 "$NFP"); do
      sn=$(printf '{"session_id":"prova1","hook_event_name":"UserPromptSubmit"}' \
        | MAPA_LOG="$lg3" MAPA_ESTADO="$est3" "$0" --parte "$p" 2>/dev/null)
      [ -z "$sn" ] || { saiu=$((saiu+1)); printf '%s' "$sn" | grep -q 'MAP — core' || echo "  ✗ turn $t part $p emitted something that is not the core"; }
    done
    [ "$saiu" -eq 0 ] || { nuc_turnos="$nuc_turnos $t"; nuc_vezes=$saiu; }
  done
  if [ "$nuc_turnos" = " $CADA_N" ] && [ "$nuc_vezes" = 1 ]; then
    echo "  ✓ core: returns ONCE, on turn $CADA_N — the rhythm has a single owner"; ok=$((ok+1))
  else
    echo "  ✗ core came out on turns [$nuc_turnos] ($nuc_vezes× on the last) — expected only turn $CADA_N, 1×"; ruim=$((ruim+1))
  fi

  # MARKER ISOLATION — one slice's mark cannot answer for another. If someone changes the file
  # name to something common to all, this test is what accuses it.
  est4=$(mktemp -d); : > "$est4/prova2.p1"
  s4=$(printf '{"session_id":"prova2","hook_event_name":"UserPromptSubmit"}' \
    | MAPA_LOG="$lg3" MAPA_ESTADO="$est4" "$0" --parte 2 2>/dev/null)
  s4b=$(printf '{"session_id":"prova2","hook_event_name":"UserPromptSubmit"}' \
    | MAPA_LOG="$lg3" MAPA_ESTADO="$est4" "$0" --parte 1 2>/dev/null)
  if [ -n "$s4" ] && [ -z "$s4b" ]; then
    echo "  ✓ isolated markers: p1 marked does not silence part 2, and silences part 1"; ok=$((ok+1))
  else
    echo "  ✗ contaminated markers: part 2 emitted ${#s4} B (expected >0), part 1 emitted ${#s4b} B (expected 0)"; ruim=$((ruim+1))
  fi
  # ── ASK THE TRANSCRIPT ───────────────────────────────────────────────────
  # Synthetic fixtures, one line per case. What is proven here is the PREDICATE — and it has three
  # known ways to lie: matching the mark outside a delivery, ignoring the compaction, and one part
  # answering for another. The three become tests.
  tdir=$(mktemp -d)
  linha_entrega() { printf '{"type":"user","attachment":{"type":"hook_success","hookName":"UserPromptSubmit","content":"<!-- mapa-hook: INITIAL LOAD \xc2\xb7 part %s of 3 \xc2\xb7 label -->\\n..."}}\n' "$1"; }
  linha_compact() { printf '{"type":"user","isCompactSummary":true,"message":{"role":"user","content":"summary..."}}\n'; }
  # THIS is the negative-control line: the mark appears in a command of MINE, not in a delivery.
  linha_citacao() { printf '{"type":"assistant","message":{"content":[{"type":"tool_use","input":{"command":"grep mapa-hook: INITIAL LOAD \xc2\xb7 part %s of 3 in the transcript"}}]}}\n' "$1"; }
  roda_t() {  # $1=transcript  $2=part → echoes the emitted size
    local est; est=$(mktemp -d)
    printf '{"session_id":"provat","hook_event_name":"UserPromptSubmit"}' \
      | MAPA_LOG=/dev/null MAPA_ESTADO="$est" MAPA_TRANSCRIPT="$1" "$0" --parte "$2" 2>/dev/null | wc -c
    rm -rf "$est"
  }
  { linha_entrega 1; linha_entrega 2; linha_entrega 3; } > "$tdir/t_entregue"
  { linha_entrega 1; linha_entrega 2; linha_entrega 3; linha_compact; } > "$tdir/t_compactado"
  { linha_compact; linha_entrega 1; } > "$tdir/t_pos_compact"
  { linha_citacao 1; linha_citacao 2; linha_citacao 3; } > "$tdir/t_so_citacao"
  : > "$tdir/t_vazio"
  # BIG CASE — it exists because the small fixtures HID the pipefail/SIGPIPE defect. It needs
  # enough volume that `tac` is still writing when `grep -m1` exits.
  { yes '{"type":"user","message":{"role":"user","content":"filler noise to give some volume"}}' \
      | head -40000; linha_entrega 1; } > "$tdir/t_grande"
  tok=1
  [ "$(roda_t "$tdir/t_entregue" 2)" = 0 ] || { echo "  ✗ transcript: slice 2 ALREADY delivered and the hook re-emitted — the fork duplicate is back"; tok=0; }
  [ "$(roda_t "$tdir/t_compactado" 2)" -gt 0 ] || { echo "  ✗ transcript: a delivery BEFORE the compact treated as alive — the map would not come back after compacting"; tok=0; }
  [ "$(roda_t "$tdir/t_pos_compact" 1)" = 0 ] || { echo "  ✗ transcript: a delivery AFTER the compact ignored — would re-emit for nothing"; tok=0; }
  [ "$(roda_t "$tdir/t_pos_compact" 2)" -gt 0 ] || { echo "  ✗ transcript: part 1 in context silenced part 2 — one part answering for another"; tok=0; }
  [ "$(roda_t "$tdir/t_so_citacao" 1)" -gt 0 ] || { echo "  ✗ transcript: the CITED mark (my command/text) passed as a delivery — predicate too wide"; tok=0; }
  [ "$(roda_t "$tdir/t_vazio" 1)" -gt 0 ] || { echo "  ✗ empty transcript: did not emit — the new session would be born without the map"; tok=0; }
  [ "$(roda_t "$tdir/nao_existe" 1)" -gt 0 ] || { echo "  ✗ ABSENT transcript: did not emit — it must fail towards emitting"; tok=0; }
  [ "$(roda_t "$tdir/t_grande" 1)" = 0 ] || { echo "  ✗ BIG transcript ($(wc -l < "$tdir/t_grande") lines): re-emitted — it is the pipefail/SIGPIPE of 'tac | grep -m1', invisible on a small fixture"; tok=0; }
  if [ "$tok" = 1 ]; then
    echo "  ✓ transcript decides: delivered→silent · before compact→emits · citation does not count · absent→emits"; ok=$((ok+1))
  else ruim=$((ruim+1)); fi
  rm -rf "$tdir"

  # `--parte` outside 1..N (the map shrank, settings stayed behind): does not emit, and SAYS so in the log.
  s5=$(printf '{"session_id":"prova3","hook_event_name":"UserPromptSubmit"}' \
    | MAPA_LOG="$lg3" MAPA_ESTADO="$est4" "$0" --parte $((NFP+1)) 2>/dev/null)
  if [ -z "$s5" ] && grep -q "emitted=invalid-part$((NFP+1))" "$lg3"; then
    echo "  ✓ --parte $((NFP+1)) (nonexistent): does not emit and SHOUTS in the log"; ok=$((ok+1))
  else
    echo "  ✗ --parte $((NFP+1)): emitted ${#s5} B and/or did not log 'invalid-part' — silent failure"; ruim=$((ruim+1))
  fi
  rm -rf "$est3" "$est4" "$lg3"

  # NEGATIVE CONTROL — without it the guard above would pass even if the script ALWAYS reset, which
  # would re-inject the whole load on every message. A normal prompt must keep COUNTING.
  #   The state is planted AGAIN, on purpose: inheriting what the test above left would make one
  # defect in the compact branch fail BOTH tests — 1 defect becoming 2 failures, and the count would
  # stop saying how many things are broken.
  rm -f "$est2"/provac.p* 2>/dev/null; printf '0' > "$est2/provac.n"
  saida3=$(printf '{"session_id":"provac","hook_event_name":"UserPromptSubmit"}' \
    | MAPA_LOG="$lg2" MAPA_ESTADO="$est2" "$0" 2>/dev/null)
  cont3=$(cat "$est2/provac.n" 2>/dev/null)
  if [ "$cont3" = "1" ] && [ -n "$saida3" ]; then
    echo "  ✓ control: a normal prompt moves 0→1 and emits slice 1 ($(printf '%s' "$saida3" | wc -c) B)"; ok=$((ok+1))
  else
    echo "  ✗ control FAILED: counter='$cont3' (expected 1), emitted $(printf '%s' "$saida3" | wc -c) B (expected >0)"; ruim=$((ruim+1))
  fi
  rm -rf "$est2" "$lg2"

  echo "== $ok ok · $ruim failure(s) =="
  [ "$ruim" -eq 0 ] || exit 1
  exit 0
fi
#   `--n-fatias` exists so the selftest's DETERMINISM CONTROL can invoke itself in another
# environment without recursion.
[ "${1:-}" = "--n-fatias" ] && { n_fatias; exit 0; }
[ "${1:-}" = "--full" ]   && { completo; exit 0; }
[ "${1:-}" = "--nucleo" ] && { nucleo;   exit 0; }

# ── real path: called as a hook ─────────────────────────────────────────────
# `--parte N` holds on BOTH events.
PARTE=""; [ "${1:-}" = "--parte" ] && PARTE="${2:-}"
entrada="$(cat 2>/dev/null || true)"
# The payload fields, read in ONE python3 call (python3 is already required by hipo-config.sh; jq is
# not). An absent, null or false field, or a payload that is not a JSON object, reads as empty.
_j_session_id=""; _j_hook_event_name=""; _j_source=""; _j_transcript_path=""
eval "$(printf '%s' "$entrada" | python3 -c '
import json, shlex, sys
try:
    d = json.loads(sys.stdin.read())
except Exception:
    d = {}
if not isinstance(d, dict):
    d = {}
for k in sys.argv[1:]:
    v = d.get(k)
    v = "" if v is None or v is False else (v if isinstance(v, str) else json.dumps(v))
    print("_j_%s=%s" % (k, shlex.quote(v)))
' session_id hook_event_name source transcript_path 2>/dev/null)"
sid="$_j_session_id"
[ -n "$sid" ] || sid="sem-sessao"
sid="$(printf '%s' "$sid" | tr -cd 'A-Za-z0-9._-')"
evento="$_j_hook_event_name"
fonte="$_j_source"
# The runtime sends the transcript path in the payload. If it ever stops, the log says so
# (`slice1-no-transcript`) and the script falls back to the marker — the old behaviour, not a break.
TRANSCRIPT="${MAPA_TRANSCRIPT:-$_j_transcript_path}"

mkdir -p "$ESTADO_DIR" 2>/dev/null || exit 0
f="$ESTADO_DIR/$sid.n"
# ONE MARKER PER SLICE, AND EACH PROCESS ONLY TOUCHES ITS OWN — this is what kills the race.
#   With N commands registered on the same event, N processes run at the same time. Exclusive owner
# per file = no process reads state another one writes. No lock, no ordering.
marca() { printf '%s/%s.p%s' "$ESTADO_DIR" "$sid" "$1"; }

# ── ASK THE TRANSCRIPT, NOT MY OWN FILE ─────────────────────────────────────
# THE MARKER WAS A PROXY, AND THE PROXY LIED ON A FORK.
#   The desktop app does not resume a conversation, it FORKS it, and the fork COPIES the history.
# New session, new `session_id`, empty markers — but the map IS ALREADY in the context, because it
# came with the copy. The marker answered "did I deliver in this session?"; the question is "is it
# in the context?". Cost of the error: a full duplicate of the map on every fork.
#   The transcript IS the thing: every hook delivery becomes a line
# `"attachment":{"type":"hook_success",…,"content":"<!-- mapa-hook: INITIAL LOAD · part N of M …"`.
#
# And "the mark is in the file" is NOT enough — TWO TRAPS:
#   (1) **The transcript keeps what left the context.** After a compact the old lines remain in the
#       jsonl, but the model no longer sees them. So the scan goes BACKWARDS and stops at the first
#       hit: if what comes first is the compaction line, the slice **fell** and must come back.
#   (2) **The mark appears outside a delivery** — in my own commands and text. So the predicate
#       requires `"type":"hook_success"` ON THE SAME LINE. A predicate too wide "finds" anywhere.
#
# FAIL TOWARDS EMITTING. No transcript, unreadable, or in doubt → return false and the slice goes
# out. Duplicating costs context; missing costs the layer — and missing is silent, which is what kills.
# THIS SCRIPT'S `pipefail` KILLED THIS PREDICATE, and only a REAL transcript exposed it.
#   `grep -m1` exits on the first hit; `tac` on the other side still has file to write and dies of
# SIGPIPE (141). With `set -o pipefail` the pipeline status becomes 141 even though grep found it —
# the predicate said "not in context" ALWAYS, on a big file. The fixtures did not catch it: on a
# 5-line transcript `tac` finishes before grep exits. Hence the BIG-transcript case in the selftest.
#   Fix: capture into a variable (the substitution runs in a subshell with pipefail off) and decide
# by the CONTENT of the hit, not by the pipeline status.
no_contexto_vivo() {  # $1 = part · 0 = already in the live context (do NOT emit)
  [ -n "${TRANSCRIPT:-}" ] && [ -r "$TRANSCRIPT" ] || return 1
  local achado
  achado=$(set +o pipefail
    LC_ALL=C tac -- "$TRANSCRIPT" 2>/dev/null \
      | LC_ALL=C grep -m1 -aE '"isCompactSummary":true|"type":"hook_success".*mapa-hook: INITIAL LOAD.*part '"$1"' of' 2>/dev/null) || true
  case "$achado" in
    *'"type":"hook_success"'*) return 0 ;;   # the delivery is the most recent thing → it is in context
    *) return 1 ;;                           # compaction in front, or nothing: emit
  esac
}
registra() {  # $1 = what it emitted   (the heartbeat is the ONLY proof the hook is registered)
  { printf '%s sid=%s turn=%s emitted=%s\n' "$(date '+%F %T')" "$sid" "${2:-0}" "$1" \
      >> "${MAPA_LOG:-$HIPO_LOG_DIR/mapa-hook.log}"; } 2>/dev/null
}

# COMPACTION — THE HOLE THAT ALMOST MADE THIS MAP A SANDCASTLE.
#   When the window fills, the runtime summarizes the conversation and **the slices vanish with the
# rest of the history**. The `session_id` does NOT change, so the counter continues where it was —
# and the rule `n <= NF` passed long ago. Result: the map goes away and **does not come back**. And
# it is WORSE than "wait for the next core": the core carries only layers 1 and 3, so **layer 2
# would NEVER come back** after a compact. Compaction is not rare: about half of the measured
# sessions compacted at least once.
#   The runtime calls the `SessionStart` hooks with `source="compact"` during the compaction, and
# what they print enters the context.
#
# `PostCompact` LOOKS like the right event BY NAME AND DOES NOT WORK — checked in the binary before
# choosing: its output is wrapped as a display message for the user's SCREEN, not context for the
# model. Registering there would give a running hook, a growing log, a green heartbeat and **zero
# arriving**.
#
# Because the 10,000-char ceiling is PER REGISTERED COMMAND (measured with two probes of 5,149
# chars: both arrived whole, 10,298 in the same turn), the compact event registers the script N
# times (`--parte 1..N`): each instance emits ONE slice and the whole map is back before the next
# user message. Each slice still says "part N of M" because the order is not guaranteed.
#   The slice delivered here MARKS its own file — UserPromptSubmit reads the mark and does not
# re-emit. The turn counter goes to ZERO because it only measures the core rhythm, which restarts.
#   Without `--parte` the behaviour is the fallback (delete the marks, reset, emit nothing) — proven,
# and what runs if someone registers the event without an argument.
if [ "$evento" = "SessionStart" ] && [ "$fonte" = "compact" ]; then
  NFC=$(n_fatias)
  if [ -n "$PARTE" ] && [ "$PARTE" -ge 1 ] 2>/dev/null && [ "$PARTE" -le "$NFC" ] 2>/dev/null; then
    : > "$(marca "$PARTE")" 2>/dev/null
    printf '0' > "$f" 2>/dev/null
    registra "compact-slice$PARTE" 0
    fatia "$PARTE"
  else
    rm -f "$ESTADO_DIR/$sid".p* 2>/dev/null
    printf '0' > "$f" 2>/dev/null
    registra reset-compact 0
  fi
  exit 0
fi

# Cleanup: state of a session idle for more than 3 days is useless. Includes the slice markers —
# otherwise an old session leaves `.pN` garbage forever.
find "$ESTADO_DIR" -maxdepth 1 \( -name '*.n' -o -name '*.p*' \) -mtime +3 -delete 2>/dev/null

# ── UserPromptSubmit with --parte: THE WHOLE LOAD ON THE FIRST TURN ─────────
#   Each instance asks ONE thing — "was MY slice already delivered in this session?" — and the
# answer lives in a file only it writes. On the 1st message no mark exists: the N emit together.
#   THE CORE RHYTHM HAS A SINGLE OWNER (part 1). If all counted, the counter would move N per
# message and the core would return N times earlier — and N times in a row, one per instance.
if [ -n "$PARTE" ]; then
  NF=$(n_fatias)
  if [ "$PARTE" -ge 1 ] 2>/dev/null && [ "$PARTE" -le "$NF" ] 2>/dev/null; then
    m="$(marca "$PARTE")"
    if [ ! -e "$m" ]; then
      # Cold marker = new session OR fork. Only here is the transcript worth reading (once per
      # session, per part); on the next turns the marker answers for free.
      if no_contexto_vivo "$PARTE"; then
        : > "$m" 2>/dev/null
        registra "already-in-context$PARTE" 1
      else
        : > "$m" 2>/dev/null
        if [ -n "$TRANSCRIPT" ]; then registra "slice$PARTE" 1
        else registra "slice$PARTE-no-transcript" 1; fi
        fatia "$PARTE"
      fi
      exit 0
    fi
    if [ "$PARTE" = 1 ]; then
      n=$(cat "$f" 2>/dev/null || echo 0); n=$((n+1)); printf '%s' "$n" > "$f" 2>/dev/null
      if [ $(( n % CADA_N )) -eq 0 ]; then registra core "$n"; nucleo
      else registra nothing "$n"; fi
    fi
    exit 0
  fi
  # `--parte` outside 1..N: the map SHRANK and settings stayed behind. Nothing to emit, but the log
  # shouts — from the outside, "did not emit because it does not exist" and "did not emit because
  # it broke" are identical.
  registra "invalid-part$PARTE" 0
  exit 0
fi

# ── LEGACY path (no --parte): one slice per turn ────────────────────────────
# Still alive because it is what runs if someone registers the hook without an argument — and
# because it is the negative control of --selftest: if this branch stops counting, the load would
# come back on every message.
n=$(cat "$f" 2>/dev/null || echo 0); n=$((n+1)); printf '%s' "$n" > "$f" 2>/dev/null

NF=$(n_fatias)

# HEARTBEAT — the only proof that the hook is REGISTERED and running.
#   Whoever writes the hook cannot test it from inside their own session: Claude Code reads settings
# at boot, so a schema error makes the hook simply NOT RUN — no error, no warning. This log is the
# TARGET to ask: if it does not grow in a new session, the registration is wrong, not the script.
#   It already lied once: `$NF` was read HERE and only assigned two lines below, so `emitted=` came
# out EMPTY, and the `2>/dev/null` that keeps the log from breaking the session swallowed the
# unset-variable error. Hence `NF` is resolved ABOVE, and --selftest checks the field is filled.
{ printf '%s sid=%s turn=%s emitted=%s\n' "$(date '+%F %T')" "$sid" "$n" \
    "$(if [ "$n" -le "$NF" ]; then echo "slice$n"; elif [ $(( n % CADA_N )) -eq 0 ]; then echo core; else echo nothing; fi)" \
    >> "${MAPA_LOG:-$HIPO_LOG_DIR/mapa-hook.log}"; } 2>/dev/null

if [ "$n" -le "$NF" ]; then
  fatia "$n"                       # initial load: one slice per turn, as many as there are
elif [ $(( n % CADA_N )) -eq 0 ]; then
  nucleo
fi
exit 0
