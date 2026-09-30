#!/usr/bin/env bash
# memory-guards.sh -- the memory guards of the CI battery, as executable checks.
#
# PRINCIPLE: turn a WRITTEN rule into an EXECUTABLE check. Every guard below defends a rule that
# used to depend on someone remembering it. Each guard names the rule it defends; the rules are
# written up in docs/guardas/memoria.md.
#
#   guarda_memoria_indice_integro                      the index and the disk agree (dead
#                                                      citation, orphan memory, caps, mirror)
#   guarda_memoria_description_sem_estado_transiente   a description names the SUBJECT, not a
#                                                      transient state
#   guarda_memoria_nao_afirma_lei_morta                the index does not restate a law the map
#                                                      already REVOKED or POSTPONED
#   guarda_memoria_cascata                             the rule<->case cascade (delegates to
#                                                      scripts/guarda-cascata.py)
#   guarda_memoria_bastao_entrega_estado_vivo          the compaction hook delivers live state
#                                                      (delegates to scripts/bastao-entrega.py)
#
# GOLDEN RULE: what is ALREADY in production is not failed retroactively.
#   --staged (hook): what is being born now -> a new convention is a FAILURE.
#   --tree  (audit): full sweep -> a new convention is a WARNING; only structural rules FAIL.
# A CI that opens red on code that has been stable for months is switched off on day one.
#
# NO ROUTER: the lab version of this battery can let a guard sleep when a commit does not touch
# what it reads. The public battery does not ship that router: every guard runs every time. The
# only gates left are the repository-signature gates of the driver (the memory guards run where
# `docs/mapa/` exists; the baton guard where the hooks file or `docs/mesa/` exists), so a repo
# without a memory store is not failed for lacking one.
#
# PATHS (from scripts/hipo-config.sh, overridable per run):
#   MEM_DIR      the memory folder              (default: $HIPO_MEMORY_DIR)
#   MEM_INDEX    the index read by the dead-law guard (default: $MEM_DIR/MEMORY.md)
#   MEM_ESPELHO  the mirror of the memory folder (default: `memoria`, relative to the repo root)
#                The mirror is OPTIONAL (scripts/memoria-espelho.sh, run by your scheduler). It counts as
#                CONFIGURED when MEM_ESPELHO is set explicitly, or when git tracks at least one file under
#                the mirror path (the mirror script commits there, so its first run leaves this trace).
#                Configured and absent = FAILURE (the backup vanished). Not configured and absent =
#                WARNING (a fresh setup that has not enabled the mirror yet).
#   MEM_SONDA / MEM_IDS  the cap probe and the citation resolver (default: scripts/ of the judged
#                repo when it has them, else scripts/ of this checkout)
#   BASTAO_SETTINGS      the hooks file the baton guard reads (default: settings.example.json)
#
# Usage:
#   memory-guards.sh            # --tree: sweeps the whole tree (default)
#   memory-guards.sh --tree
#   memory-guards.sh --staged   # same guards; a new-convention violation becomes red
#   memory-guards.sh --help
# rc 1 if any guard is red, 0 otherwise. Conscious bypass: git commit --no-verify (and own the debt).

set -uo pipefail

MODO="tree"
while [ $# -gt 0 ]; do
  case "$1" in
    --tree)   MODO="tree" ;;
    --staged) MODO="staged" ;;
    --help|-h) sed -n '2,48p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) echo "memory-guards: unknown option '$1' (use --help)" >&2; exit 2 ;;
  esac
  shift
done

PUB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../scripts/hipo-config.sh
. "$PUB/scripts/hipo-config.sh"
MEM_DIR="${MEM_DIR:-$HIPO_MEMORY_DIR}"
MEM_INDEX="${MEM_INDEX:-$MEM_DIR/MEMORY.md}"

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "memory-guards: outside a git repo" >&2; exit 2; }
cd "$ROOT" || exit 2

# A script the guards delegate to: the judged repo's own copy when it has one, else this checkout's.
_script() { if [ -f "$ROOT/scripts/$1" ]; then printf '%s' "$ROOT/scripts/$1"; else printf '%s' "$PUB/scripts/$1"; fi; }

FALHAS=0; AVISOS=0; RODADOS=0

_titulo()  { printf '\033[%sm%s %s\033[0m\n' "$1" "$2" "$3"; shift 3; for l in "$@"; do printf '    %s\n' "$l"; done; }
vermelho() { _titulo 31 '✗' "$@"; FALHAS=$((FALHAS+1)); }
amarelo()  { _titulo 33 '!' "$@"; AVISOS=$((AVISOS+1)); }
verde()    { printf '\033[32m✓ %s\033[0m\n' "$1"; }
conta()    { RODADOS=$((RODADOS+1)); }
conta_desconta() { RODADOS=$((RODADOS-1)); }  # closed gate: the guard did not run, and the counter must not say it did
# Truncates the list, but NEVER silently: a list cut without notice reads as "that is all".
detalhe() {
  local todas n; todas="$(grep -v '^$')"; n=$(printf '%s\n' "$todas" | grep -c '' )
  printf '%s\n' "$todas" | head -6 | while IFS= read -r l; do printf '      %s\n' "$l"; done
  [ "$n" -gt 6 ] && printf '      ... and %s more\n' "$((n-6))"
  return 0
}

