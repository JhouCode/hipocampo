#!/usr/bin/env python3
"""THE ORACLE — the front's ruler comes BEFORE the work, not after.

WHY IT EXISTS
  If a request is about building, and build good practices already exist, why are they not put in
  front of the work at its start? Checking is an expensive proof, and it becomes cheap when you KNOW
  how the thing was built. And: inferring the front from the owner's text is only a guess when the
  AGENT infers it; when the information is curated by the owner it becomes input — **what makes a
  guess a guess is the AUTHORSHIP, not the moment.** So the fronts here are the ones the owner named
  (build, cpp, db, scripts) and their content passes the owner's gate.

WHAT IT DOES — TWO channels, because one does not reach
  Measured against real owner messages: matching only the owner's text, 86% of them went out in
  silence. Not because of a weak trigger — because of how people talk. The owner writes a SYMPTOM;
  the front only appears when the agent decides to open a file. So:

    A · `UserPromptSubmit`  matches the owner's TEXT (`when-matches`)  — when the owner names the front
    B · `PostToolUse`       matches MY COMMAND (`when-touches`)        — on the FIRST touch of the front

  **Channel B is `PostToolUse`, not `PreToolUse`, by measurement.** `PreToolUse` does not accept
  `additionalContext`: it has `permissionDecision`, a channel to BLOCK, not to speak
  (`docs/gatilhos/CANAIS.md §1`). `PostToolUse` accepts it.

  Honest consequence: the ruler arrives **after the first command of that front**, not before it.
  The first touch is usually reconnaissance (`ls`, `grep`) and the following commands already get
  the ruler — but the first one goes without it, and that is declared, not hidden.

WHAT IT IS NOT
  Not a guard: it blocks nothing and judges no command. A guard checks AFTER, and both read the SAME
  source on purpose — a ruler in two files becomes two diverging truths.

HOW IT AVOIDS FLOODING — each lock has a measured reason
  1. **At most 2 fronts per prompt.** A request that matches four is a conversation about the
     project, and dumping 4 rulers on it is exactly the formalization that does not belong there.
  2. **Once per session PER FRONT.** A ruler repeated on every message is pure noise. Same marker
     idea as `mapa-hook.sh`.
  3. **Silence when nothing matches.** The common case pays nothing.
  4. **A byte ceiling per source**, and an aggregate one. A ruler that grows without a ceiling
     becomes one more big file that nobody opens.

USAGE
  oraculo.py                (stdin = hook JSON of UserPromptSubmit)
  oraculo.py --selftest     positive, negative and budget controls
  oraculo.py --frentes      lists the sources with weight and trigger
  oraculo.py --texto "..."  simulates a prompt and shows what would come out
"""
import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "docs" / "oraculo"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipo_config as HC  # noqa: E402
CACHE = Path(os.environ.get("ORACULO_CACHE", str(Path(HC.STATE_DIR) / "oraculo")))

MAX_FRENTES = 2
TETO_BYTES = 9000          # ~2,500 tokens per front. Enforced by the guard, not only here.

# ── THE AGGREGATE CEILING ───────────────────────────────────────────────────
#   THE PER-FRONT CEILING IS BLIND TO THE WHOLE, and it was the only one. Every front could grow to
# 9,000 B with CI green all the way: 36,000 B of implicit ceiling that nobody declared. And what
# reaches a session is not the MAXIMUM — it is the SUM of the fronts that light up.
#
#   THE TWO NUMBERS COME FROM FACT, NOT TASTE — and they are two because one alone gives no direction:
#
#   · BAR = 36,068 B, **the value measured on the day the ceiling was introduced**, frozen. It is the
#     TARE: that day's state became the plate, and from then on **every addition weighs**. Zero slack
#     is deliberate — it is the revolving door written as a number: for something to enter,
#     something leaves. A ceiling with comfortable slack only marks the expiry date.
#
#   · TARGET = 30,325 B, **the load cost of the map** (`mapa-hook.sh --selftest`), the other resident
#     source. The oracle costing more than the map is the anomaly to fix. The target does not block —
#     it says where the door must push.
#
#   The gap between BAR and TARGET is a declared debt. It does not become a repeated warning; it is
# collected by `PORTA-ORAC-AGREGADO` (scripts/porta.py), with a destination.
#   (Both values are from the reference deployment; set them from your own measurement.)
TETO_AGREGADO = 36068      # frozen at introduction — the tare. Every addition weighs from here on.
ALVO_AGREGADO = 30325      # the cost of the map. Where the door pushes; does not block.
MIN_SINAIS = 1             # how many distinct triggers the text must light


