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
# of the process TREE, dead children included (the waiting parent is ~0; the work lives in the children).
#
# THE TIMER DOES NOT HANG AROUND. A blind clock that sleeps the whole window piles up: one session
# showed 7 timers "running", 5 of them watching jobs that had already finished; asking the session to
# disarm them did not hold. So the exits belong to the timer itself:
#   · the TARGET closed (close line in the log, PID gone, Claude Code worker with `"finished": true`
#     in its meta.json) → it checks right away and ends: the session wakes with FINISHED;
#   · the same NAME was RE-ARMED → the pidfile NAME.timer passes to the new one; the old one leaves;
#   · `close NAME` removed the record → the timer leaves at its next step.
#   Nobody kills anybody by name: each timer reads the pidfile and steps aside on its own.
#   Peek interval: VIGIA_STEP (30 s, local) · VIGIA_STEP_REMOTE (120 s, over ssh).
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
#   tarefa-vigia.sh timer    NAME [SEC]  # in the background; waits the window OR the target closing, then checks
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
VIGIA_STEP="${VIGIA_STEP:-30}"                 # the timer peeks at the target every step (local: free)
VIGIA_STEP_REMOTE="${VIGIA_STEP_REMOTE:-120}"  # target over ssh: one ssh every 2 min
VIGIA_LOCAL_HOSTS="${VIGIA_LOCAL_HOSTS:-local}"  # names that mean THIS host (probed without ssh)
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
      { pid=$1; s=$0; sub(/^.*\) /, "", s); split(s, f, " "); pp[pid]=f[2]; t[pid]=f[12]+f[13]+f[14]+f[15] }
      END { in_[r]=1; changed=1
            while (changed) { changed=0; for (k in pp) if (!(k in in_) && (pp[k] in in_)) { in_[k]=1; changed=1 } }
            sum=0; for (k in in_) sum+=t[k]; printf "%d\n", sum*100/hz }')
  else alive=0; fi
fi
mt=$(stat -c %Y "$log" 2>/dev/null || echo 0)
mk=$(stat -c %y "$log" 2>/dev/null | tr " " _); mk=${mk:-absent}
cl=0; tail -n 50 "$log" 2>/dev/null | grep -Eq "$cre" && cl=1
#   Claude Code worker (Agent): the log is tasks/<id>.output -> subagents/agent-<id>.jsonl; the harness marks the end in meta.json
r=$(readlink -f "$log" 2>/dev/null); case "$r" in */subagents/agent-*.jsonl)
  grep -q '"finished": *true' "${r%.jsonl}.meta.json" 2>/dev/null && cl=1 ;; esac
cy=0; [ -n "$yre" ] && cy=$(grep -cE "$yre" "$log" 2>/dev/null); cy=${cy:-0}
echo "$alive ${cpu:-0} $mt $(date +%s) $cl $cy $mk"
EOF

_is_local() { [[ " $VIGIA_LOCAL_HOSTS " == *" $1 "* ]]; }

