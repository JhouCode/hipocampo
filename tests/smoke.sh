#!/usr/bin/env bash
# smoke.sh -- the reproduction smoke test. It follows the README in a temporary folder with a fake
# HOME, so nothing of the machine that runs it is read or written:
#   1. clone this checkout (tracked + untracked-not-ignored files) into <tmp>/hipocampo;
#   2. configure: hipocampo.conf with HIPO_WORKDIR=<tmp>/work, the example memory copied into the
#      native memory folder that the configuration resolves, settings.example.json with
#      <YOUR_FOLDER> filled in, installed as <fake HOME>/.claude/settings.json;
#   3. run EVERY hook command registered in that settings file, with a sample payload of its event,
#      and check what it emits;
#   4. run the memory guards over the example (green) and prove each guard on its fixtures
#      (control green, every mutant red);
#   5. run every selftest, compile every .py, parse every .sh, and the private-data selftest.
# Verdict: one line per check, then `N of M` and rc 0 only if every check passed.
set -uo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"; mkdir -p "$HOME/.claude" "$TMP/work"
R="$TMP/hipocampo"; mkdir -p "$R"
unset HIPO_REPO HIPO_CLAUDE_DIR HIPO_WORKDIR HIPO_PROJECT_DIR HIPO_MEMORY_DIR HIPO_SETTINGS HIPO_STATE_DIR HIPO_LOG_DIR MEM_DIR
unset GIT_INDEX_FILE GIT_DIR GIT_WORK_TREE
# the fake HOME has no git identity; the mirror commits, so give it one
export GIT_AUTHOR_NAME=smoke GIT_AUTHOR_EMAIL=smoke@example.com GIT_COMMITTER_NAME=smoke GIT_COMMITTER_EMAIL=smoke@example.com

N=0; OK=0
check() {  # $1 = name · $2 = rc (0 = pass) · $3 = evidence
  N=$((N+1))
  if [ "$2" = 0 ]; then OK=$((OK+1)); printf '  ✓ %-58s %s\n' "$1" "$3"
  else printf '  ✗ %-58s %s\n' "$1" "$3"; fi
}

echo "== 1. clone into a temporary folder"
(cd "$SRC" && git ls-files -co --exclude-standard -z | xargs -0 -I{} cp --parents {} "$R/") 2>/dev/null \
  || (cd "$SRC" && tar --exclude=.git -cf - . | tar -xf - -C "$R")
rm -f "$R/.private-terms" "$R/hipocampo.conf"
git -C "$R" init -q && git -C "$R" add -A && git -C "$R" -c user.name=smoke -c user.email=smoke@example.com commit -qm smoke
check "clone has scripts/ and docs/" "$([ -d "$R/scripts" ] && [ -d "$R/docs" ]; echo $?)" "$(git -C "$R" ls-files | wc -l) files"