def le_fontes(dir_fontes=None):
    """Returns (fronts, problems).

    An unreadable source or one without a trigger must SHOUT, not vanish: an item that disappears
    silently shrinks the population together with the count, and the number stays coherent and LIES.
    """
    d = Path(dir_fontes) if dir_fontes else FONTES
    frentes, problemas = [], []
    if not d.is_dir():
        return frentes, ["sources directory does not exist: %s" % d]
    for md in sorted(d.glob("*.md")):
        # `_` at the start = not a front. The common preamble lives like this: it matches nothing,
        # goes out once per session and holds in any front. Without this rule it would become a
        # fifth front without a trigger, and the contract guard would rightly accuse it.
        if md.name.startswith(("README", "BASELINE", "_")):
            continue
        txt = md.read_text(encoding="utf-8")
        m = re.search(r"<!--\s*when-matches:\s*(.+?)\s*-->", txt)
        if not m:
            problemas.append("%s: no `<!-- when-matches: … -->`" % md.name)
            continue
        mt = re.search(r"<!--\s*when-touches:\s*(.+?)\s*-->", txt)
        if not mt:
            problemas.append("%s: no `<!-- when-touches: … -->` (channel B goes blind)" % md.name)
            continue
        try:
            rx = re.compile(m.group(1), re.I)
            rx_toca = re.compile(mt.group(1), re.I)
        except re.error as e:
            problemas.append("%s: invalid regex (%s)" % (md.name, e))
            continue
        corpo = txt.split("## PREMISES", 1)
        if len(corpo) != 2:
            problemas.append("%s: no `## PREMISES` section" % md.name)
            continue
        regua = ("## PREMISES" + corpo[1]).strip()
        if len(regua.encode()) > TETO_BYTES:
            problemas.append("%s: ruler with %d bytes, ceiling %d"
                             % (md.name, len(regua.encode()), TETO_BYTES))
        frentes.append({"nome": md.stem, "rx": rx, "rx_toca": rx_toca, "regua": regua,
                        "bytes": len(regua.encode()), "arquivo": md.name})
    return frentes, problemas


METACARACTERE = re.compile(r"[\\|\[\]()^$*?{}+]")


def alvo_do_comando(cmd):
    r"""What the command TOUCHES — never what it MENTIONS.

    MEASURED: 3 injections in one session, 3 FALSE POSITIVES, ~16 KB of context burned — and no
    compiled file had been touched, no build run, nothing promoted.

      · the `cpp` front lit because a `grep -nE "...|\.cpp|\.py" scripts/oraculo.py` had the string
        `.cpp` INSIDE THE SEARCH PATTERN. The file opened was `.py`;
      · the `build` front lit because the script being WRITTEN contained `make install`, `git push`
        and `systemctl` — 4 occurrences, none executed.

    The fix is the same principle as anchoring any guard: anchor on the TARGET, not on the string.
    Two exclusions, both categorical:

      1 · A HEREDOC BODY is content I write. Writing a script about building is not building — if
          it were, every doc about a front would light that front.
      2 · A TOKEN WITH A METACHARACTER is a search pattern, not an operand. `\.cpp` is not a file;
          `scripts/oraculo.py` is.

    WHAT THIS DOES **NOT** CATCH, declared: a search pattern without metacharacters (`grep mysql
    notes.txt` would still light `db`). It is rare and genuinely ambiguous — reading about mysql can
    be db work. The cut stays where the evidence is objective.
    """
    if not cmd:
        return ""
    cmd = re.sub(r"<<-?\s*(['\"]?)([A-Za-z_]\w*)\1.*?^\s*\2\s*$", " ", cmd, flags=re.S | re.M)
    return " ".join(t for t in cmd.split() if not METACARACTERE.search(t))


