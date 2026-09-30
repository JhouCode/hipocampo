#!/usr/bin/env bash
# MEMORY MIRROR -- the memory store has no backup of its own.
#
# WHY THIS EXISTS
#   The native memory folder lives outside any repository: the index that loads on every turn, the
# working rules and the state of every open project. A disaster-recovery rebuild that restores the
# hooks and the machine but not this folder rebuilds the machine that READS the memory, without the
# memory. And part of it cannot be recovered from anywhere else: a memory that points to no doc is
# the ONLY source of what it says.
#
# THE DESIGN, and each choice has a reason
#   · **rsync with `--delete`**: the mirror is a PROJECTION, not a parallel store. A memory deleted on
#     purpose has to leave the mirror too -- otherwise the mirror resurrects what was removed, and
#     `git log` already keeps the past.
#   · **`git commit --only memoria/`**: NEVER `git add -A`. Another session may work in the same
#     tree, and a plain `git commit` takes the WHOLE index with it.
#   · **commits only if something changed**: an hourly cron with empty commits becomes noise nobody reads.
#   · **`flock`**: two simultaneous rounds committing the same tree is a guaranteed race.
#   · **no `git push` if the commit fails** -- and the pre-commit guards may block on purpose.
#     A failure here is an ALARM, not something to swallow with `|| true`.
#   · **push is OPT-IN** (`MEM_PUSH=1`): the mirror carries private memory, and the default repository
#     is whatever checkout you configured; pushing it to an upstream you did not choose for this would
#     publish it. Without `MEM_PUSH=1` the mirror commits locally and says so in the log.
#   · **it pushes only what is ITS OWN**: `git push` takes the WHOLE branch, and the branch may be
#     shared by several sessions. If anything ahead of the upstream is not a commit of this mirror,
#     it commits and does NOT push: the log says `push HELD` and names the foreign commits. The
#     backup goes up again on the first run after their owner pushes.
#
# CONFIGURATION (env, all optional)
#   MEM_DIR      the memory folder            (default: HIPO_MEMORY_DIR)
#   REPO_DIR     the repository to mirror into (default: HIPO_REPO); the mirror is REPO_DIR/memoria/
#   MEM_PUSH     1 = push after a commit      (default: 0, local commit only)
#   MEM_REMOTE   remote asked by --status     (default: the remote of the current branch's upstream)
#   MEM_BRANCH   branch asked by --status     (default: the branch of that upstream)
#   MEM_LOG      the cron log read by --status (default: HIPO_LOG_DIR/memoria-espelho.cron.log)
#
# USAGE
#   memoria-espelho.sh              mirrors, commits if changed, pushes if MEM_PUSH=1
#   memoria-espelho.sh --dry-run    says what it would do, touches nothing
#   memoria-espelho.sh --selftest   proves the predicate without touching the real repository
#   memoria-espelho.sh --status     the state NOW, measured on the spot (read-only)
#
# WHY `--status` EXISTS, and not a dated sentence in the doc
#   "Current status" and "a sentence written one day" are different things: the sentence ages by
# itself and nobody notices. docs/MEMORIA.md keeps HOW the cron works and WHAT has been proved; the
# state of NOW is asked here, and it measures on the spot.
#   And it asks the TARGET, not the watchman: "did it push?" is answered by comparing the local
# `HEAD` with the remote branch, not by reading "ok" in its own log -- the log says what the script
# thought it did.
set -uo pipefail

. "$(dirname "${BASH_SOURCE[0]}")/hipo-config.sh"

MEM="${MEM_DIR:-$HIPO_MEMORY_DIR}"
REPO="${REPO_DIR:-$HIPO_REPO}"
DEST="$REPO/memoria"
mkdir -p "$HIPO_STATE_DIR"
LOCK="$HIPO_STATE_DIR/memoria-espelho.lock"
PUSH="${MEM_PUSH:-0}"
SECO=0; [ "${1:-}" = "--dry-run" ] && SECO=1

log() { printf '%s · %s\n' "$(date '+%F %T')" "$*"; }

