#!/usr/bin/env bash
# tarefa-vigia.sh — a timer per long task: whoever wakes up asks the TARGET, never the status.
#
# WHY: the harness wakes a session only when a background process ENDS. A stuck task does not end,
# and from the outside the silence of a stuck task is the same as the silence of a working one. The
# case that started it: a worker's wait loop showed as "running" for hours; its job had already been
# done by other workers and the loop was never going to finish. Nobody knew, and nothing warned.
#
# HOW: the session that launches a long task REGISTERS it and arms `timer` in the background. The
# timer is a clock that ENDS — not a loop, so it cannot hang in silence (a watcher that is a loop
# can get stuck watching itself; it happened, and cost 7 hours). When it ends, the process exit
# wakes the session with the verdict in its output; the session re-arms or reports. The check asks
# the target by EXACT PID (a match by name once matched itself), by the log on disk, and by the CPU
# of the process TREE (the waiting parent is ~0; the work lives in the children).
#
# THE WINDOW IS MODULAR (per task, at registration):
#   time  — `--window 1h` (default 1 h): moved = the log was written since the last check.
#   cycle — `--cycle REGEX [--factor 3]`: moved = a NEW cycle line appeared (a log that only repeats
#           "waiting…" is NOT progress: that was the wait loop above). The window is measured from
#           USE: factor × the average cycle seen, clamped between VIGIA_MIN and `--window`; before
#           2 cycles, `--window` applies.
#   `--cpu` — the task is legitimately silent (a build with no output): CPU in the window counts as
#           progress. Without the flag CPU only INFORMS, because a wait loop also burns CPU.
#
# Usage:
#   tarefa-vigia.sh run      NAME LOG [options] -- CMD…   # wrapper: registers, runs, writes CLOSE rc=N
#   tarefa-vigia.sh register NAME HOST PID|- LOG [options] # a task already launched (by a worker, over ssh…)
#   tarefa-vigia.sh timer    NAME [SEC]  # in the background; sleeps the task's window, then checks
#   tarefa-vigia.sh check    NAME        # verdict; rc 0 moving · 10 finished · 20 stuck ·
#                                        #   21 dead without close · 22 stopped (no PID) · 2 no signal
#   tarefa-vigia.sh next     NAME        # how many seconds the next timer should sleep
#   tarefa-vigia.sh pending              # task not checked for > 1.25 window: its timer DIED
#   tarefa-vigia.sh list | close NAME | --selftest
# options: --window 90s|30m|1h · --cycle REGEX · --factor N · --close REGEX · --cpu
#   HOST: `local`, a Linux ssh alias, or a Windows host listed in VIGIA_WIN_HOSTS (asked through Git
#   Bash over stdin; cmd.exe eats the quotes of an inline command).
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/hipo-config.sh"

VIGIA_DIR="${VIGIA_DIR:-$HIPO_STATE_DIR/tarefa-vigia}"  # not /tmp: systemd's `D /tmp` wipes it at boot
VIGIA_MIN="${VIGIA_MIN:-300}"          # floor of the cycle window: a cycle of seconds is not a timer of seconds
VIGIA_CPU_MIN_CS="${VIGIA_CPU_MIN_CS:-200}"  # hundredths of CPU in the window for `--cpu` to count as progress
VIGIA_WIN_HOSTS="${VIGIA_WIN_HOSTS:-}"
VIGIA_GITBASH="${VIGIA_GITBASH:-C:\\Program Files\\Git\\bin\\bash.exe}"
CLOSE_DEFAULT='^CLOSE rc='

_sec() {   # 90s · 30m · 1h · 3600 → seconds
  local v="$1"
  case "$v" in
    *h) echo $(( ${v%h} * 3600 )) ;; *m) echo $(( ${v%m} * 60 )) ;; *s) echo "${v%s}" ;;
    *[!0-9]*|'') echo "invalid window: $v" >&2; return 1 ;; *) echo "$v" ;;
  esac
}

_name_ok() { [[ "$1" =~ ^[A-Za-z0-9._-]+$ && "$1" != .* ]] || { echo "invalid name: '$1' (letters, digits, . _ -)" >&2; return 1; }; }
_reg() { echo "$VIGIA_DIR/$1.reg"; }