def casa_toque(comando, frentes):
    """Channel B: matches MY command. Returns at most ONE front — the most specific.

    Evidence is not summed here as in channel A: a command belongs to one front. `mysql` inside a
    `.sh` is db, not scripts, and dumping both on the first touch is the flood to avoid.
    The specificity order is fixed and declared, not alphabetical.
    """
    ordem = ["build", "db", "cpp", "scripts"]
    alvo = alvo_do_comando(comando)
    achadas = [f for f in frentes if f["rx_toca"].search(alvo)]
    achadas.sort(key=lambda f: ordem.index(f["nome"]) if f["nome"] in ordem else 99)
    return achadas[:1]


def casa(texto, frentes):
    """Orders the fronts by how many DISTINCT triggers the text lit.

    Counting total occurrences would let one repeated word beat a front really cited; counting
    distinct ones measures the breadth of the evidence, which is what separates "a build request"
    from "wrote 'build' in passing".
    """
    pontos = []
    for f in frentes:
        achados = {a.lower() if isinstance(a, str) else a
                   for a in re.findall(f["rx"], texto)}
        achados = {a for a in achados if a}
        if len(achados) >= MIN_SINAIS:
            pontos.append((len(achados), f))
    pontos.sort(key=lambda t: (-t[0], t[1]["nome"]))
    return [f for _, f in pontos[:MAX_FRENTES]]


def ja_vista(sessao, nome):
    if not sessao:
        return False
    marca = CACHE / ("%s.%s" % (re.sub(r"[^A-Za-z0-9_-]", "", sessao)[:40], nome))
    if marca.exists():
        return True
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        marca.write_text("")
    except OSError:
        pass                      # cache unavailable: repeating is better than vanishing
    return False


def le_comum(dir_fontes=None):
    """The cross-cutting preamble. Returns (text, bytes) or (None, 0) if absent.

    It exists because a rule that was ALREADY in the map was still not applied in most sessions:
    always loaded is not arriving on time. But it does not belong to one front — it crosses all
    four. Repeating it in each source would create 4 diverging truths.
    """
    d = Path(dir_fontes) if dir_fontes else FONTES
    p = d / "_comum.md"
    if not p.is_file():
        return None, 0
    txt = p.read_text(encoding="utf-8")
    if "## PREMISES" not in txt:
        return None, 0
    corpo = ("## PREMISES" + txt.split("## PREMISES", 1)[1]).strip()
    return corpo, len(corpo.encode())


def nomes_das_frentes(dir_fontes=None):
    """The names WITHOUT parsing content — that is what makes the cost shortcut cheap."""
    d = Path(dir_fontes) if dir_fontes else FONTES
    if not d.is_dir():
        return []
    return [p.stem for p in d.glob("*.md") if not p.name.startswith(("README", "BASELINE"))]


def tudo_ja_visto(sessao, dir_fontes=None):
    nomes = nomes_das_frentes(dir_fontes)
    if not nomes:
        return False
    s = re.sub(r"[^A-Za-z0-9_-]", "", sessao)[:40]
    return all((CACHE / ("%s.%s" % (s, n))).exists() for n in nomes)


def alvo_do_toque(d):
    """What channel B examines: the Bash command, or the Edit/Write path."""
    ti = d.get("tool_input") or {}
    return " ".join(str(x) for x in
                    [ti.get("command", ""), ti.get("file_path", ""), ti.get("notebook_path", "")]
                    if x)