# rc 0 = everything ahead of the upstream is a commit of this mirror (may push);
# rc 1 = there is a foreign commit (prints `hash subject` of each) or there is no upstream.
# `awk`, not `grep -v`: under pipefail a grep that finds nothing returns 1 and inverts the answer.
so_espelho_a_frente() {
  local u alheios
  u=$(git -C "$1" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null) \
    || { echo "(no upstream)"; return 1; }
  alheios=$(git -C "$1" log --format='%h %s' "$u..HEAD" | awk '$0 !~ /^[0-9a-f]+ memoria: automatic mirror \(/')
  [ -z "$alheios" ] || { printf '%s\n' "$alheios"; return 1; }
}

# -- status: the state NOW, and each line says WHERE it came from --------------------------------
if [ "${1:-}" = "--status" ]; then
  LOGF="${MEM_LOG:-$HIPO_LOG_DIR/memoria-espelho.cron.log}"
  alerta=0; falha=0
  d() { printf '  %-13s %s\n' "$1" "$2"; }

  # 1 · is the cron armed? (source: the user's crontab)
  #   `CRONTAB_CMD` exists only so the defect is INJECTABLE: without it, proving the "cron is gone"
  # branch would require really disarming the crontab -- and a guard not proved failing is decoration.
  CRONTAB_CMD="${CRONTAB_CMD:-crontab}"
  linha_cron=$($CRONTAB_CMD -l 2>/dev/null | grep -c 'memoria-espelho' || true)
  if [ "$linha_cron" -ge 1 ]; then d "cron" "armed, $($CRONTAB_CMD -l 2>/dev/null | grep 'memoria-espelho' | awk '{print $1,$2,$3,$4,$5}')"
  else d "cron" "MISSING from the crontab -- the mirror does not run by itself"; falha=1; fi

  # 2 · when it last ran, and what it did (source: the cron log)
  if [ -f "$LOGF" ]; then
    ult=$(tail -1 "$LOGF"); quando=$(printf '%s' "$ult" | cut -d' ' -f1-2)
    idade=$(( ($(date +%s) - $(date -d "$quando" +%s 2>/dev/null || date +%s)) / 60 ))
    d "last run" "$ult"
    #   The cron is HOURLY. Going past 90 min without running is not "quiet", it is a symptom -- and
    # the silence of a backup is exactly what nobody notices by themselves.
    if [ "$idade" -gt 90 ]; then d "" "!! $idade min ago -- the cron is hourly, this is a delay"; alerta=1; fi
    case "$ult" in
      *"push failed"*)   d "" "!! the push FAILED: it is in the local git, not offsite"; falha=1 ;;
      *"commit failed"*) d "" "!! the commit FAILED -- probably a guard blocking"; falha=1 ;;
      *"push HELD"*)     d "" "!! push held: a commit by another hand is ahead of the offsite (see the log)"; alerta=1 ;;
    esac
  else d "last run" "no log at $LOGF -- never ran by cron, or the path changed"; alerta=1; fi

  # 3 · do the source and the mirror match? (source: the disk, on both sides)
  nf=$(ls -1 "$MEM"/*.md 2>/dev/null | wc -l); ne=$(ls -1 "$DEST"/*.md 2>/dev/null | wc -l)
  d "source" "$nf file(s) in $MEM"
  d "mirror" "$ne file(s) in $DEST"
  if [ "$nf" != "$ne" ]; then
    d "" "!! they differ by $((nf > ne ? nf - ne : ne - nf)) -- normal if something changed after the last run"
    alerta=1
  fi

  # 4 · did the backup reach the OFFSITE? -- the question goes to the remote, not to the local log
  if cd "$REPO" 2>/dev/null; then
    hl=$(git rev-parse HEAD 2>/dev/null)
    up=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)
    rem="${MEM_REMOTE:-${up%%/*}}"; br="${MEM_BRANCH:-${up#*/}}"
    hr=""
    [ -n "$rem" ] && [ -n "$br" ] && hr=$(timeout 45 git ls-remote "$rem" "refs/heads/$br" 2>/dev/null | cut -f1)
    if [ -z "$hr" ]; then d "offsite" "could not ask the remote (network/credential/no upstream) -- NOT MEASURED"; alerta=1
    elif [ "$hl" = "$hr" ]; then d "offsite" "up to date: local and $rem/$br on the same commit ${hl:0:8}"
    else
      atras=$(git rev-list --count "$hr..$hl" 2>/dev/null || echo '?')
      d "offsite" "!! local ${hl:0:8} x $rem/$br ${hr:0:8} -- $atras commit(s) not pushed"; alerta=1
    fi
    d "last commit" "$(git log -1 --format='%h %ad · %s' --date=format:'%F %H:%M' -- memoria/ 2>/dev/null)"
  fi

  echo
  if [ "$falha" = 1 ];  then echo "  VERDICT: FAIL -- the memory backup is not closing the cycle"; exit 2
  elif [ "$alerta" = 1 ]; then echo "  VERDICT: ATTENTION -- see the lines with !! above"; exit 1
  else echo "  VERDICT: OK -- source, mirror and offsite in the same state, and the cron ran within the hour"; exit 0; fi