_probe() {   # host pid log close cycle
  local host="$1"; shift
  local body; body="$(printf 'set -- %q %q %q %q\n' "$@")"$'\n'"$_PROBE"
  if _is_local "$host"; then printf '%s\n' "$body" | bash -s
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
  #   a relative log of a local task becomes absolute: the timer runs from another directory
  _is_local "$host" && [[ "$log" != /* ]] && log="$PWD/$log"
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
    _is_local "$R_host" && v="$v · $(tail -n 50 "$R_log" 2>/dev/null | grep -E "$R_close" | tail -1 | cut -c1-200)"
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

timer() {   # waits the window (or SEC) or the target closing, then checks — the END of this process wakes the session
  _load "$1" || return 1
  local name="$1" sec="${2:-$(next "$1")}" pf="$VIGIA_DIR/$1.timer"
  echo $$ > "$pf"                       # the current timer is the one in the pidfile; the previous one steps aside
  local step=$VIGIA_STEP; _is_local "$R_host" || step=$VIGIA_STEP_REMOTE
  local end=$(( $(date +%s) + sec )) now s alive cl
  while now=$(date +%s); [ "$now" -lt "$end" ]; do
    sleep $(( end - now < step ? end - now : step ))
    [ -f "$(_reg "$name")" ] || { echo "CLOSED · $name left the registry (close, or another check said FINISHED)"; return 0; }
    [ "$(cat "$pf" 2>/dev/null)" = $$ ] || { echo "REPLACED · $name was re-armed; this timer steps aside"; return 0; }
    s=$(_probe "$R_host" "$R_pid" "$R_log" "$R_close" "$R_cycle") || continue
    read -r alive _ _ _ cl _ _ <<<"$s"
    [ "$cl" = 1 ] || [ "$alive" = 0 ] && break          # the target closed: check now, not an hour from now
  done
  [ "$(cat "$pf" 2>/dev/null)" = $$ ] && rm -f "$pf"
  check "$name"
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

close() { _name_ok "$1" || return 1; rm -f "$(_reg "$1")" && echo "closed: $1 (its timer leaves at the next step)"; }

# --------------------------------------------------------------------------- selftest
_selftest() {
  local tmp ok=0 bad=0
  tmp=$(mktemp -d); trap 'kill $(jobs -p) 2>/dev/null; rm -rf "$tmp"' RETURN
  export VIGIA_DIR="$tmp/reg" VIGIA_CPU_MIN_CS=50 VIGIA_MIN=60
  local me; me=$(readlink -f "$0")   # absolute: one case runs from another directory
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


  # 5b · --cpu counts a child that has ALREADY died: a reaped child's CPU moves to the parent's cutime/cstime
  #      (a test runner whose test binaries live ~1 min each read as ~0 CPU when only the living were summed)
  : > "$tmp/t5b.log"; touch -d '-10 min' "$tmp/t5b.log"
  ( for i in $(seq 1 14); do timeout 0.2 sh -c 'while :; do :; done'; sleep 0.05; done; exec sleep 300 ) & local p5b=$!
  bash "$me" register t5b local "$p5b" "$tmp/t5b.log" --cpu >/dev/null
  sleep 3.8
  _case "--cpu with short children that already died → QUIET-WORKING" "QUIET-WORKING" "$(bash "$me" check t5b)"
  kill "$p5b" 2>/dev/null
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

  # 14 · THE TIMER DOES NOT HANG AROUND: the job closes → the timer ends with it, not an hour later
  export VIGIA_STEP=1
  : > "$tmp/t14.log"; sleep 300 & local p14=$!
  bash "$me" register t14 local "$p14" "$tmp/t14.log" >/dev/null
  ( sleep 1.5; echo "CLOSE rc=0 x" >>"$tmp/t14.log" ) &
  local t0=$SECONDS out14; out14=$(bash "$me" timer t14 60)
  _case "close line → a 60 s timer ends in ≤ 4 s with FINISHED" "FINISHED ok" "${out14:0:8} $( [ $((SECONDS - t0)) -le 4 ] && echo ok || echo "took $((SECONDS - t0))s")"
  kill "$p14" 2>/dev/null
  : > "$tmp/t15.log"; sleep 300 & local p15=$!
  bash "$me" register t15 local "$p15" "$tmp/t15.log" >/dev/null
  ( sleep 1.5; kill "$p15" ) &
  t0=$SECONDS; local out15; out15=$(bash "$me" timer t15 60)
  _case "PID gone → the timer ends in ≤ 4 s with DEAD-NO-CLOSE" "DEAD-NO-CLOSE ok" "${out15:0:13} $( [ $((SECONDS - t0)) -le 4 ] && echo ok || echo "took")"
  # Claude Code worker: tasks/<id>.output -> subagents/agent-<id>.jsonl + meta.json "finished": true
  mkdir -p "$tmp/subagents" "$tmp/tasks"; echo '{"type":"assistant"}' > "$tmp/subagents/agent-x1.jsonl"
  echo '{"agentType":"worker","finished":false}' > "$tmp/subagents/agent-x1.meta.json"
  ln -s "$tmp/subagents/agent-x1.jsonl" "$tmp/tasks/x1.output"
  bash "$me" register t16 local - "$tmp/tasks/x1.output" >/dev/null
  ( sleep 1.5; echo '{"agentType":"worker","finished":true}' > "$tmp/subagents/agent-x1.meta.json" ) &
  t0=$SECONDS; local out16; out16=$(bash "$me" timer t16 60)
  _case "worker with finished:true → the timer ends in ≤ 4 s with FINISHED" "FINISHED ok" "${out16:0:8} $( [ $((SECONDS - t0)) -le 4 ] && echo ok || echo "took")"
  # re-arming the same name: the old one steps aside; close: the timer leaves
  : > "$tmp/t17.log"; sleep 300 & local p17=$!
  bash "$me" register t17 local "$p17" "$tmp/t17.log" >/dev/null
  bash "$me" timer t17 60 >"$tmp/t17a.out" & local a17=$!; sleep 1.2
  bash "$me" timer t17 60 >"$tmp/t17b.out" & local b17=$!
  t0=$SECONDS; wait "$a17"
  _case "re-armed: the old timer steps aside in ≤ 3 s" "REPLACED ok" "$(cut -d" " -f1 "$tmp/t17a.out") $( [ $((SECONDS - t0)) -le 3 ] && echo ok || echo took)"
  bash "$me" close t17 >/dev/null; t0=$SECONDS; wait "$b17"
  _case "close: the current timer leaves in ≤ 3 s" "CLOSED ok" "$(cut -d" " -f1 "$tmp/t17b.out") $( [ $((SECONDS - t0)) -le 3 ] && echo ok || echo took)"
  kill "$p17" 2>/dev/null
  # a relative log of a local task becomes absolute
  ( cd "$tmp" && bash "$me" register t18 local - rel.log >/dev/null )
  _case "relative log becomes absolute in the record" "log=$tmp/rel.log" "$(grep '^log=' "$(_reg t18)")"

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