def main(texto=None, sessao=None, marcar=True, evento="prompt"):
    dados = {}
    if texto is None:
        try:
            dados = json.load(sys.stdin)
        except Exception:
            return 0
        sessao = dados.get("session_id") or ""
        texto = (alvo_do_toque(dados) if evento == "post-tool"
                 else (dados.get("prompt") or ""))
    if not texto.strip():
        return 0

    # COST GUARD. This hook runs on EVERY `PostToolUse` — hundreds in a working session. Without
    # this shortcut it parses the markdown sources on every command for the rest of the session,
    # long after it has nothing left to say: a diffuse slowness with no owner. If every front was
    # already injected, leave before reading any source. The file name is already the front name.
    if marcar and sessao and tudo_ja_visto(sessao):
        return 0

    frentes, problemas = le_fontes()
    if problemas:
        sys.stderr.write("⚠️ oracle: " + " · ".join(problemas) + "\n")

    if evento == "post-tool":
        candidatas = casa_toque(texto, frentes)
        porque = ("This came in because this was the **first touch** of this front in the session"
                  " — the ruler holds for the next ones.")
    else:
        candidatas = casa(texto, frentes)
        porque = "This came in because **your request** matched this front."

    escolhidas = [f for f in candidatas if not (marcar and ja_vista(sessao, f["nome"]))]
    if not escolhidas:
        return 0

    partes = ["<!-- oracle: the front's ruler, injected BEFORE the work -->"]

    # The common preamble travels with the FIRST ruler of the session, never alone: it has no trigger
    # of its own, and emitting it outside front work would be the noise this instrument exists not to
    # be. `_comum` in the marker keeps it idempotent like any front.
    comum, _ = le_comum()
    if comum and not (marcar and ja_vista(sessao, "_comum")):
        partes.append("\n# ORACLE · what holds in ANY front\n\n%s" % comum)

    for f in escolhidas:
        partes.append("\n# ORACLE · front `%s`\n\n"
                      "> %s It is a **premise**, not a reminder: what follows must be\n"
                      "> checked against it, and where I diverge I say why.\n"
                      "> Source: `docs/oraculo/%s`.\n\n%s"
                      % (f["nome"], porque, f["arquivo"], f["regua"]))
    saida = "\n".join(partes) + "\n"

    if evento == "post-tool":
        # `PostToolUse` speaks through `additionalContext` — raw stdout goes only to the debug log.
        #    `PreToolUse` not even that: there is no channel to speak there (CANAIS.md §1).
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": saida}}, ensure_ascii=False))
    else:
        sys.stdout.write(saida)
    return 0


# ---------------------------------------------------------------- selftest
#
#   Two halves, as in any guard. Here the NEGATIVE half matters most: a front that is too wide
# injects a build ruler into a conversation about a changelog, and becomes the formalization that
# does not belong to the front.
CASOS = [
    # (label, prompt text, expected fronts)
    ("explicit build request",
     "we need to compile the native module on staging with cmake, run the build", {"build"}),
    ("cpp request",
     "open Worker.cpp and check the pointer to the Job before the handler", {"cpp"}),
    ("db request",
     "run a select on the jobs_queue table and check the mysql schema", {"db"}),
    ("script/guard request",
     "write a new guard in memory-guards and run the script selftest", {"scripts"}),
    ("mixed build+cpp request matches BOTH (ceiling 2)",
     "compile with cmake and fix the error in Queue.cpp in the handler", {"build", "cpp"}),

    ("product conversation matches NOTHING",
     "the worker only retries three times, decided yesterday", set()),
    ("changelog question matches NOTHING",
     "post the bilingual announcement to the team chat", set()),
    ("a passing mention is not enough alone",
     "good morning, let's get to work!", set()),

    # These three are in the OWNER's wording, not the agent's. Measuring against real prompts is
    # what showed words like `guards` and `battery` missing from the trigger. A fixture written by
    # the agent uses the agent's vocabulary and would never have caught that.
    ("owner's wording: 'guards'",
     "before moving on take a pass over the guards - analyze the errors", {"scripts"}),
    ("owner's wording: 'battery'",
     "beating this battery we can start phase 2", {"scripts"}),
    ("owner's wording: 'automate' + 'dry-run'",
     "run the automation and a dry-run confirming phase 1 too", {"scripts"}),
    ("a product symptom matches NO front — correctly",
     "it never loads, the page always spins for me", set()),
]