echo "== 2. configure (README, section Configuration)"
cp "$R/hipocampo.conf.example" "$R/hipocampo.conf"
printf 'HIPO_WORKDIR=%s\nHIPO_STATE_DIR=%s\n' "$TMP/work" "$TMP/state" >> "$R/hipocampo.conf"
eval "$(python3 "$R/scripts/hipo_config.py")"
check "memory folder resolves under the fake HOME" "$(case "$HIPO_MEMORY_DIR" in "$HOME"/.claude/projects/*/memory) echo 0;; *) echo 1;; esac)" "$HIPO_MEMORY_DIR"
mkdir -p "$HIPO_MEMORY_DIR" && cp "$R"/examples/memory/*.md "$HIPO_MEMORY_DIR/"
check "example memory installed" "$([ -f "$HIPO_MEMORY_DIR/MEMORY.md" ]; echo $?)" "$(ls "$HIPO_MEMORY_DIR" | wc -l) file(s)"
sed "s#<YOUR_FOLDER>#$R#g" "$R/settings.example.json" > "$HOME/.claude/settings.json"
check "settings installed, no placeholder left" "$(! grep -q '<YOUR_FOLDER>' "$HOME/.claude/settings.json"; echo $?)" "$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(sum(len(h["hooks"]) for e in d["hooks"].values() for h in e), "commands")' "$HOME/.claude/settings.json")"
mkdir -p "$HIPO_PROJECT_DIR"
TR="$HIPO_PROJECT_DIR/00000000-smoke.jsonl"; : > "$TR"

echo "== 3. every registered hook, with a sample payload"
python3 - "$HOME/.claude/settings.json" "$R" "$TR" "$TMP/work" > "$TMP/hooks.tsv" <<'PY'
import json, sys
s, repo, tr, cwd = sys.argv[1:5]
d = json.load(open(s))
base = {"session_id": "smoke", "transcript_path": tr, "cwd": cwd}
payload = {
  "UserPromptSubmit": {"hook_event_name": "UserPromptSubmit", "prompt": "hello"},
  "SessionStart":     {"hook_event_name": "SessionStart", "source": "compact"},
  "PostToolUse":      {"hook_event_name": "PostToolUse", "tool_name": "Edit",
                       "tool_input": {"file_path": repo + "/scripts/deploy.sh", "old_string": "a", "new_string": "b"},
                       "tool_response": {"success": True}},
  "PreToolUse":       {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                       "tool_input": {"command": "ls " + repo}},
  "Stop":             {"hook_event_name": "Stop", "stop_hook_active": False},
  "PostCompact":      {"hook_event_name": "PostCompact", "trigger": "manual"},
}
for ev, entries in d["hooks"].items():
    for e in entries:
        for h in e["hooks"]:
            p = dict(base, **payload[ev])
            if ev == "SessionStart" and e.get("matcher") != "compact":
                p["source"] = "startup"
            print("%s\t%s\t%s" % (ev, h["command"], json.dumps(p)))
PY
while IFS=$'\t' read -r ev cmd pl; do
  out="$(printf '%s' "$pl" | (cd "$TMP/work" && timeout 30 bash -c "$cmd") 2>"$TMP/err")"; rc=$?
  short="$(printf '%s' "$cmd" | sed "s#$R/##g")"
  bytes=$(printf '%s' "$out" | wc -c)
  check "$ev · $short" "$([ "$rc" = 0 ] && echo 0 || echo 1)" "rc=$rc · ${bytes} B out$( [ -s "$TMP/err" ] && printf ' · stderr: %s' "$(head -c 120 "$TMP/err" | tr '\n' ' ')")"
  printf '%s\n' "$out" > "$TMP/out.$(printf '%s' "$ev · $short" | tr -c 'a-zA-Z0-9' _)"
done < "$TMP/hooks.tsv"
# what each piece must emit (read from the captured outputs)
o() { cat "$TMP/out.$(printf '%s' "$1" | tr -c 'a-zA-Z0-9' _)" 2>/dev/null; }
for k in 1 2 3; do
  n=$(o "UserPromptSubmit · scripts/mapa-hook.sh --parte $k" | grep -c "part $k of")
  check "map slice $k is labelled 'part $k of N'" "$([ "${n:-0}" -gt 0 ]; echo $?)" "$n label line(s)"
done
n=$(o "SessionStart · python3 scripts/bastao-entrega.py --emitir docs/mesa/BASTAO.md" | grep -c '^\*Updated:')
check "baton cut carries the *Updated: live state" "$([ "$n" -gt 0 ]; echo $?)" "$n line(s)"
n=$(o "PostToolUse · scripts/gatilho.py --evento post-tool" | grep -c 'DEBT-01')
check "escalator warns on the example debt (scripts/deploy.sh)" "$([ "$n" -gt 0 ]; echo $?)" "$n line(s) naming DEBT-01"
n=$(o "PostCompact · cat docs/mesa/BASTAO.md" | grep -c '^\*Updated:')
check "PostCompact echoes the whole baton" "$([ "$n" -gt 0 ]; echo $?)" "$n line(s)"

echo "== 4. memory guards: green on the example, proven red on each mutant"
# step 7 of the order (optional piece): the mirror of the memory folder into git. The index guard
# requires it: a memory folder with no mirror has no backup at all.
out="$(cd "$R" && MEM_DIR="$HIPO_MEMORY_DIR" bash scripts/memoria-espelho.sh 2>&1)"; rc=$?
check "memoria-espelho.sh mirrors the example into memoria/" "$([ "$rc" = 0 ] && [ -f "$R/memoria/MEMORY.md" ]; echo $?)" "$(printf '%s' "$out" | tail -1 | cut -c1-80)"
out="$(cd "$R" && MEM_DIR="$HIPO_MEMORY_DIR" bash guards/memory-guards.sh --tree 2>&1)"; rc=$?
printf '%s\n' "$out" | sed 's/\x1b\[[0-9;]*m//g' | sed 's/^/      /'
check "memory-guards.sh on the example memory" "$rc" "$(printf '%s' "$out" | sed 's/\x1b\[[0-9;]*m//g' | grep -c '^✓') green · $(printf '%s' "$out" | sed 's/\x1b\[[0-9;]*m//g' | grep -c '^✗') red"
out="$(cd "$R" && bash guards/prove-fixture.sh --todas 2>&1)"; rc=$?
printf '%s\n' "$out" | sed 's/^/      /'
check "prove-fixture.sh --todas" "$rc" "$(printf '%s' "$out" | grep -o '[0-9]* of [0-9]* case(s) as expected' | awk '{a+=$1; b+=$3} END {print a" of "b" case(s) as expected"}')"

echo "== 5. selftests, syntax, private data"
st() {  # $1 = label · rest = command (run in the clone, under the fake HOME)
  local lab="$1"; shift
  out="$(cd "$R" && "$@" 2>&1)"; rc=$?
  check "$lab" "$rc" "$(printf '%s' "$out" | sed 's/\x1b\[[0-9;]*m//g' | grep -v '^\s*$' | tail -1 | cut -c1-90)"
}
st "mapa-hook.sh --selftest"            bash scripts/mapa-hook.sh --selftest
st "gatilho.py --selftest"              python3 scripts/gatilho.py --selftest
st "oraculo.py --selftest"              python3 scripts/oraculo.py --selftest
st "porta.py --selftest"                python3 scripts/porta.py --selftest
st "bastao-entrega.py --selftest"       python3 scripts/bastao-entrega.py --selftest
st "memory-cap-probe.py --selftest"     python3 scripts/memory-cap-probe.py --selftest
st "janela-teto.py --selftest"          python3 scripts/janela-teto.py --selftest
st "contexto-medir.py --selftest"       python3 scripts/contexto-medir.py --selftest
st "memoria-estaciona.py --selftest"    env MEM_DIR="$HIPO_MEMORY_DIR" python3 scripts/memoria-estaciona.py --selftest
st "memoria-resolve.py --selftest"      python3 scripts/memoria-resolve.py --selftest
st "memoria-id-assign.py --selftest"    python3 scripts/memoria-id-assign.py --selftest
st "guarda-indice-citacao.py --selftest" python3 scripts/guarda-indice-citacao.py --selftest
st "guarda-indice-citacao.py on the example" env MEM_DIR="$HIPO_MEMORY_DIR" python3 scripts/guarda-indice-citacao.py
st "guarda-cascata.py on the example"   python3 scripts/guarda-cascata.py "$HIPO_MEMORY_DIR"
st "guarda-crase.py --selftest"         python3 scripts/guarda-crase.py --selftest
st "memoria-resolve.py 1"               env MEM_DIR="$HIPO_MEMORY_DIR" python3 scripts/memoria-resolve.py 1
st "check-private.py --selftest"        python3 guards/check-private.py --selftest
bad=""
while IFS= read -r f; do
  case "$f" in
    *.py) python3 -m py_compile "$R/$f" 2>/dev/null || bad="$bad $f" ;;
    *.sh|.githooks/*) bash -n "$R/$f" 2>/dev/null || bad="$bad $f" ;;
  esac
done < <(git -C "$R" ls-files)
np=$(git -C "$R" ls-files | grep -c '\.py$'); ns=$(git -C "$R" ls-files | grep -Ec '\.sh$|^\.githooks/')
check "every .py compiles, every .sh parses" "$([ -z "$bad" ]; echo $?)" "$np .py · $ns .sh${bad:+ · FAIL:$bad}"

echo "== 6. a new reader's first steps: empty store, missing folder, relocated Claude home, law retirement"
E="$TMP/empty"; mkdir -p "$E/fakehome/.claude" "$E/mem"
out="$(cd "$R" && HOME="$E/fakehome" HIPO_MEMORY_DIR="$E/mem" python3 scripts/memoria-recall.py 2>&1)"; rc=$?
check "memoria-recall.py on an empty store: honest, rc 0" "$([ "$rc" = 0 ] && printf '%s' "$out" | grep -q 'no memory yet'; echo $?)" "rc=$rc · $(printf '%s' "$out" | tail -1 | cut -c1-60)"
for m in --ranking --cobrado; do
  out="$(cd "$R" && HOME="$E/fakehome" HIPO_CLAUDE_DIR="$E/fakehome/.claude" python3 scripts/contexto-consumo.py $m 2>&1)"; rc=$?
  check "contexto-consumo.py $m on an empty store: honest, rc 0" "$([ "$rc" = 0 ] && printf '%s' "$out" | grep -q 'no transcript yet'; echo $?)" "rc=$rc · $(printf '%s' "$out" | tail -1 | cut -c1-60)"
done
out="$(cd "$R" && python3 scripts/guarda-cascata.py "$E/no-such-folder" 2>&1)"; rc=$?
check "guarda-cascata.py on a missing folder is RED" "$([ "$rc" = 1 ]; echo $?)" "rc=$rc · $(printf '%s' "$out" | sed 's/\x1b\[[0-9;]*m//g' | tail -1 | cut -c1-60)"
mkdir -p "$E/cc/projects/elsewhere/memory"; cp "$R/examples/memory/MEMORY.md" "$E/cc/projects/elsewhere/memory/"
out="$(cd "$R/scripts" && HOME="$E/fakehome" HIPO_CLAUDE_DIR="$E/cc" python3 -c 'import importlib.util as u; s=u.spec_from_file_location("p","memory-cap-probe.py"); m=u.module_from_spec(s); s.loader.exec_module(m); print(len(m.stores()))' 2>&1)"
check "memory-cap-probe.py finds stores under HIPO_CLAUDE_DIR" "$([ "$out" = 1 ]; echo $?)" "$out store(s) found outside HOME"
n_in="$(cd "$R" && bash scripts/mapa-hook.sh --nucleo 2>/dev/null | grep -c '^- \*\*P9\*\*')"
check "law P9, named by a guard header, leaves the core" "$([ "$n_in" = 0 ]; echo $?)" "P9 lines in the core: $n_in"
grep -v '# @guard memory index' "$R/guards/memory-guards.sh" > "$E/guards-without-header.sh"
n_mut="$(cd "$R" && MAPA_GUARDAS="$E/guards-without-header.sh" bash scripts/mapa-hook.sh --nucleo 2>/dev/null | grep -c '^- \*\*P9\*\*')"
check "mutant: header removed, P9 comes back to the core" "$([ "$n_mut" = 1 ]; echo $?)" "P9 lines in the core: $n_mut"

echo "== 7. no jq, optional mirror, revolving door"
NJ="$TMP/nojq"; mkdir -p "$NJ"
IFS=: read -ra _dirs <<< "$PATH"
for d in "${_dirs[@]}"; do for b in "$d"/*; do n="${b##*/}"; [ "$n" = jq ] && continue; [ -e "$NJ/$n" ] || ln -s "$b" "$NJ/$n" 2>/dev/null; done; done
out="$(cd "$R" && PATH="$NJ" bash scripts/mapa-hook.sh --selftest 2>&1)"; rc=$?
check "mapa-hook.sh --selftest with NO jq in PATH" "$([ "$rc" = 0 ] && ! PATH="$NJ" command -v jq >/dev/null; echo $?)" "$(printf '%s' "$out" | grep -v '^\s*$' | tail -1 | cut -c1-60)"
M2="$TMP/nomirror"; mkdir -p "$M2"; (cd "$R" && git ls-files -z | xargs -0 -I{} cp --parents {} "$M2/") ; rm -rf "$M2/memoria"
git -C "$M2" init -q && git -C "$M2" add -A && git -C "$M2" commit -qm x
out="$(cd "$M2" && MEM_DIR="$HIPO_MEMORY_DIR" bash guards/memory-guards.sh --tree 2>&1 | sed 's/\x1b\[[0-9;]*m//g')"; rc=$?
check "no mirror configured: index guard WARNS, battery green" "$([ "$rc" = 0 ] && printf '%s' "$out" | grep -q 'no mirror configured'; echo $?)" "rc=$rc · $(printf '%s' "$out" | grep -o 'no mirror configured[^-]*' | head -1)"
out="$(cd "$M2" && MEM_DIR="$HIPO_MEMORY_DIR" MEM_ESPELHO=memoria bash guards/memory-guards.sh --tree 2>&1 | sed 's/\x1b\[[0-9;]*m//g')"; rc=$?
check "mirror configured and absent: index guard is RED" "$([ "$rc" = 1 ]; echo $?)" "rc=$rc · $(printf '%s' "$out" | grep -o 'mirror memoria does not exist' | head -1)"
out="$(cd "$R" && bash guards/door-guard.sh 2>&1 | sed 's/\x1b\[[0-9;]*m//g')"; rc=$?
check "door-guard.sh: the map inside its slice budget" "$rc" "$(printf '%s' "$out" | grep -v '^\s*$' | tail -1 | cut -c1-70)"

echo "== $OK of $N checks passed"
[ "$OK" = "$N" ]