# A convention that does not apply retroactively: fails what is born now, warns on a tree audit.
novo_viola() { [ "$MODO" = staged ] && vermelho "$@" || amarelo "$@"; }

# ── the guards ────────────────────────────────────────────────────────────────────────────────

guarda_memoria_bastao_entrega_estado_vivo() {
  conta
  # The compaction hook delivers the baton without live state: the fixed head ate the 2,000-unit preview.
  # doc: docs/guardas/memoria.md
  #   WHAT IT PROTECTS: the compaction hook `cat`s the baton (~100 KB) and the runtime puts only the
  # PREVIEW of 2,000 units into context. A fixed head at the top of the baton filled the whole preview:
  # measured, 0 of 72 persisted deliveries carried live state. The head moved to
  # docs/mesa/BASTAO_REGRAS.md, and the top of the baton keeps a 1-line pointer.
  #   IT STARTS FROM THE HOOK, NOT FROM THE PATH: the piece reads the `SessionStart` that matches
  # `compact` in the hooks file, simulates each `cat` and judges what the runtime DELIVERS. An emitter
  # it cannot simulate (a script, a cut) comes out RED: whoever changes the emitter teaches the
  # simulation in the same commit. `PostCompact` does not count: it only reaches the echo of a manual
  # `/compact`, never the automatic one (docs/CONTEXTO.md).
  #   It DELEGATES to the piece: the preview emulation lives ONCE, in scripts/bastao-entrega.py, and it
  # is the same one `--validar` checks against the real previews of the transcripts.
  #   THE PIECE THAT JUDGES IS THE COMMIT'S: in the hook it comes from the INDEX -- a draft lying in the
  # tree judges nobody's commit. Outside the repo (the fixture battery runs in a temporary tree) it
  # comes from this checkout's scripts/.
  local fonte="${BASTAO_SETTINGS:-settings.example.json}" peca="scripts/bastao-entrega.py" tmp="" saida cabeca
  command -v python3 >/dev/null 2>&1 || { amarelo "memory/baton: no python3 -- the hook delivery was not verified"; return; }
  if [ "$MODO" = staged ] && git cat-file -e ":$peca" 2>/dev/null; then
    tmp=$(mktemp "${TMPDIR:-/tmp}/bastao-entrega-XXXXXX.py") && git show ":$peca" > "$tmp" && peca="$tmp"
  elif [ ! -f "$peca" ]; then
    peca="$PUB/scripts/bastao-entrega.py"
  fi
  if [ ! -f "$peca" ]; then
    amarelo "memory/baton: scripts/bastao-entrega.py missing -- the compaction hook delivery was not verified"
    return
  fi
  if ! saida=$(python3 "$peca" --selftest 2>&1); then
    [ -n "$tmp" ] && rm -f "$tmp"
    vermelho "memory/baton: the INSTRUMENT is broken (selftest failed)" \
      "run: python3 scripts/bastao-entrega.py --selftest"
    printf '%s\n' "$saida" | grep -E '✗' | detalhe
    return
  fi
  saida=$(BASTAO_SETTINGS="$fonte" python3 "$peca" --guarda "$MODO" 2>&1)
  [ -n "$tmp" ] && rm -f "$tmp"
  cabeca=$(printf '%s\n' "$saida" | head -1)
  case "$cabeca" in
    VERDE)
      verde "memory/baton: the compaction hook delivers live state -- $(printf '%s\n' "$saida" | sed -n 2p)" ;;
    AUSENTE)
      amarelo "memory/baton: no $fonte -- the compaction hook delivery was not verified" ;;
    JSON)
      vermelho "memory/baton: $fonte is not valid JSON -- there is no way to know what the hook delivers"
      printf '%s\n' "$saida" | tail -n +2 | detalhe ;;
    SEM_EMISSOR)
      vermelho "memory/baton: SessionStart:compact does not emit the baton through an emitter the guard simulates (\`cat\` or the piece's cut)" \
        "what arrives is decided by the hook ($fonte); a new emitter -> teach the simulation to the piece in the same commit" \
        "PostCompact does not count: it only reaches the echo of a manual /compact, never the automatic one (docs/CONTEXTO.md)"
      printf '%s\n' "$saida" | tail -n +2 | detalhe ;;
    CABECA)
      vermelho "memory/baton: the head grew back at the top of the baton" \
        "rule: 1 pointer line and the live state right after; what it is and its rules live in docs/mesa/BASTAO_REGRAS.md"
      printf '%s\n' "$saida" | tail -n +2 | detalhe ;;
    SEM_ESTADO)
      vermelho "memory/baton: what the compaction hook DELIVERS carries no live state" \
        "the runtime delivers only the 2,000-unit preview; live state = the *Updated: line and >=1 entry (- ) inside it" \
        "fix: the fixed head lives in docs/mesa/BASTAO_REGRAS.md; the top of BASTAO.md keeps 1 pointer line"
      printf '%s\n' "$saida" | tail -n +2 | detalhe ;;
    *)
      vermelho "memory/baton: the INSTRUMENT broke -- unexpected output from --guarda"
      printf '%s\n' "$saida" | detalhe ;;
  esac
}