# Channel B: the command is mine and declares the front. One front per touch, the most specific.
CASOS_TOQUE = [
    ("bash running cmake is BUILD, not scripts",
     "cd ~/webapp/native/build && cmake --build . -j8", "build"),
    ("mysql inside ssh is DB",
     "ssh build-host 'mysql -N -B -e \"SELECT 1\"'", "db"),
    ("grep on a .cpp is CPP",
     "grep -n Tick src/native/Worker.cpp", "cpp"),
    ("a script selftest is SCRIPTS",
     "python3 scripts/oraculo.py --selftest", "scripts"),
    ("mysql called from inside a .sh is still DB",
     "bash -c 'mysql -e \"SELECT 1\"'", "db"),
    ("a neutral command matches no front",
     "ls -la /srv/webapp/docs", None),
    # -- the 2 REAL FALSE POSITIVES, turned into permanent controls ------------------------------
    #    "Not lighting" is not enough: both have a RIGHT front, and it is `scripts` in both cases.
    #    Suppressing would hide that the oracle was mute on the front actually being worked on.
    ("search pattern with .cpp, reading a .py, is SCRIPTS",
     'grep -nE "front|match|\\.cpp|\\.py" scripts/oraculo.py', "scripts"),
    ("writing a script that CONTAINS `make install` is SCRIPTS, not build",
     "cat > scripts/write-guard.py <<'EOF'\nWRITES = 'make install|git push|systemctl'\nEOF\nchmod +x scripts/write-guard.py", "scripts"),
    ("git status matches no front",
     "git status --short", None),
]