_load() {   # loads the record into R_<field>
  local f; f=$(_reg "$1")
  [ -f "$f" ] || { echo "no record: $1 (see: $0 list)" >&2; return 1; }
  local k v
  while IFS='=' read -r k v; do [ -n "$k" ] && printf -v "R_$k" '%s' "$v"; done < "$f"
}

_save() {   # rewrites the record from R_* (atomic: copy and mv)
  local f; f=$(_reg "$R_name")
  { for k in name host pid log close cpu window cycle factor created last_check cpu_last cycles_last mark_last; do
      local var="R_$k"; printf '%s=%s\n' "$k" "${!var-}"; done; } > "$f.new" && mv "$f.new" "$f"
}

# THE PROBE — the same text runs locally or on the far side of ssh. Prints: alive cpu_cs mtime now close cycles mark
#   alive: 1 · 0 · - (no PID declared). mark: the log's `stat %y`, with nanoseconds. "Moved" is the mark
#   CHANGING since the last look. Comparing the mtime in seconds with the clock of the previous check
#   lost a write made in the same second, and mixed the checker's clock with the host's (measured on a
#   real remote host: a line was written to the log and the verdict came back STUCK).
read -r -d '' _PROBE <<'EOF'
p=$1 log=$2 cre=$3 yre=$4
alive=- cpu=0
if [ "$p" != - ]; then
  if [ -d "/proc/$p" ]; then
    alive=1
    hz=$(getconf CLK_TCK 2>/dev/null || echo 100)
    cpu=$(cat /proc/[0-9]*/stat 2>/dev/null | awk -v r="$p" -v hz="$hz" '
      { pid=$1; s=$0; sub(/^.*\) /, "", s); split(s, f, " "); pp[pid]=f[2]; t[pid]=f[12]+f[13] }
      END { in_[r]=1; changed=1
            while (changed) { changed=0; for (k in pp) if (!(k in in_) && (pp[k] in in_)) { in_[k]=1; changed=1 } }
            sum=0; for (k in in_) sum+=t[k]; printf "%d\n", sum*100/hz }')
  else alive=0; fi
fi
mt=$(stat -c %Y "$log" 2>/dev/null || echo 0)
mk=$(stat -c %y "$log" 2>/dev/null | tr " " _); mk=${mk:-absent}
cl=0; tail -n 50 "$log" 2>/dev/null | grep -Eq "$cre" && cl=1
cy=0; [ -n "$yre" ] && cy=$(grep -cE "$yre" "$log" 2>/dev/null); cy=${cy:-0}
echo "$alive ${cpu:-0} $mt $(date +%s) $cl $cy $mk"
EOF

_probe() {   # host pid log close cycle
  local host="$1"; shift
  local body; body="$(printf 'set -- %q %q %q %q\n' "$@")"$'\n'"$_PROBE"
  if [ "$host" = local ]; then printf '%s\n' "$body" | bash -s
  elif [[ " $VIGIA_WIN_HOSTS " == *" $host "* ]]; then
    printf '%s\n' "$body" | timeout 30 ssh -o ConnectTimeout=8 -o BatchMode=yes "$host" "\"$VIGIA_GITBASH\" -s" 2>/dev/null
  else printf '%s\n' "$body" | timeout 30 ssh -o ConnectTimeout=8 -o BatchMode=yes "$host" bash -s 2>/dev/null
  fi
}

_options() {   # fills R_window R_cycle R_factor R_close R_cpu; what is left goes to _REST
  R_window=3600 R_cycle='' R_factor=3 R_close="$CLOSE_DEFAULT" R_cpu=0; _REST=()
  while [ $# -gt 0 ]; do
    case "$1" in
      --window) R_window=$(_sec "${2:-}") || return 1; shift 2 ;;
      --cycle)  R_cycle="${2:-}"; [ -n "$R_cycle" ] || { echo "--cycle needs a REGEX" >&2; return 1; }; shift 2 ;;
      --factor) R_factor="${2:-}"; [[ "$R_factor" =~ ^[1-9][0-9]*$ ]] || { echo "--factor needs an integer ≥1" >&2; return 1; }; shift 2 ;;
      --close)  R_close="${2:-}"; shift 2 ;;
      --cpu)    R_cpu=1; shift ;;
      --) shift; _REST=("$@"); return 0 ;;
      *) echo "unknown option: $1" >&2; return 1 ;;
    esac
  done
}