guarda_memoria_description_sem_estado_transiente() {
  conta
  # Memory: a description stating a TRANSIENT state -- it is the recall key, and it rots.
  # doc: docs/guardas/memoria.md
  #   WHAT IT PROTECTS: the `description` is the SUMMARY read first inside the file, and it is what a
  # search matches. A wrong statement there is not a wrong detail -- it is the wrong summary served as
  # the subject. (There is no automatic recall in this installation: when the description arrives, the
  # body came with it. The guard survives for the reason above.)
  #   Measured case: a description said "in staging, waiting for validation; local commit, no push"
  # while the body said "in production since last month, pushed". The summary served the lie, and the
  # body -- which was right -- was never read.
  #   IT DOES NOT BAN STATE, and the distinction was measured: most descriptions that state a state
  # state a TERMINAL one (in production, resolved, live). Terminal does not rot backwards. What rots is
  # the TRANSIENT: pending, waiting, in progress, in staging. It was 3 of 187, and all 3 were rewritten.
  #   The rule: the description says the SUBJECT of the memory (what it keeps, and why one would open
  # it); the STATE lives in the body, dated, where the new line goes in chronological order.
  #   PUBLIC PORT: the lab's vocabulary was Portuguese; the words below are its English equivalents.
  local dir="$MEM_DIR"
  if [ ! -d "$dir" ]; then
    amarelo "memory: $dir does not exist -- guard without population"
    return
  fi
  local saida
  saida=$(MEM_D="$dir" python3 - <<'PYX'
import os, re, pathlib
d = pathlib.Path(os.environ['MEM_D'])
RX = re.compile(r"\b(PENDING|pending|waiting|WAITING|in progress|IN PROGRESS"
                r"|IN STAGING|in staging|WIP|not promoted|in review)\b")
ruins, n = [], 0
for f in sorted(d.glob("*.md")):
    if f.name == "MEMORY.md":
        continue
    n += 1
    m = re.search(r"^description:\s*(.*)$", f.read_text(encoding="utf-8", errors="replace"), re.M)
    if m and RX.search(m.group(1)):
        ruins.append("%s -> %s" % (f.name, "/".join(sorted(set(RX.findall(m.group(1)))))))
print("N|%d" % n)
for r in ruins:
    print("FAIL|%s" % r)
PYX
)
  local n; n=$(printf '%s\n' "$saida" | sed -n 's/^N|//p')
  if printf '%s' "$saida" | grep -c '^FAIL|' >/dev/null; then
    vermelho "memory: description stating a TRANSIENT state -- it is the recall key, and it rots" \
      "rule: the description says the SUBJECT; the STATE lives in the body, dated" \
      "measured: a description said IN STAGING while the body said IN PRODUCTION" \
      "a TERMINAL state (in production, resolved) is accepted -- it does not go backwards"
    printf '%s\n' "$saida" | sed -n 's/^FAIL|/  /p' | detalhe
  else
    verde "memory: $n description(s), none stating a transient state in the recall key"
  fi
}

guarda_memoria_cascata() {
  conta
  # The rule<->case cascade: link, `prova:` count, revocation with a reason, acceptance.
  # doc: docs/guardas/memoria.md
  #   It DELEGATES to the piece itself (scripts/guarda-cascata.py) instead of recounting here: a new
  # guard that reimplements an existing count creates a SECOND TRUTH.
  local dir="$MEM_DIR"
  if [ ! -d "$dir" ]; then
    amarelo "cascade: $dir does not exist -- guard without population" \
      "zero is not a result: either the path changed, or this guard went blind"
    return
  fi
  local saida
  if saida=$(python3 "$(_script guarda-cascata.py)" "$dir" 2>&1); then
    verde "memory: cascade intact ($(ls "$dir"/*.md 2>/dev/null | wc -l) file(s))"
  else
    vermelho "memory: the rule<->case cascade broke" \
      "dead link, \`prova:\` count off, revocation without a reason, or an orphan case" \
      "$(printf '%s' "$saida" | sed 's/^/        /')"
  fi
}