def selftest():
    falhas = 0
    frentes, problemas = le_fontes()
    print("   sources read: %d" % len(frentes))
    for p in problemas:
        print("   \033[31m✗\033[0m source with a problem: %s" % p)
        falhas += 1
    if not frentes:
        print("   \033[31m✗\033[0m NO source — the oracle would be mute and green")
        return 1

    for rotulo, texto, esperado in CASOS:
        got = {f["nome"] for f in casa(texto, frentes)}
        ok = got == esperado
        falhas += 0 if ok else 1
        print("   %s %-46s %s%s"
              % ("\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m", rotulo,
                 sorted(got) or "—",
                 "" if ok else "  ← expected %s" % (sorted(esperado) or "—")))

    print("   --- channel B (my command declares the front)")
    for rotulo, cmd, esperado in CASOS_TOQUE:
        got = [f["nome"] for f in casa_toque(cmd, frentes)]
        got1 = got[0] if got else None
        ok = got1 == esperado
        falhas += 0 if ok else 1
        print("   %s %-46s %s%s"
              % ("\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m", rotulo, got1 or "—",
                 "" if ok else "  ← expected %s" % (esperado or "—")))

    #   BUDGET — and it WATCHED THE WRONG DOOR at first.
    #   The indicator only warned when a source OVERFLOWED, and what overflows in practice is not a
    # new premise: it is an **existing item getting fatter**. Measured: one source went from 2,896
    # to 8,952 bytes in ONE day with almost no new premise. When the alarm rings it is already late.
    #   The valve: from AVISO_PCT of the ceiling on, the selftest names the heaviest premises of the
    # source. It mechanizes a rule that README §5 already gave by eye — and a rule that depends on
    # remembering to look is a rule that does not hold.
    AVISO_PCT = 85
    #   THE AGGREGATE COMES BEFORE THE PER-FRONT on purpose: it is what answers what reaches a
    # session. Reading the individual lines first makes each one look under control.
    _comum_b = le_comum()[1]      # returns (text, bytes) — the byte count is already there
    _soma = sum(f["bytes"] for f in frentes) + _comum_b
    _ok_ag = _soma <= TETO_AGREGADO
    falhas += 0 if _ok_ag else 1
    print("   --- AGGREGATE budget (blocks at %d B · target %d B = the cost of the map)"
          % (TETO_AGREGADO, ALVO_AGREGADO))
    print("   %s %d B in the %d front(s) + _comum — %d%% of what blocks"
          % ("\033[32m✓\033[0m" if _ok_ag else "\033[31m✗\033[0m",
             _soma, len(frentes), _soma * 100 // TETO_AGREGADO))
    if _soma > ALVO_AGREGADO:
        print("     \033[33m⚠ %d B above the TARGET — the oracle costs %d%% more than the map. "
              "The door must push down; PORTA-ORAC-AGREGADO collects it\033[0m"
              % (_soma - ALVO_AGREGADO, (_soma - ALVO_AGREGADO) * 100 // ALVO_AGREGADO))
    if not _ok_ag:
        print("     \033[31m✗ OVER the tare — for something to enter, something leaves "
              "(oraculo/README §5). Raising the number is not a destination.\033[0m")

    print("   --- budget per front (ceiling %d bytes · warning from %d%%)"
          % (TETO_BYTES, AVISO_PCT))
    for f in sorted(frentes, key=lambda x: -x["bytes"]):
        ok = f["bytes"] <= TETO_BYTES
        falhas += 0 if ok else 1
        pct = f["bytes"] * 100 // TETO_BYTES
        print("   %s %-46s %5d bytes  ~%4d tokens  %d%%"
              % ("\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m",
                 f["nome"], f["bytes"], f["bytes"] / 3.6, pct))
        if pct < AVISO_PCT:
            continue
        # who is getting fat? names the 3 heaviest premises, which is where the revolving door must
        # be applied — not on the first one in sight when the ceiling breaks.
        try:
            corpo = (FONTES / ("%s.md" % f["nome"])).read_text(encoding="utf-8")
        except OSError:
            continue
        secs = re.split(r"(?m)^(### .*)$", corpo.split("## PREMISES", 1)[-1])
        pesos = sorted((((len((secs[i] + secs[i + 1]).encode())), secs[i].strip()[4:52])
                        for i in range(1, len(secs), 2)), reverse=True)
        print("      \033[33m⚠ %d%% of the ceiling — the heaviest (the revolving door starts here):\033[0m"
              % pct)
        for b, titulo in pesos[:3]:
            print("        %5d B  %s" % (b, titulo))

    # idempotence: the same front does not come out twice in the same session
    import tempfile
    global CACHE
    velho = CACHE
    CACHE = Path(tempfile.mkdtemp())
    try:
        a = ja_vista("sessao-de-teste", "build")
        b = ja_vista("sessao-de-teste", "build")
        ok = (a is False and b is True)
        falhas += 0 if ok else 1
        print("   %s %-46s 1st=%s 2nd=%s"
              % ("\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m",
                 "idempotence: 2nd prompt does not repeat", a, b))
    finally:
        CACHE = velho

    # ORDERING of the premises. Two sessions feeding a source and inserting in the middle without
    # renumbering produce `7 → 7.2 → 7.1 → 8`. An out-of-order source breaks nothing in the engine:
    # it breaks the READING, and an unreadable ruler is a ruler not applied. Cheap to check,
    # invisible without checking.
    print("   --- ordering of the premises (contract §3)")
    import glob as _g
    for arq in sorted(_g.glob(str(FONTES / "*.md"))):
        nome = os.path.basename(arq)
        if nome.startswith(("README", "BASELINE")):
            continue
        txt = open(arq, encoding="utf-8").read()
        if "## PREMISES" not in txt:
            continue
        nums = []
        for t in re.findall(r"^### ([\d.]+)", txt.split("## PREMISES", 1)[1], re.M):
            try:
                nums.append(tuple(int(x) for x in t.split(".")))
            except ValueError:
                pass
        ok = nums == sorted(nums)
        falhas += 0 if ok else 1
        fora = [".".join(str(y) for y in n) for n, s in zip(nums, sorted(nums)) if n != s]
        print("   %s %-46s %d premises%s"
              % ("\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m", nome, len(nums),
                 "" if ok else "  ← OUT OF ORDER: %s" % ", ".join(fora[:4])))

    #   BALLAST of the premises (contract §3). The ruler enters the context **as a premise**, before
    # the work — so an item without ballast is not just a weak doc: it is **a guess with the force of
    # a ruler**.
    #   The kind is DECLARED, not inferred: two predicates that tried to guess "does this have
    # evidence?" gave 25 and 18 of 40, and inspection overturned both in both directions. A guard
    # that judges does not converge; a guard that checks FORMAT does.
    #   So the predicate is literal: either the item says `Measured…` (LESSON, with number and
    # population), or `**Source:**` (PROCEDURE, with a pointer to whoever rules). Neither = fail.
    print("   --- ballast of the premises (contract §3: LESSON has `Measured`, PROCEDURE has `Source:`)")
    rx_lastro = re.compile(r"\bMeasured\b|\bmeasured\b|\*\*Source:\*\*")
    for arq in sorted(_g.glob(str(FONTES / "*.md"))):
        nome = os.path.basename(arq)
        if nome.startswith(("README", "BASELINE")):
            continue
        txt = open(arq, encoding="utf-8").read()
        if "## PREMISES" not in txt:
            continue
        secs = re.split(r"(?m)^(### .*)$", txt.split("## PREMISES", 1)[1])
        sem = [secs[i].strip()[4:44] for i in range(1, len(secs), 2)
               if not rx_lastro.search(secs[i] + secs[i + 1])]
        n = (len(secs) - 1) // 2
        if n == 0:
            falhas += 1
            print("   \033[31m✗\033[0m %-46s NO PREMISE — population 0 is not green" % nome)
            continue
        falhas += 0 if not sem else 1
        print("   %s %-46s %d of %d with ballast%s"
              % ("\033[32m✓\033[0m" if not sem else "\033[31m✗\033[0m", nome, n - len(sem), n,
                 "" if not sem else "  ← GUESS: %s" % "; ".join(sem[:3])))

    # the common preamble: it cannot become a front, and it pays budget like any ruler
    comum, nb = le_comum()
    ok = comum is not None
    falhas += 0 if ok else 1
    print("   %s %-46s %s"
          % ("\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m",
             "common preamble exists and has PREMISES", "%d bytes" % nb if ok else "ABSENT"))
    ok = "_comum" not in {f["nome"] for f in frentes}
    falhas += 0 if ok else 1
    print("   %s %-46s %d fronts"
          % ("\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m",
             "common does NOT become a front (no trigger)", len(frentes)))
    ok = nb <= TETO_BYTES
    falhas += 0 if ok else 1
    print("   %s %-46s %d ≤ %d"
          % ("\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m",
             "common under the budget ceiling", nb, TETO_BYTES))

    # cost guard: with every front already seen, the shortcut must close BEFORE reading a source
    import tempfile
    velho = CACHE
    CACHE = Path(tempfile.mkdtemp())
    try:
        antes = tudo_ja_visto("sessao-custo")
        for n in nomes_das_frentes():
            ja_vista("sessao-custo", n)
        depois = tudo_ja_visto("sessao-custo")
        ok = (antes is False and depois is True)
        falhas += 0 if ok else 1
        print("   %s %-46s before=%s after=%s"
              % ("\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m",
                 "cost guard: shortcut closes with all seen", antes, depois))
    finally:
        CACHE = velho

    # front ceiling: a text that cites all four cannot dump all four
    quatro = "compile Body.cpp with cmake, run the script selftest and check the table in mysql"
    n = len(casa(quatro, frentes))
    ok = n <= MAX_FRENTES
    falhas += 0 if ok else 1
    print("   %s %-46s %d fronts (ceiling %d)"
          % ("\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m",
             "front ceiling: a request citing all 4", n, MAX_FRENTES))

    print("\n%s" % ("\033[32m✓ oracle selftest OK\033[0m" if not falhas
                    else "\033[31m✗ %d FAILURE(S)\033[0m" % falhas))
    return 1 if falhas else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--frentes" in sys.argv:
        fs, probs = le_fontes()
        for f in fs:
            print("  %-10s %5d bytes  trigger: %s" % (f["nome"], f["bytes"], f["rx"].pattern[:90]))
        for p in probs:
            print("  ⚠️ %s" % p)
        sys.exit(0)
    if "--texto" in sys.argv:
        i = sys.argv.index("--texto")
        sys.exit(main(texto=sys.argv[i + 1], sessao="", marcar=False))
    ev = "prompt"
    if "--evento" in sys.argv:
        ev = sys.argv[sys.argv.index("--evento") + 1]
    sys.exit(main(evento=ev))