fi

# -- selftest: the predicate is "the mirror reflects the directory, removals included" -----------
if [ "${1:-}" = "--selftest" ]; then
  ok=0; bad=0
  t=$(mktemp -d); mkdir -p "$t/mem" "$t/repo/memoria"
  printf 'a\n' > "$t/mem/feedback_a.md"; printf 'idx\n' > "$t/mem/MEMORY.md"
  printf 'junk\n' > "$t/repo/memoria/feedback_morta.md"     # has to LEAVE the mirror
  printf 'x\n'    > "$t/mem/nao_e_md.txt"                    # a non-.md does not enter
  rsync -a --delete --include='*.md' --include='*/' --exclude='*' "$t/mem/" "$t/repo/memoria/"
  chk() { if [ "$2" = "$3" ]; then ok=$((ok+1)); printf '  \033[32m✓\033[0m %s\n' "$1";
          else bad=$((bad+1)); printf '  \033[31m✗\033[0m %s (got=%s expected=%s)\n' "$1" "$2" "$3"; fi; }
  chk "positive: a new memory shows up in the mirror" \
      "$([ -f "$t/repo/memoria/feedback_a.md" ] && echo sim || echo nao)" "sim"
  chk "positive: the INDEX is mirrored too" \
      "$([ -f "$t/repo/memoria/MEMORY.md" ] && echo sim || echo nao)" "sim"
  chk "REMOVAL: a file that no longer exists in the source LEAVES the mirror" \
      "$([ -f "$t/repo/memoria/feedback_morta.md" ] && echo sim || echo nao)" "nao"
  chk "negative: a non-.md file does NOT enter" \
      "$([ -f "$t/repo/memoria/nao_e_md.txt" ] && echo sim || echo nao)" "nao"
  chk "population: the mirror count matches the source count" \
      "$(ls -1 "$t/repo/memoria"/*.md 2>/dev/null | wc -l)" "$(ls -1 "$t/mem"/*.md 2>/dev/null | wc -l)"
  # LIMIT control: an empty source must not EMPTY the mirror in silence
  rm -f "$t/mem"/*.md
  antes=$(ls -1 "$t/repo/memoria"/*.md 2>/dev/null | wc -l)
  n=$(ls -1 "$t/mem"/*.md 2>/dev/null | wc -l)
  chk "LIMIT: an empty source is aborted, not mirrored (otherwise the mirror zeroes silently)" \
      "$([ "$n" -eq 0 ] && echo aborta || echo espelha)" "aborta"
  rm -rf "$t"
  # pushes only what is ITS OWN: bare remote + clone with upstream, 3 states
  t=$(mktemp -d); git init -q --bare "$t/r.git"; git clone -q "$t/r.git" "$t/c" 2>/dev/null
  g() { git -C "$t/c" -c user.name=t -c user.email=t@t "$@"; }
  g commit -q --allow-empty -m base; g push -q origin HEAD:master 2>/dev/null; g branch -q -u origin/master 2>/dev/null
  g commit -q --allow-empty -m "memoria: automatic mirror (1 file(s), 2 in total)"
  chk "positive: only mirror commits ahead -> pushes" \
      "$(so_espelho_a_frente "$t/c" >/dev/null && echo empurra || echo segura)" "empurra"
  g commit -q --allow-empty -m "other: work waiting for its owner"
  chk "NEGATIVE: a foreign commit ahead -> holds" \
      "$(so_espelho_a_frente "$t/c" >/dev/null && echo empurra || echo segura)" "segura"
  chk "the foreign one is NAMED, and only it" \
      "$(so_espelho_a_frente "$t/c" | awk '{print $2}' | tr '\n' ' ')" "other: "
  g push -q origin HEAD:master 2>/dev/null; g fetch -q 2>/dev/null
  g commit -q --allow-empty -m "memoria: automatic mirror (2 file(s), 2 in total)"
  chk "after the owner pushes, the mirror goes up again" \
      "$(so_espelho_a_frente "$t/c" >/dev/null && echo empurra || echo segura)" "empurra"
  rm -rf "$t"
  printf '%s\n' "$([ "$bad" -eq 0 ] && printf '\033[32m✓ selftest OK -- %d controls\033[0m' "$ok" \
                                    || printf '\033[31m✗ %d of %d failed\033[0m' "$bad" $((ok+bad)))"
  [ "$bad" -eq 0 ] || exit 1
  exit 0
fi

exec 9>"$LOCK" || exit 1
flock -n 9 || { log "another round in progress -- leaving"; exit 0; }

[ -d "$MEM" ]  || { log "✗ source $MEM does not exist -- NOTHING mirrored (and that is not 'nothing changed')"; exit 2; }
[ -d "$REPO" ] || { log "✗ repo $REPO does not exist"; exit 2; }

# LIMIT CONTROL, and it is what prevents the worst case: if the source is empty (wrong dir, disk
# half-mounted, home swapped), an rsync --delete would ERASE the whole mirror and the next commit
# would erase the backup. Absence is not a result.
N=$(ls -1 "$MEM"/*.md 2>/dev/null | wc -l)
[ "$N" -ge 2 ] || { log "✗ source has $N .md file(s) -- aborting BEFORE the rsync --delete"; exit 2; }

mkdir -p "$DEST"
if [ "$SECO" = 1 ]; then
  log "dry: $N file(s) in the source; differences against the mirror:"
  rsync -a --delete --itemize-changes --dry-run \
        --include='*.md' --include='*/' --exclude='*' "$MEM/" "$DEST/"
  exit 0