register() {   # NAME HOST PID LOG [options]
  [ $# -ge 4 ] || { echo "usage: register NAME HOST PID|- LOG [options]" >&2; return 1; }
  _name_ok "$1" || return 1
  local name="$1" host="$2" pid="$3" log="$4"; shift 4
  [[ "$pid" == - || "$pid" =~ ^[0-9]+$ ]] || { echo "invalid PID: $pid" >&2; return 1; }
  _options "$@" || return 1
  mkdir -p "$VIGIA_DIR"
  R_name=$name R_host=$host R_pid=$pid R_log=$log
  R_created=$(date +%s) R_last_check=$R_created R_cpu_last=0 R_cycles_last=0 R_mark_last=absent
  local s; if s=$(_probe "$host" "$pid" "$log" "$R_close" "$R_cycle"); then
    read -r _ R_cpu_last _ _ _ R_cycles_last R_mark_last <<<"$s"
  fi
  _save
  echo "registered: $name @$host pid $pid · window $(next "$name")s$( [ -n "$R_cycle" ] && echo " · by cycle /$R_cycle/ ×$R_factor")"
}

next() {   # the CURRENT window: time, or factor × the average cycle measured in use
  _load "$1" || return 1
  local w="$R_window"
  if [ -n "$R_cycle" ] && [ "${R_cycles_last:-0}" -ge 2 ]; then
    local avg=$(( (R_last_check - R_created) / R_cycles_last ))
    w=$(( avg * R_factor ))
    [ "$w" -lt "$VIGIA_MIN" ] && w=$VIGIA_MIN
    [ "$w" -gt "$R_window" ] && w=$R_window
  fi
  echo "$w"
}

_dur() { local s=$1; [ "$s" -ge 3600 ] && printf '%dh%02d' $((s/3600)) $((s%3600/60)) || printf '%dmin' $((s/60)); }

check() {
  _load "$1" || return 1
  local s
  if ! s=$(_probe "$R_host" "$R_pid" "$R_log" "$R_close" "$R_cycle") || [ -z "$s" ]; then
    echo "NO-SIGNAL · $R_name @$R_host · could not ask the host (ssh failed or host down) — this is NOT 'stopped'"
    return 2
  fi
  local alive cpu mt now cl cy mk; read -r alive cpu mt now cl cy mk <<<"$s"
  local here; here=$(date +%s)   # window and "pending" use THIS machine's clock; the host's only times the log
  local dcpu=$(( cpu - R_cpu_last )); [ "$dcpu" -lt 0 ] && dcpu=$cpu
  local window=$(( here - R_last_check ))
  local moved=0 by
  if [ -n "$R_cycle" ]; then
    by="cycles $R_cycles_last→$cy"; [ "$cy" -gt "$R_cycles_last" ] && moved=1
  elif [ "$mk" = absent ]; then by="log NOT FOUND on the host ($R_log)"
  else by="log written $(_dur $(( now - mt ))) ago"; [ "$mk" != "${R_mark_last:-}" ] && moved=1; fi
  local cpu_txt; cpu_txt=$(awk -v c="$dcpu" 'BEGIN{printf "%.1f", c/100}')
  local det="$R_name @$R_host pid $R_pid · $by · CPU in window ${cpu_txt}s · window $(_dur "$window")"
  local v rc
  if [ "$cl" = 1 ]; then
    v="FINISHED · $det"; rc=10
    [ "$R_host" = local ] && v="$v · $(tail -n 50 "$R_log" 2>/dev/null | grep -E "$R_close" | tail -1)"
  elif [ "$alive" = 0 ]; then v="DEAD-NO-CLOSE · $det · the process is gone and the log has no close line"; rc=21
  elif [ "$moved" = 1 ]; then v="MOVING · $det"; rc=0
  elif [ "$alive" = 1 ] && [ "$R_cpu" = 1 ] && [ "$dcpu" -ge "$VIGIA_CPU_MIN_CS" ]; then
    v="QUIET-WORKING · $det · log still, CPU rising (task declared silent)"; rc=0
  elif [ "$alive" = - ]; then v="STOPPED · $det · no PID declared: stuck or dead, cannot tell which"; rc=22
  else v="STUCK · $det · alive and not progressing"; rc=20
    [ "$dcpu" -ge "$VIGIA_CPU_MIN_CS" ] && v="$v (burns CPU: may be a wait loop)"
  fi
  R_last_check=$here R_cpu_last=$cpu R_cycles_last=$cy R_mark_last=$mk
  _save
  if [ "$rc" = 10 ]; then mkdir -p "$VIGIA_DIR/closed"; mv "$(_reg "$R_name")" "$VIGIA_DIR/closed/"; fi
  echo "$v"
  return "$rc"
}

timer() {   # sleeps the window (or SEC) and checks — the END of this process is what wakes the session
  _load "$1" || return 1
  local sec="${2:-$(next "$1")}"
  sleep "$sec"
  [ -f "$(_reg "$1")" ] || { echo "CLOSED · $1 had already left the registry"; return 0; }
  check "$1"
}

run() {   # NAME LOG [options] -- CMD…  — registers ITSELF and writes the close line with the rc
  [ $# -ge 3 ] || { echo "usage: run NAME LOG [options] -- CMD…" >&2; return 1; }
  local name="$1" log="$2"; shift 2
  _name_ok "$name" || return 1
  _options "$@" || return 1
  [ ${#_REST[@]} -gt 0 ] || { echo "run: missing the command after --" >&2; return 1; }
  local cmd=("${_REST[@]}") opts=(--window "$R_window" --factor "$R_factor" --close "$R_close")
  [ -n "$R_cycle" ] && opts+=(--cycle "$R_cycle"); [ "$R_cpu" = 1 ] && opts+=(--cpu)
  register "$name" local "$BASHPID" "$log" "${opts[@]}" >/dev/null || return 1
  "${cmd[@]}" >>"$log" 2>&1; local rc=$?
  echo "CLOSE rc=$rc $(date '+%F %T')" >>"$log"
  return "$rc"
}

#   Age in STEPS (whole hours; under 1 h, tens of minutes): the neighbour notice repeats when its
# text changes, and minute by minute it would repeat on every prompt.
_step() { local s=$1; [ "$s" -ge 3600 ] && echo "$((s/3600))h" || echo "$((s/600*10))min"; }

pending() {   # the timer's blind spot: it lives in the app's process; app down = timer dead in silence
  local f now; now=$(date +%s)
  for f in "$VIGIA_DIR"/*.reg; do
    [ -f "$f" ] || continue
    local n; n=$(basename "$f" .reg)
    _load "$n" 2>/dev/null || continue
    local w; w=$(next "$n")
    local age=$(( now - R_last_check ))
    [ $(( age * 4 )) -gt $(( w * 5 )) ] &&
      echo "⏰ task $n @$R_host not checked for $(_step "$age") (window $(_dur "$w")): its timer died — run: bash scripts/tarefa-vigia.sh check $n"
  done
  return 0
}

list() {
  local f; for f in "$VIGIA_DIR"/*.reg; do
    [ -f "$f" ] || continue; local n; n=$(basename "$f" .reg); _load "$n" || continue
    echo "$n @$R_host pid $R_pid · window $(next "$n")s · last check $(date -d "@$R_last_check" '+%m-%d %H:%M') · $R_log"
  done
}

close() { _name_ok "$1" || return 1; rm -f "$(_reg "$1")" && echo "closed: $1"; }

# --------------------------------------------------------------------------- selftest
_selftest() {
  local tmp ok=0 bad=0
  tmp=$(mktemp -d); trap 'kill $(jobs -p) 2>/dev/null; rm -rf "$tmp"' RETURN
  export VIGIA_DIR="$tmp/reg" VIGIA_CPU_MIN_CS=50 VIGIA_MIN=60
  local me="$0"
  _case() {   # label · expected (prefix of the verdict) · output
    if [[ "$3" == "$2"* ]]; then ok=$((ok+1)); echo "  ✓ $1"
    else bad=$((bad+1)); echo "  ✗ $1"; echo "      expected '$2', got: ${3:0:150}"; fi
  }
  _age() { local f; f=$(_reg "$1"); sed -i "s/^last_check=.*/last_check=$2/" "$f"; }

  # 1 · wrapper with close line: the rc reaches the log and the verdict is FINISHED
  bash "$me" run t1 "$tmp/t1.log" -- sh -c 'echo work; exit 3'; local r1=$?
  _case "run writes 'CLOSE rc=3' and returns the command's rc" "3" "$r1"
  _case "wrapped task that ended → FINISHED" "FINISHED" "$(bash "$me" check t1)"

  # 2 · alive, log still, no CPU → STUCK (the wait-loop case)
  : > "$tmp/t2.log"; touch -d '-10 min' "$tmp/t2.log"; sleep 300 & local p2=$!
  bash "$me" register t2 local "$p2" "$tmp/t2.log" >/dev/null
  _case "alive, log still, no CPU → STUCK" "STUCK" "$(bash "$me" check t2)"

  # 3 · alive and writing → MOVING; and the base moves: stopped writing → STUCK
  ( for i in 1 2 3 4; do echo "step $i"; sleep 0.25; done; exec sleep 300 ) >>"$tmp/t3.log" & local p3=$!
  bash "$me" register t3 local "$p3" "$tmp/t3.log" >/dev/null
  sleep 1.2
  _case "alive and writing to the log → MOVING" "MOVING" "$(bash "$me" check t3)"
  sleep 2.2
  _case "the check moves the base: stopped writing → STUCK" "STUCK" "$(bash "$me" check t3)"

  # 3b · a write in the SAME second as the previous check is not lost
  bash "$me" check t2 >/dev/null; echo "new line" >>"$tmp/t2.log"
  _case "write right after the check (same second) → MOVING" "MOVING" "$(bash "$me" check t2)"
  bash "$me" register t3c local "$p2" "$tmp/does-not-exist.log" >/dev/null
  _case "a missing log is SAID, not turned into an absurd age" "STUCK · t3c @local pid $p2 · log NOT FOUND" "$(bash "$me" check t3c)"

  # 4 · killed with kill -9, no close line → DEAD-NO-CLOSE
  : > "$tmp/t4.log"; sleep 300 & local p4=$!
  bash "$me" register t4 local "$p4" "$tmp/t4.log" >/dev/null; kill -9 "$p4"; wait "$p4" 2>/dev/null
  _case "kill -9 without close → DEAD-NO-CLOSE" "DEAD-NO-CLOSE" "$(bash "$me" check t4)"

  # 5 · silent but burning CPU: with --cpu it counts as work; without --cpu it is STUCK (wait loop)
  : > "$tmp/t5.log"; touch -d '-10 min' "$tmp/t5.log"
  timeout 20 sh -c 'while :; do :; done' & local p5=$!
  bash "$me" register t5c local "$p5" "$tmp/t5.log" --cpu >/dev/null
  bash "$me" register t5s local "$p5" "$tmp/t5.log" >/dev/null
  sleep 1.2
  _case "silent with CPU and --cpu → QUIET-WORKING" "QUIET-WORKING" "$(bash "$me" check t5c)"
  _case "silent with CPU without --cpu → STUCK (CPU only informs)" "STUCK" "$(bash "$me" check t5s)"
  bash "$me" register t5n local "$p2" "$tmp/t2.log" --cpu >/dev/null
  _case "sleeping with --cpu → STUCK (no CPU, the flag does not save it)" "STUCK" "$(bash "$me" check t5n)"
  kill "$p5" 2>/dev/null

  # 6 · by CYCLE: a log that only repeats 'waiting' is NOT progress; a cycle line is
  ( while :; do echo "waiting…"; sleep 0.2; done ) >>"$tmp/t6.log" & local p6=$!
  bash "$me" register t6 local "$p6" "$tmp/t6.log" --cycle '^CYCLE' >/dev/null
  bash "$me" register t6t local "$p6" "$tmp/t6.log" >/dev/null
  sleep 1.2
  _case "by time, a log repeating 'waiting' → MOVING (why cycle exists)" "MOVING" "$(bash "$me" check t6t)"
  _case "by cycle, only 'waiting' → STUCK" "STUCK" "$(bash "$me" check t6)"
  echo "CYCLE 1" >>"$tmp/t6.log"
  _case "by cycle, a new cycle line → MOVING" "MOVING" "$(bash "$me" check t6)"
  kill "$p6" 2>/dev/null

  # 7 · the cycle window is measured from USE: factor × average cycle, between the floor and --window
  bash "$me" register t7 local - "$tmp/t7.log" --cycle '^CYCLE' --factor 3 --window 2h >/dev/null
  local f7; f7=$(_reg t7); local nw; nw=$(date +%s)
  sed -i "s/^created=.*/created=$(( nw - 1200 ))/; s/^last_check=.*/last_check=$nw/; s/^cycles_last=.*/cycles_last=4/" "$f7"
  _case "average cycle 300 s × factor 3 → window 900" "900" "$(bash "$me" next t7)"
  sed -i "s/^cycles_last=.*/cycles_last=1/" "$f7"
  _case "before 2 cycles --window applies (2h = 7200)" "7200" "$(bash "$me" next t7)"
  sed -i "s/^cycles_last=.*/cycles_last=600/" "$f7"
  _case "a 2 s cycle does not become a 6 s timer: floor (60)" "60" "$(bash "$me" next t7)"
  bash "$me" register t7b local - "$tmp/t7.log" --window 30m >/dev/null
  _case "by time, --window 30m → 1800" "1800" "$(bash "$me" next t7b)"

  # 8 · no PID: log still → STOPPED (does not pretend to know if it died)
  : > "$tmp/t8.log"; touch -d '-10 min' "$tmp/t8.log"
  bash "$me" register t8 local - "$tmp/t8.log" >/dev/null
  _case "no PID and log still → STOPPED" "STOPPED" "$(bash "$me" check t8)"

  # 9 · a host that does not answer → NO-SIGNAL, never 'stopped'
  bash "$me" register t9 does-not-exist.invalid 1 /x >/dev/null 2>&1
  _case "unreachable host → NO-SIGNAL" "NO-SIGNAL" "$(bash "$me" check t9 2>&1)"

  # 10 · pending: the timer that died with the app shows up; one checked just now does not
  _age t8 $(( $(date +%s) - 3 * 3600 ))
  local pend; pend=$(bash "$me" pending)
  _case "check 3 h old (window 1 h) → shows in pending" "⏰ task t8" "$(grep 't8 ' <<<"$pend")"
  _case "checked just now → NOT in pending" "empty" "$(grep 't2 ' <<<"$pend" || echo empty)"

  # 11 · the timer sleeps and checks: its END carries the verdict
  _case "timer wakes up with the verdict" "STUCK" "$(bash "$me" timer t2 1)"

  # 12 · a name that escapes the directory is refused
  bash "$me" register ../out local - /x >/dev/null 2>&1; local r12=$?
  _case "name '../out' refused" "1" "$r12"

  # 13 · editing the script IN PLACE in the middle of a timer does not kill the timer
  cp "$me" "$tmp/copy.sh"; cp "$(dirname "$me")/hipo-config.sh" "$(dirname "$me")/hipo_config.py" "$tmp/"
  bash "$tmp/copy.sh" timer t2 2 >"$tmp/t13.out" 2>&1 & local p13=$!
  sleep 0.5
  { printf '#%.0s' $(seq 300); echo; cat "$tmp/copy.sh"; } >"$tmp/copy.new"
  cat "$tmp/copy.new" >"$tmp/copy.sh"          # SAME inode: that is what an in-place edit does
  wait "$p13"; local r13=$?
  _case "script edited mid-timer: verdict and rc intact" "STUCK rc=20" \
    "$(head -c 5 "$tmp/t13.out") rc=$r13$(grep -E 'command not found|syntax error' "$tmp/t13.out" | head -1)"

  kill "$p2" "$p3" 2>/dev/null
  echo "== $ok ok · $bad failure(s)"
  [ "$bad" -eq 0 ]
}

#   DISPATCH AND `exit` IN ONE BLOCK. bash reads a script IN PIECES while it runs; `timer` sleeps for an
# hour, and whoever edits this file in the meantime shifts the rest: measured, the timer woke with the
# right verdict and died reading garbage (`q: command not found`). Between `{` and `}` everything is
# read before running, and the `exit` keeps bash from going back to the disk.
{
  case "${1:-}" in
    run|register|check|timer|next|close) cmd=$1; shift; "$cmd" "$@" ;;
    pending|list) "$1" ;;
    --selftest) _selftest ;;
    *) sed -n '2,/^set -uo/p' "$0" | sed '$d'; exit 1 ;;
  esac
  exit $?
}