guarda_memoria_indice_integro() {
  # @guard memory index · covers the law P9: every memory file has one line in the index
  conta
  # Memory: the index and the disk diverged -- and a memory outside the index DOES NOT LOAD.
  # doc: docs/guardas/memoria.md
  local dir="$MEM_DIR"
  if [ ! -d "$dir" ]; then
    amarelo "memory: $dir does not exist -- guard without population" \
      "zero is not a result: either the path changed, or this guard went blind"
    return
  fi
  local saida esp_conf=0
  #   THE SIGNAL THAT THE MIRROR IS CONFIGURED is what the operator or the mirror itself leaves: the
  # variable set by hand, or files under the mirror path in git (memoria-espelho.sh commits there).
  # There is no config key for it: a key nobody reads would be a second, silent truth.
  if [ -n "${MEM_ESPELHO+x}" ] || [ -n "$(git ls-files -- "${MEM_ESPELHO:-memoria}" 2>/dev/null | head -1)" ]; then
    esp_conf=1
  fi
  saida=$(MEM_D="$dir" MEM_TETO="${MEM_TETO:-24576}" MEM_ESP="${MEM_ESPELHO:-memoria}" MEM_ESP_CONF="$esp_conf" \
    MEM_SONDA="${MEM_SONDA:-$(_script memory-cap-probe.py)}" \
    MEM_IDS="${MEM_IDS:-$(_script memoria_ids.py)}" python3 - <<'PY'
import os, re, pathlib, sys
d = pathlib.Path(os.environ['MEM_D']); teto = int(os.environ['MEM_TETO'])
idx = d / 'MEMORY.md'
if not idx.is_file():
    print('FAIL|index %s missing -- nothing loads into context' % idx); sys.exit(0)
txt = idx.read_text(encoding='utf-8')
#   THE PREDICATE MATCHES THREE FORMATS of the index: a markdown link, a bare file name in pointer
# position, and the citation `[N]` (today's). When the index changed format, the old regex alone
# found ZERO and accused every memory as orphan at once -- that was this guard's positive control.
#   THE HYPHEN IS PART OF THE NAME (a_note_2026-06-18.md): without it in the class, the predicate cuts
# at the hyphen. Uppercase stays OUT on purpose: it keeps repo docs cited in prose (LIFECYCLE.md,
# 3_DECIDIDO.md) from becoming "dead pointers".
#   POSITION, NOT PRESENCE: a prose line explaining the format ("the pointer is the bare file name
# (name.md)") was accused as a dead pointer. Where real pointers live was measured before writing
# the predicate: at line start, after ` - `, after `:`.
#   TWO AXES, AND THEY WANT OPPOSITE WIDTHS:
#   . "DEAD pointer" (name cited that does not exist on disk) wants the NARROW predicate: if wide,
#     prose becomes data.
#   . "ORPHAN memory" (file the index never cites) wants the WIDE predicate: if narrow, a real entry
#     written with punctuation it does not know disappears, and the guard BLOCKS a correct commit.
#   The cost of error is asymmetric and decides it: a false orphan BLOCKS legitimate work; a dead
# pointer that escapes is a dirty line the next pass catches.
#   THE INDEX BECAME CITATIONS, and both axes would go blind in OPPOSITE directions if this block did
# not resolve `[N]`: the wide one finds zero names and accuses every memory (loud red); the narrow one
# also finds zero and comes out GREEN in silence -- which is worse: a green guard on the wrong axis
# answers "all is well" with authority.
#   The number->name resolution is NOT redone here: it lives in scripts/memoria_ids.py. And a MISSING
# module is a FAILURE, never green: without it the guard cannot resolve any citation, and "found no
# pointer" would become "there is no pointer".
#   `p` (the findings list) is only born further down; accumulating in `_pend` first avoids a
# NameError that the anti-blindness branch would turn into "predicate DIED without a verdict".
_pend, _ids = [], {}
_mod = os.environ.get('MEM_IDS', '')
if not pathlib.Path(_mod).is_file():
    _pend.append('FAIL|citation resolver missing (%s) -- without it BOTH axes of this block '
                 'go blind, and blind is not green' % _mod)
else:
    import importlib.util
    _si = importlib.util.spec_from_file_location('memids', _mod)
    _mi = importlib.util.module_from_spec(_si); _si.loader.exec_module(_mi)
    _ids = {n: x.name for n, x in _mi.varre(d)[0].items()}
    _cit = {int(m.group(1)) for m in _mi.CITACAO.finditer(txt)}
    # a citation that does not resolve is a dead pointer of the NEW format -- same axis, other spelling
    for _n in sorted(_cit - set(_ids)):
        _pend.append('FAIL|dead citation in the index: [%d] resolves to no memory' % _n)
    _resolvidos = {_ids[n] for n in _cit & set(_ids)}
_POS = r'(?:^[ \t]*|[-:][ \t]+)([a-z0-9_][a-z0-9_-]*\.md)\b'
_PRES = r'\b([a-z0-9_][a-z0-9_-]*\.md)\b'
_LINK = r'\]\(([^)]+\.md)\)'
_resolvidos = locals().get('_resolvidos', set())
refs_pos = set(re.findall(_POS, txt, re.M)) | set(re.findall(_LINK, txt)) | _resolvidos   # narrow
refs_pres = set(re.findall(_PRES, txt)) | set(re.findall(_LINK, txt)) | _resolvidos       # wide
#   PARKED: an index block taken out of load lives in `indice_*_estacionado.md`
# (scripts/memoria-estaciona.py). A memory cited THERE is not orphan -- it is PARKED, out of load by
# decision, and opens by `memoria-resolve.py N` as always. Without this clause parking was impossible
# by construction. A dead citation in a parked block is a FAILURE like one in the index.
_mi_ = locals().get('_mi')
_est_txt = ''.join(q.read_text(encoding='utf-8', errors='replace') for q in sorted(d.glob('indice_*_estacionado.md')))
_est_cit = {int(m.group(1)) for m in _mi_.CITACAO.finditer(_est_txt)} if _mi_ else set()
for _n in sorted(_est_cit - set(_ids)):
    _pend.append('FAIL|dead citation in a PARKED index: [%d] resolves to no memory' % _n)
_estacionadas = {_ids[n] for n in _est_cit & set(_ids)}
mortos = sorted(r for r in refs_pos if not (d / r).exists())
arq = {p.name for p in d.glob('*.md')} - {'MEMORY.md'}
orfas = sorted(arq - refs_pres - _estacionadas)
b = len(txt.encode())
# pace: an index line costs the measured average; what is left is said in LINES, not bytes
por_linha = max(1, b // max(1, len(arq)))
cabem = (teto - b) // por_linha
p = list(_pend)
for x in mortos: p.append('FAIL|dead pointer in the index: %s' % x)
for x in orfas:  p.append('FAIL|ORPHAN memory (never loads, and nothing accuses it): %s' % x)
if b > teto:     p.append('FAIL|index at %d B, ceiling %d -- time for the revolving door' % (b, teto))
#   THERE ARE TWO CAPS, AND THIS GUARD ONLY WATCHED ONE -- bytes. Measured: the index was at 72% of
# the byte ceiling (comfortable green) and at 185 LINES of 200 -- 7.5% left. The line axis is the one
# that cuts first. A green guard on the wrong axis is worse than no guard.
#   THE COUNT IS NOT REDONE HERE: it lives in scripts/memory-cap-probe.py, which has a `--selftest`
# with edge controls in both directions. A guard that reimplements an existing count creates a
# second truth, and the two diverge the day only one is fixed.
#   WHY A WARNING, NOT A FAILURE, BEFORE 200: cutting the index is the owner's decision. Red here would
# block EVERY commit until he decides, and a guard that blocks legitimate work becomes `--no-verify`
# by habit. Red only on the accomplished fact: past 200, it is already losing content.
eixo_linha = '(line axis NOT measured)'
#   PRESENT IS NOT COMPATIBLE. `is_file()` alone passes on an OLD probe without `metrics()`, and the
# AttributeError that follows would become an empty green (see the empty-output branch in the shell).
_sonda = os.environ.get('MEM_SONDA', '')
_pb = None
if not pathlib.Path(_sonda).is_file():
    p.append('FAIL|cap probe missing (%s) -- the LINE axis has no ruler, and that is not green' % _sonda)
else:
    import importlib.util
    _sp = importlib.util.spec_from_file_location('probe', _sonda)
    _pb = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_pb)
    if not hasattr(_pb, 'metrics'):
        p.append('FAIL|probe %s is OLD: it has no metrics() -- the LINE axis has no ruler '
                 '(the probe and this guard must move in the same commit)' % _sonda)
        _pb = None
if _pb is not None:
    mm = _pb.metrics(str(idx))
    piso = int(os.environ.get('MEM_PISO_LINHA', '15'))
    eixo_linha = '%d/%d lines (%d free)' % (mm['lines'], mm['lines_cap'], mm['lines_free'])
    if mm['lines'] > mm['lines_cap']:
        p.append('FAIL|index at %d LINES, cap %d -- IT IS ALREADY CUTTING: %s'
                 % (mm['lines'], mm['lines_cap'], _pb.measure(str(idx))))
    elif mm['lines_free'] < piso:
        p.append('WARN|index at %d lines from the cap of %d (floor %d) -- the LINE axis bites before the byte one; '
                 'cutting is the owner\'s decision, bring a proposal' % (mm['lines_free'], mm['lines_cap'], piso))
#   CEILING PER LINE -- the global ceiling alone let fat in line by line.
#   Measured: 25 entries of 150-400 B ate 28% of the index, and their excess was a COPY of the body
# (6 of 6 samples were already in the file) -- text paid in every session. Shortening the 49 entries
# above 80 B gave back 22%.
#   Why 80 and why HARD: the open rate per hook-length band was noise, not a curve -- a rich hook does
# NOT buy recall, so the ceiling costs no recall. And a named exception rots: a line that "needs more"
# is saying its content belongs in the body or in the map.
#   The hook answers "WHY would I open this?". Proof, number and path live in the body.
teto_linha = int(os.environ.get('MEM_TETO_LINHA', '80'))
#   `[N]` ENTERS HERE TOO, and this is the axis that would go quietest: without the citation
# alternative, `marcas` is EMPTY on every line and the 80 B ceiling simply STOPS EXISTING.
#   The `\b` stays INSIDE the name alternative, never after the group: `]` and the space after it are
# both non-word, so there is no boundary there -- with `\b` at the end, `[7]` never matches.
_ABRE = re.compile(r'(?:^[ \t]*|[-:·][ \t]+)((?:[a-z0-9_][a-z0-9_-]*)\.md\b|\[\d+\])')
gordas, atual = [], None
for linha in txt.split('\n'):
    if not linha.strip():
        continue
    marcas = list(_ABRE.finditer(linha))
    ind = len(linha) - len(linha.lstrip())
    if not marcas:
        if atual and ind > 2:            # continuation: belongs to the entry's last pointer
            atual[1] += len(linha.strip().encode()) + 1
        else:
            atual = None                 # title/prose: nobody's entry
        continue
    for i, m in enumerate(marcas):
        fim = marcas[i+1].start() if i+1 < len(marcas) else len(linha)
        atual = [m.group(1), len(linha[m.end():fim].strip(' -·').encode())]
        gordas.append(atual)
for nome, n in gordas:
    if n > teto_linha:
        p.append('FAIL|index line with %d B (ceiling %d per line): %s -- the excess goes to the body' % (n, teto_linha, nome))
#   THE MIRROR IS THE ONLY BACKUP -- none of the other backup paths touch the memory folder. A stale
# mirror gives no error: it gives silence, and silence only charges on the day of the restore.
esp = pathlib.Path(os.environ['MEM_ESP'])
if not esp.is_dir() and os.environ.get('MEM_ESP_CONF') == '1':
    p.append('FAIL|mirror %s does not exist -- the memories have no backup at all' % esp)
elif not esp.is_dir():
    #   OPTIONAL AND NOT CONFIGURED: a warning, never silence -- "no backup" must still be said.
    p.append('WARN|mirror not configured: %s does not exist and nothing under it is tracked -- the '
             'memories have no backup (optional: scripts/memoria-espelho.sh)' % esp)
else:
    no_esp = {x.name for x in esp.glob('*.md')}
    faltam = sorted((arq | {'MEMORY.md'}) - no_esp)
    sobram = sorted(no_esp - (arq | {'MEMORY.md'}))
    for x in faltam[:6]: p.append('FAIL|outside the mirror (a restore loses it): %s' % x)
    for x in sobram[:6]: p.append('FAIL|in the mirror and NOT in the source (rsync --delete did not run): %s' % x)
    #   "COMPLETE" USED TO COMPARE ONLY NAMES -- same name with different content came out GREEN. A
    # mirror that checks the list and not the content promises a backup and delivers a backup index.
    #   And the fix must NOT be raw red: between editing a memory and the hourly mirror job propagating
    # it, the divergence is LEGITIMATE. Red there would teach people to ignore the guard.
    #   So AGE separates the two cases: within one turn of the job it is a WARNING with the age stated;
    # past that, the job is not closing the loop and it becomes a FAILURE.
    import time
    difs, ilegiveis, mais_velha = [], [], 0.0
    agora = time.time()
    for nome in sorted((arq | {'MEMORY.md'}) & no_esp):
        f, e = d / nome, esp / nome
        try:
            if f.read_bytes() != e.read_bytes():
                difs.append(nome)
                mais_velha = max(mais_velha, agora - f.stat().st_mtime)
        except OSError as ex:
            #   A FILE THAT CANNOT BE READ IS NOT "STALE" -- it is a backup nobody knows exists, and it
            # must ALWAYS be a failure, never a warning. Before, it fell into `difs` and inherited the
            # age rule: with a recent mtime it became the yellow warning, the most reassuring sentence
            # in the repertoire at the wrong time. A broken symlink -- the natural residue of an
            # interrupted `mv` or rsync -- gives exactly the same result.
            ilegiveis.append('%s (%s)' % (nome, type(ex).__name__))
    for x in ilegiveis[:6]:
        p.append('FAIL|mirror UNREADABLE, and unreadable is not stale: %s' % x)
    if difs:
        idade = int(mais_velha // 60)
        amostra = ', '.join(difs[:3]) + ('...' if len(difs) > 3 else '')
        if idade <= 75:   # one turn of the hourly job, with slack for the run itself
            p.append('WARN|mirror with stale content in %d of %d (source edited %d min ago; '
                     'the hourly mirror job closes it): %s' % (len(difs), len(arq) + 1, idade, amostra))
        else:
            #   THE AGE IS THE SOURCE's mtime, not the instant the two diverged -- the disk does not
            # keep that instant. Re-editing the source REJUVENATES the divergence. That is why the
            # message says which clock it is talking about.
            p.append('FAIL|mirror stale in %d of %d, source edited %d min ago -- past one turn '
                     'of the mirror job, it is not closing: %s'
                     % (len(difs), len(arq) + 1, idade, amostra))
print('\n'.join(p) if p else
      'OK|%d memories · index %d B of %d (%d%%) · %s · ~%d B per line, room for +%d · mirror at %s '
      'complete and EQUAL byte by byte'
      % (len(arq), b, teto, b * 100 // teto, eixo_linha, por_linha, cabem, esp))
PY
)
  #   EMPTY OUTPUT WAS COMING OUT GREEN -- for ANY exception. It was enough for the predicate to raise in
  # the middle for `$( )` to return an empty string, no branch to match FAIL|/WARN|, and the `else` to
  # print a green check with no text, rc=0. The fix is for the CLASS: a predicate that produced no
  # verdict did not produce green.
  if [ -z "$(printf '%s' "$saida" | tr -d '[:space:]')" ]; then
    vermelho "memory: the guard's predicate DIED without a verdict -- empty output is NOT green" \
      "rule: a guard that could not measure declares blindness; it does not get the benefit of the doubt" \
      "look at the traceback right above this line: it is the cause, and the \`\$( )\` swallowed it"
  elif printf '%s' "$saida" | grep -c '^FAIL|' >/dev/null; then
    vermelho "memory: the index and the disk diverged -- and a memory outside the index DOES NOT LOAD" \
      "rule: only the index enters the context; each memory is read on demand" \
      "fix: one line per memory in MEMORY.md, and every pointer resolving in its folder" \
      "over the ceiling? the way out is the revolving door (became a doc/guard · obsolete leaves · siblings merge)"
    printf '%s\n' "$saida" | sed 's/^FAIL|/  /' | grep -v '^WARN|' | detalhe
  #   YELLOW is the divergence WITHIN one turn of the mirror job: legitimate, but said out loud.
  elif printf '%s' "$saida" | grep -c '^WARN|' >/dev/null; then
    #   THE TITLE MUST MATCH THE WARNING THAT CAME OUT: the line-headroom warning shares this pipe, and a
    # fixed title about the mirror would describe the wrong cause with authority.
    if printf '%s' "$saida" | grep -c '^WARN|index at ' >/dev/null; then
      amarelo "memory: the index is reaching the LINE cap -- and it bites before the byte one" \
        "cutting is the owner's decision: bring a proposal, do not execute"
    elif printf '%s' "$saida" | grep -c '^WARN|mirror not configured' >/dev/null; then
      amarelo "memory: no mirror configured -- the memory folder has NO backup" \
        "the mirror is optional; to enable it run scripts/memoria-espelho.sh from your scheduler" \
        "once configured (MEM_ESPELHO set, or the mirror tracked in git), an absent mirror is a FAILURE"
    else
      amarelo "memory: the mirror has not caught up with the source -- the backup is STALE, not missing" \
        "it is the normal interval until the hourly mirror job; past one turn, this line turns red"
    fi
    printf '%s\n' "$saida" | sed 's/^WARN|/  /' | detalhe
  else
    verde "memory: $(printf '%s' "$saida" | sed 's/^OK|//')"
  fi
}

guarda_memoria_nao_afirma_lei_morta() {
  conta
  # Memory: a pointer states a law the map already REVOKED or POSTPONED.
  # doc: docs/guardas/memoria.md
  # WHAT IT PROTECTS
  #   Measured: 45 of 112 index pointers restate a law the map already delivers in full. Trimming them
  # was proposed and the measurement killed it: it would save 1.9% of the reload, and the duplicated
  # piece is exactly what IDENTIFIES the memory.
  #   So the duplication STAYS, and the risk changes shape: when a law is revoked or postponed in the
  # map, the memory's hook keeps stating the opposite -- and the index header itself says "in
  # conflict, the DOC wins". Nobody notices the conflict: both sentences arrive in the same context,
  # both look true, and the older one is read first (memory enters the system prompt; the map later).
  #   IT DOES NOT ACCUSE DUPLICATION -- duplicating a law IN FORCE is accepted. It accuses only the
  # dangerous case: memory stating what the map already killed.
  #   PUBLIC PORT: the map's state words are REVOKED and POSTPONED (the lab's were Portuguese).
  local mapa=docs/mapa/3_DECIDIDO.md
  local mem="$MEM_INDEX"
  [ -f "$mapa" ] || { amarelo "memory: $mapa missing -- dead-law conflict not verified"; return; }
  [ -f "$mem" ] || { amarelo "memory: index not found at $mem -- the guard does not run off the host"; return; }
  local saida
  saida=$(MAPA_F="$mapa" MEM_F="$mem" python3 - <<'PY'
import os, re, unicodedata
def norm(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9 ]', ' ', s)
mortas = []
for l in open(os.environ['MAPA_F'], encoding='utf-8'):
    if not l.strip().startswith('|'):
        continue
    col = [c.strip() for c in l.strip().strip('|').split('|')]
    if len(col) < 3 or not re.match(r'^[A-Z]\d+$', col[0]):
        continue
    if 'REVOKED' not in col[1] and 'POSTPONED' not in col[1]:
        continue
    # the dead statement = the 1st struck-through or bold span of the decision column
    m = re.search(r'~~(.+?)~~', col[2]) or re.search(r'\*\*(.+?)\*\*', col[2])
    if m:
        mortas.append((col[0], m.group(1)))
#   THE PREDICATE WAS ONLY `startswith('-')` -- a markdown bullet -- and the index became PLAIN TEXT.
# Measured: 110 of 153 lines swept before, 0 after, with the guard printing GREEN. Zero lines does not
# produce zero hits: it produces zero SWEEP, and the message declared the MAP's population, never the
# swept one -- so the silence was indistinguishable from health.
#   The union is backward-compatible: bullet (old format) OR a line carrying a memory pointer in
# pointer position (bare name) OR a citation `[N]` (today's format). Without the citation arm the
# predicate sweeps ZERO and the anti-blindness branch below fires.
linhas = [l for l in open(os.environ['MEM_F'], encoding='utf-8')
          if l.strip().startswith('-')
          or re.search(r'(?:^[ \t]*|[-:·][ \t]+)[a-z0-9_][a-z0-9_-]*\.md\b', l)
          or re.search(r'(?<!\[)\[\d+\](?!\])', l)]
achados = []
for lid, txt in mortas:
    pal = {w for w in norm(txt).split() if len(w) >= 5}
    if len(pal) < 2:
        continue
    for l in linhas:
        n = norm(l)
        if sum(1 for w in pal if w in n) / len(pal) >= 0.7:
            achados.append(f"{lid} ({txt[:44]}) still stated in: {l.strip()[:76]}")
print(f"POP {len(mortas)}")
print(f"VAR {len(linhas)}/{sum(1 for _ in open(os.environ['MEM_F'], encoding='utf-8'))}")
for a in achados:
    print("HIT " + a)
PY
)
  local pop; pop=$(printf '%s' "$saida" | sed -n 's/^POP //p')
  local var; var=$(printf '%s' "$saida" | sed -n 's/^VAR //p')
  local hits; hits=$(printf '%s' "$saida" | grep -c '^HIT ' || true)
  #   ZERO SWEPT IS A FAILURE, not silence: a guard that looks at nothing prints the same green as a
  # guard that looked at everything.
  if [ "${var%%/*}" = "0" ] || [ -z "${var:-}" ]; then
    vermelho "memory: the dead-law guard SWEPT ZERO index lines -- it is blind" \
      "the predicate does not recognize the index format; green here means nothing" \
      "check the line predicate against the current MEMORY.md format"
    return
  fi
  if [ "${hits:-0}" -eq 0 ]; then
    verde "memory: no pointer states a dead law (${pop:-0} REVOKED/POSTPONED x ${var:-0} index line(s) SWEPT)"
  else
    vermelho "memory: a pointer states a law the map already REVOKED/POSTPONED" \
      "both sentences reach the same context and the memory arrives FIRST -- the dead version is read" \
      "fix the hook in MEMORY.md; in conflict the DOC wins (the index's own rule)"
    printf '%s\n' "$saida" | sed -n 's/^HIT //p' | detalhe
  fi
}

# ── the driver ────────────────────────────────────────────────────────────────────────────────
_g() { "$1"; }

_g guarda_memoria_nao_afirma_lei_morta
#   Own gate: the guard belongs to the memory system of THIS repo (the hooks file and the baton in
# docs/mesa/). Other repos with the pre-commit installed have neither.
if [ -f "${BASTAO_SETTINGS:-settings.example.json}" ] || [ -d docs/mesa ]; then
  _g guarda_memoria_bastao_entrega_estado_vivo
fi
#   GATED: these three look at the memory STORE, which only the repo with `docs/mapa/` carries. Without
# the gate they run in a repo that has no store and BLOCK someone else's commit -- and a guard that
# blocks legitimate work is a guard someone switches off. Inside the gate a missing CONFIGURED mirror
# is still a FAILURE: not running in another repo is different from passing green here.
if [ -d docs/mapa ]; then
  _g guarda_memoria_indice_integro
  _g guarda_memoria_description_sem_estado_transiente
  _g guarda_memoria_cascata
fi

printf '── %s guards · %s failure(s) · %s warning(s)\n' "$RODADOS" "$FALHAS" "$AVISOS"
[ "$FALHAS" -eq 0 ] || { echo "   (conscious bypass: git commit --no-verify -- and the debt is yours)" >&2; exit 1; }
exit 0