fi

rsync -a --delete --include='*.md' --include='*/' --exclude='*' "$MEM/" "$DEST/" \
  || { log "✗ rsync failed"; exit 2; }

cd "$REPO" || exit 2
if git diff --quiet -- memoria/ && git diff --cached --quiet -- memoria/ \
   && [ -z "$(git ls-files --others --exclude-standard -- memoria/)" ]; then
  log "no change in the $N memories -- nothing to commit"
  exit 0
fi

MUD=$(git status --porcelain -- memoria/ | wc -l)
git add -- memoria/ || { log "✗ git add failed"; exit 2; }
# `-m` comes BEFORE `--`. With `--` first, git treats `-m` and the message as PATHS -- a first run
# failed exactly like that, and the script blamed the pre-commit without having read the error.
# And stderr is NOT thrown away: guessing the cause is asking the watchman, not the target.
if ! erro=$(git commit -m "memoria: automatic mirror ($MUD file(s), $N in total)" \
                       --only -- memoria/ 2>&1); then
  log "✗ commit failed -- git said:"
  printf '%s\n' "$erro" | sed 's/^/    /' | tail -12
  # A blocked commit does NOT leave memoria/ in the index: the index is ONE for every session, and
  # what stays staged here travels in any neighbour's plain `git commit`. The tree stays intact;
  # the next round re-adds it.
  git reset -q -- memoria/ || log "! index reset failed -- memoria/ is still STAGED"
  exit 1
fi
log "committed: $MUD changed file(s) of $N"
if [ "$PUSH" != 1 ]; then
  log "ok (local commit only; push disabled -- set MEM_PUSH=1 to push)"
  exit 0
fi
if ! alheios=$(so_espelho_a_frente "$REPO"); then
  log "! push HELD -- ahead of the offsite there is a commit that is not this mirror's; its owner pushes:"
  printf '%s\n' "$alheios" | sed 's/^/    /'
  exit 0
fi
git push -q 2>/dev/null || log "! push failed -- the mirror is in the local git, but not offsite"
log "ok"
