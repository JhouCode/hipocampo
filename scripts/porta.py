#!/usr/bin/env python3
"""THE REVOLVING-DOOR PIPELINE — *paid, swapped*.

  The requirement: when a piece of work is concluded (a milestone, the end of a turn, anything),
the oracle must refresh and things must go to their place before the next one — triggered at the
moment of conclusion, where the commits happen, and automated so it does not depend on memory.

  And the condition attached to that authorization: *if something leaves or enters, it goes through
a commit, and the commit holds the cause and the timestamp.*
**An automatic move without a cause recorded in the commit is a bug, not a convenience.**

WHAT IT DOES — and what it deliberately does NOT do
  DETECTS the state of the doors, DERIVES who leaves and to where from the layer's destination
  table, and COLLECTS what did not leave by writing `docs/gatilhos/porta.md`, which `gatilho.py`
  already knows how to deliver (D1 warns → D2 collects at end of turn → D3 BLOCKS). The escalation
  is what makes this independent of anyone remembering.
  It does NOT rewrite rulers or laws. Moving curated content is judgement, and automation that
  rewrites a ruler on its own errs in silence — the failure mode this whole system exists to kill.
  It proposes with a derived destination; the hand is a person's.

ANTI-LOOP: it runs in `post-commit`, and a commit of its own would fire the hook again. It exits
at once if HEAD is already its own commit (prefix `porta:`) or if `PORTA_EM_EXECUCAO` is set.

USAGE
  porta.py                 measures and rewrites the trigger source
  porta.py --seco          measures and prints, writes nothing
  porta.py --selftest      positive and negative controls of the predicates
"""
import datetime
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipo_config as HC  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "docs" / "gatilhos" / "porta.md"
MEM = Path(os.environ.get("MEM_DIR", HC.MEMORY_DIR))
TETO_ORACULO = 9000
AVISO_PCT = 85


def sh(*a, cwd=None):
    r = subprocess.run(list(a), capture_output=True, text=True, errors="replace", cwd=cwd or RAIZ)
    return r.stdout


# ── DOOR 1 · ORACLE: a saturated source must turn ───────────────────────────
#   THE ARITHMETIC COMES FROM `oraculo.py`, NEVER REDONE HERE. The first version measured
# `len(file)` and said a source was at 102% while `--frentes` said 95%: the oracle measures the
# EXTRACTED RULER, without the contract header and the trigger. Two numbers with the same name —
# whoever consumes them cannot tell which one rules, and the wrong one is always the one on screen.
def _fontes_do_oraculo():
    import importlib.util
    o = RAIZ / "scripts" / "oraculo.py"
    if not o.exists():
        return None
    spec = importlib.util.spec_from_file_location("orc", o)
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
        frentes, _probs = m.le_fontes()
        return ([(f["nome"], len(f["regua"].encode()), m.TETO_BYTES) for f in frentes],
                getattr(m, "TETO_AGREGADO", None), getattr(m, "ALVO_AGREGADO", None),
                m.le_comum()[1])
    except Exception:
        return None


def porta_oraculo():
    lido = _fontes_do_oraculo()
    fontes = lido[0] if lido else None
    if fontes is None:
        return [{
            "id": "PORTA-ORAC-MUDA",
            "casa": r"docs/oraculo/",
            "diz": "🚧 **could not measure the fronts** — `scripts/oraculo.py` did not answer. "
                   "The oracle door is BLIND, not empty",
            "passo": "Run `scripts/oraculo.py --selftest`; while it does not answer, no front "
                     "saturation is detected and silence here is not green",
            "degrau": "D1",
        }]
    return _decide_oraculo(fontes) + _agregado(fontes, lido[1], lido[2], lido[3])


def _agregado(fontes, teto_ag, alvo, comum_b):
    """The ceiling is PER FRONT and there was NO ceiling for the whole — and the sum is what arrives.

    Every front can grow to its ceiling with CI green all the way; together that is an implicit
    ceiling nobody declared. And what reaches a session is not the maximum — it is the sum of the
    fronts that light up.

    THIS WARNING DOES NOT ESTIMATE A DEADLINE, deliberately. The known growth pace was measured in
    FILE BYTES; the slack here is in EXTRACTED RULER. Dividing one by the other gives a number that
    looks like an answer and mixes two quantities. When a ruler series exists, the deadline enters;
    until then, the number is the slack.
    """
    #   THE CEILING COMES FROM `oraculo.py`, NEVER RECOMPUTED HERE — it was declared there as the TARE
    # (the value measured that day, frozen). Summing the per-front ceilings would give ANOTHER number
    # with the same name.
    if not fontes or not teto_ag:
        return []
    soma = sum(n for _, n, _ in fontes) + (comum_b or 0)
    #   SETTLEMENT IS AGAINST THE TARGET, not the tare. The debt was always "N B above the TARGET";
    # without this branch, a paid target kept the warning lit up to 70% of the TARE, printing
    # "-8 B above" — a paid debt becoming a repeated warning. The tare still blocks in CI
    # (oraculo.py); a regression above the target lights this again.
    if alvo and soma <= alvo:
        return []
    pct = soma * 100 // teto_ag
    if pct < 70:
        return []
    return [{
        "id": "PORTA-ORAC-AGREGADO",
        "casa": r"docs/oraculo/",
        "diz": "🚧 the aggregate is at **%d%% of the tare** (%d of %d B **of extracted ruler, from the %d "
               "fronts PLUS `_comum`**) and **%d B above the TARGET** (%d B = the load cost of the "
               "map). The tare blocks in CI; the target is where the door pushes"
               % (pct, soma, teto_ag, len(fontes), soma - (alvo or soma), alvo or 0),
        "passo": "The tare has ZERO slack by construction: every addition blocks, and the way out is "
                 "the door (`oraculo/README §5`) — for something to enter, something leaves. To close "
                 "the debt against the target, the oracle `--selftest` already names the heaviest "
                 "premises of each front; start with those, not the first one in sight",
        "degrau": "D1",
    }]


def _decide_oraculo(fontes):
    """The PREDICATE, separated from the reading — this is the half the selftest exercises with a
    fixture. The other half (reading and measuring the ruler) belongs to `oraculo.py`, which has its
    own selftest: testing it again here would be the second truth coming back through the back door."""
    itens = []
    for nome, n, teto in sorted(fontes):
        pct = n * 100 // teto
        if pct >= AVISO_PCT:
            itens.append({
                "id": "PORTA-ORAC-%s" % nome.upper(),
                "casa": r"docs/oraculo/%s\.md" % nome,
                #   THE UNIT GOES IN THE NUMBER, not in a code comment: `PORTA-PLACAR` next to it
                # publishes FILE bytes, and both would appear together in the same context. Say the
                # unit and the population out loud, then read the name you gave — if the name
                # promises more than that sentence, the name is wrong.
                "diz": "🚧 front `%s` is at **%d%% of the ceiling** (%d of %d B **of extracted "
                       "ruler**, without the contract header) — the revolving door starts here, "
                       "and 'raise the ceiling' is not a destination" % (nome, pct, n, teto),
                "passo": "Choose the premise that leaves and its destination from the table in "
                         "`oraculo/README §5`: 1 became a guard · 2 became a map law · 3 became a "
                         "front doc · 4 shrank. The pointer that stays is ONE line — a farewell "
                         "paragraph is not a way out",
                "degrau": "D1",
            })
    return itens


# ── DOOR 2 · MAP: a law with a guard should not be in the reminder ──────────
#   ASKS THE HOOK ITSELF WHAT IT EMITS, instead of recounting the glyph in the doc. The first version
# counted the `⚙` in `3_DECIDIDO` and kept saying "10 laws still go out" AFTER four had left —
# second truth, the same defect `porta_oraculo` had already paid. Whoever knows what reaches the
# core is `mapa-hook.sh`, not the table.
def porta_mapa():
    c3 = RAIZ / "docs" / "mapa" / "3_DECIDIDO.md"
    hook = RAIZ / "scripts" / "mapa-hook.sh"
    if not c3.exists() or not hook.exists():
        return []
    com_guarda = set()
    for l in c3.read_text(encoding="utf-8").splitlines():
        if l.startswith("|") and "IN FORCE ⚙" in l:
            p = l.split("|")
            if len(p) > 2:
                com_guarda.add(p[1].strip())
    nucleo = sh("bash", str(hook), "--nucleo")
    ainda = sorted(i for i in com_guarda
                   if re.search(r"^- \*\*%s\*\*" % re.escape(i), nucleo, re.M))
    if not ainda:
        return []
    return [{
        "id": "PORTA-MAPA-NUCLEO",
        "diz": "🚧 **%d of %d laws with a guard (⚙) still go out in the core** (%s) — for a law to "
               "leave, its guard must NAME it in its `# @guard` header (e.g. *'covers the law P14'*). "
               "These have a guard borrowed from another purpose, cited as proof"
               % (len(ainda), len(com_guarda), " ".join(ainda)),
        "casa": r"(docs/mapa/3_DECIDIDO|mapa-hook|guards/memory-guards)",
        "passo": "The `@guard` predicate is TRIAGE, not a verdict — it is lexical, and a guard can "
                 "cover without naming. To really decide: **inject a violation of EACH clause of "
                 "the statement and watch the guard light up**. If it lights on all, the law "
                 "leaves — named or not. Reading the predicate and believing it covers is a "
                 "hypothesis. Until someone injects, these stay, and staying is the safe side",
        "degrau": "D1",
    }]


#   AGE FLOOR — a freshly written memory is not an orphan, it is NEWBORN. Measured: all the memories
# the door accused were ≤ 7 days old (`git log --diff-filter=A`), and the youngest was written 20 min
# earlier by the very session that read the warning. Never-opened and never-cited is the NORMAL state
# in the first days: nobody had a chance to open it, and citations in the channels come later.
# Without a floor the door accuses the most RECENT work forever, and each firing costs a ride.
#   THE VALUE IS A DOMAIN CUT and moves the number, like the anchor regex: say why when changing it.
IDADE_MIN_DIAS = 14


def _nascimento(raiz=None):
    """Creation date of every memory in ONE git call — the door runs on every `PostToolUse`, and one
    call per name would be expensive. Without git or history it returns `{}`, and then the floor
    filters nothing: **it fails towards ACCUSING**, the safe side of a door."""
    r = raiz or RAIZ
    out = sh("git", "log", "--diff-filter=A", "--reverse", "--date=short",
             "--format=@%ad", "--name-only", "--", "memoria/", cwd=str(r))
    nasc, data = {}, None
    for l in out.splitlines():
        l = l.strip()
        if l.startswith("@"):
            data = l[1:]
        elif l.endswith(".md") and data:
            nasc.setdefault(l.split("/")[-1][:-3], data)
    return nasc


# ── DOOR 3 · MEMORY: an orphan weighs on the tare and arrives by no channel ─
def porta_memoria(recall=None, nascimento=None, hoje=None):
    """Orphan = never opened AND not cited in anything that loads. It is not garbage: it is
    knowledge WITHOUT A TRIGGER, which is something else (`docs/guardas/memoria.md`).

    TWO QUEUES, and mixing them produces false proof of irrelevance:
      · WITH a concrete anchor (path, extension, host, command in backticks): giving it a
        `when it matches` works.
      · WITHOUT an anchor: rules about how the agent TALKS and DECIDES. No command lights them,
        because they do not apply to a file — they apply to the agent. Giving them a trigger
        produces noise, they do not light, and the silence becomes "evidence" they were useless.
        Many are already distilled in layer 1 of the map, which arrives every session.

    AND THE ORPHAN COUNT ITSELF IS INFLATED — declared blindness, not an estimate. The "arrives by
    another channel" predicate below is LEXICAL: it looks for the memory's NAME in the channels. But
    the map DISTILLS WITHOUT CITING, so every memory distilled without a citation falls in the wrong
    queue. How many? Measuring it is a semantic comparison. The number here is a CEILING, not a count.
    """
    if recall is None:
        return []
    #   `_proposals` is a channel because a triage there classified the whole store and the owner
    # decided the batch — a memory listed there was seen and judged, and an orphan is what was NEVER
    # seen. A new memory, outside the triage, keeps being accused.
    canais = [RAIZ / "docs" / "mapa", RAIZ / "docs" / "oraculo", RAIZ / "docs" / "gatilhos",
              RAIZ / "docs" / "_proposals", RAIZ / "guards" / "memory-guards.sh"]
    orfas = []
    for nome in recall:
        achou = False
        for c in canais:
            #   `grep -l` returns PATHS; the old predicate (`name in output`) compared the name
            # against the path and never matched — the channel filter was dead letter and orphan
            # became a synonym of never-opened. Proven failing by the TRIAGED control: the question
            # is "did grep find ANYTHING?", not "is the name in the path?".
            if c.exists() and sh("grep", "-rlF", nome, str(c)).strip():
                achou = True
                break
        if not achou:
            orfas.append(nome)
    #   THE FLOOR (see IDADE_MIN_DIAS): removes the newborn, not the abandoned. `nascimento` and
    # `hoje` come in by parameter so the selftest can pin both ends.
    nasc = _nascimento() if nascimento is None else nascimento
    if nasc:
        hoje = hoje or datetime.date.today()
        velhas = []
        for n in orfas:
            d = nasc.get(n)
            if d is None:
                continue                      # not committed yet = just born
            a = datetime.date(*map(int, d.split("-")))
            if (hoje - a).days >= IDADE_MIN_DIAS:
                velhas.append(n)
        orfas = velhas

    if not orfas:
        return []

    #   WHAT COUNTS AS AN ANCHOR IS A PROJECT CHOICE, AND IT MOVES THE NUMBER. Measured: adding the
    # host names to the list moved the split by eight points, for a decision nobody had declared.
    # Changing this regex changes the number: say why.
    ancora = re.compile(r"`[^`]*(/|\.(sh|py|cpp|h|md|json|sql|conf)|(build|app)-host"
                        r"|mysql|git |ssh |grep |make)[^`]*`")
    com, sem = [], []
    for n in orfas:
        f = RAIZ / "memoria" / ("%s.md" % n)
        (com if (f.exists() and ancora.search(f.read_text(encoding="utf-8", errors="replace")))
         else sem).append(n)

    return [{
        "id": "PORTA-MEM-ORFAS",
        "casa": r"(MEMORY\.md|memoria/|memoria-recall)",
        "diz": "🚧 **up to %d orphan memories** (%d with a command anchor, %d WITHOUT) — never opened "
               "and not cited in the channels. They are the biggest READING tare of the system. "
               "The number is a CEILING: the predicate is lexical and the map distills WITHOUT citing"
               % (len(orfas), len(com), len(sem)),
        "passo": "TWO queues, and mixing them produces false proof of irrelevance. The %d WITH an "
                 "anchor: give them a `when it matches` and take them out of the index. The %d "
                 "WITHOUT an anchor are rules about how the agent talks and decides — no command "
                 "lights them, and many are already in layer 1 of the map; those go to TRIAGE, not "
                 "to a trigger. A domain cut is the owner's decision" % (len(com), len(sem)),
        "degrau": "D1",
    }]


# ── THE SCOREBOARD · the number that answers 'did the pipeline work?' ───────
def placar():
    """Is the door PAYING? — and the answer is STATE, never an event count.

    The first two versions counted commits with the `porta:` prefix, and both measured DELIVERY
    when the question is EFFECT. Measured: **7 commits with the prefix against ~18 that actually
    reduced** a file covered by the door — one of them titled *"the revolving door pays in the same
    commit"* did not count, because the prefix was missing.
      And what kills the metric is not the count: it is the size series. While the event scoreboard
    said "there was movement, it works", the size of the largest front GREW. The two disagreed, and
    the wrong one was the scoreboard.
      Counting events also rewards whoever writes `porta:` in a commit. Measuring state rewards
    whoever SHRINKS, which is the behaviour the door exists to produce.

    The quantity here is FILE BYTES at both points of the series, not the extracted ruler that
    `oraculo.py` measures — history comes from `git show`, and there only the file exists.
    Homogeneous with itself, so it answers "did it go down?"; not comparable with `--frentes` %.
    """
    d = RAIZ / "docs" / "oraculo"
    #   The window is 30 days OR the age of the source, whichever is SMALLER — and it is declared in
    # the warning. A declared short window measures; an absent ideal window does not.
    #
    #   AND A DECLARED WINDOW STILL LIES IF THE ANCHOR FALLS ON THE SOURCE'S INITIAL FILLING.
    # Anchored at the birth commit, the first version said "the peak MORE THAN DOUBLED, the door is
    # not paying" — a false accusation: the sources existed as sketches at birth and were written in
    # the following hours. Comparing with the sketch measures the source BEING WRITTEN, not the door
    # turning. Anchored after stabilization, the same series showed the door PAID.
    #   So the instrument prints the SERIES, not two points, and when the anchor falls near the birth
    # it SAYS so instead of giving a binary verdict.
    sha = sh("git", "log", "--until=30 days ago", "-1", "--format=%H").strip()
    if sha and not sh("git", "show", "%s:docs/oraculo/cpp.md" % sha):
        sha = sh("git", "log", "--diff-filter=A", "--format=%H", "--", "docs/oraculo/cpp.md").strip().splitlines()
        sha = sha[-1] if sha else ""
    desde = sh("git", "log", "-1", "--format=%ad", "--date=short", sha).strip() if sha else "?"
    hoje, antes = [], []
    for md in sorted(d.glob("*.md")):
        if md.name in ("README.md", "BASELINE_T0.md") or md.name.startswith("_"):
            continue
        hoje.append((len(md.read_bytes()), md.stem))
        if sha:
            velho = sh("git", "show", "%s:docs/oraculo/%s" % (sha, md.name))
            if velho:
                antes.append((len(velho.encode()), md.stem))
    if not hoje:
        return []
    pico_h, nome_h = max(hoje)
    if not antes:
        return [{
            "id": "PORTA-PLACAR", "casa": r"docs/oraculo/",
            "diz": "📊 **no series** — there is no version from 30 days ago to compare. The door is "
                   "not measured, and that is declared blindness, not green",
            "passo": "Wait for the series to fill; from then on the criterion is the fullest front "
                     "GOING DOWN",
            "degrau": "RULE"}]
    pico_a, nome_a = max(antes)
    desceu = pico_h < pico_a
    # is the anchor young? then the starting point may be a sketch, and the verdict does not hold
    nasceu = sh("git", "log", "--diff-filter=A", "--format=%at", "--", "docs/oraculo/cpp.md").strip()
    nasceu = int(nasceu.splitlines()[-1]) if nasceu else 0
    t_anc = sh("git", "log", "-1", "--format=%at", sha).strip()
    verde = (int(t_anc) - nasceu) > 86400 if (t_anc and nasceu) else False
    #   PEAK AND TOTAL ANSWER DIFFERENT QUESTIONS, AND MEASURING ONLY ONE ALLOWS A FALSE VICTORY.
    # Measured: the PEAK went down 655 B while the TOTAL went up 16%, because the other fronts grew.
    # The peak answers "will it break the ceiling?"; the total answers "is it weighing more in the
    # context?". Both matter, and one alone hides the other.
    tot_h, tot_a = sum(b for b, _ in hoje), sum(b for b, _ in antes)
    serie = "peak %s %d → %s %d · total %d → %d" % (nome_a, pico_a, nome_h, pico_h, tot_a, tot_h)
    if not verde:
        return [{
            "id": "PORTA-PLACAR", "casa": r"docs/oraculo/",
            "diz": "📊 **series too short for a verdict** — the anchor (%s) is less than 24 h from "
                   "the birth of the source, when it was still being WRITTEN. Comparing with the "
                   "sketch measures the writing, not the door. Series (FILE bytes): %s" % (desde, serie),
            "passo": "Wait for the window to pass 24 h after the source's birth. Until then the "
                     "number exists but is NOT a verdict — and saying so is different from staying mute",
            "degrau": "RULE"}]
    return [{
        "id": "PORTA-PLACAR",
        "casa": r"docs/oraculo/",
        "diz": "📊 since %s — **peak %s** (%s %d → %s %d) and **total %s** (%d → %d B of FILE). %s"
               % (desde, "WENT DOWN" if desceu else "went up", nome_a, pico_a, nome_h, pico_h,
                  "went down" if tot_h < tot_a else "WENT UP", tot_a, tot_h,
                  "The door is paying on both." if (desceu and tot_h < tot_a) else
                  "🚧 The two disagree: the ceiling gives way and the load grows — the door holds "
                  "the overflow but not the sum." if desceu else
                  "🚧 **The door is NOT paying.**"),
        "passo": "The death criterion is STATE, not event: if the peak does not go down for a month "
                 "with the pipeline installed, it did not work and the right thing is to REMOVE it. "
                 "Full series: `git show <sha>:docs/oraculo/<front>.md | wc -c`. This byte is of "
                 "FILE; the % that `PORTA-ORAC-*` collects is of EXTRACTED RULER. Two measures with "
                 "similar names — do not compare one with the other",
        "degrau": "RULE",
    }]


CABECALHO = """# Source `porta` — the revolving door charging itself

> **A trigger source of the dispatcher**, generated by [`scripts/porta.py`](../../scripts/porta.py)
> in the `post-commit` hook: *paid, swapped* — on concluding, things go to their place before the
> next round, and that cannot depend on anyone remembering.
>
> **THIS FILE IS GENERATED. Do not edit it by hand** — the next run overwrites it. What you edit is
> `porta.py`. What is preserved between runs: the `~~paid~~` rows (kept as proof that the trigger
> worked), the `rides` counter of each item, and a `⏸` wait marker put by hand in the `step` cell.
>
> **Why it collects instead of moving:** moving curated content is judgement. The pipeline derives
> the destination from the layer's table and PROPOSES; a person writes the ruler. Automation that
> rewrites a ruler on its own errs in silence.
>
> **The death criterion, declared before birth:** if `PORTA-PLACAR` stays at zero for a month with
> this source installed, the pipeline did not work and the right answer is to REMOVE it.

| id | when it matches | what to say | NEXT STEP | step | rides |
|---|---|---|---|---|---|
"""


def linhas_pagas():
    """The `~~paid~~` rows survive regeneration — they are the proof that the door turned."""
    if not FONTE.exists():
        return []
    return [l for l in FONTE.read_text(encoding="utf-8").splitlines()
            if l.startswith("| ~~")]


def _celulas(linha):
    r"""Splits a table row RESPECTING THE `\|` ESCAPE.

    A raw `split("|")` counts the escaped pipe as a separator and shifts EVERY following column.
    Measured: the `PORTA-MEM-ORFAS` row gave **10 fields where there should be 8**, and `rides` was
    read from inside the warning text — the counter of the ladder to D3 came from a sentence, not a
    number. Escaping on write without unescaping on read is half a fix, and half a fix here disarms
    the collection in silence.
    """
    return [c.strip() for c in re.split(r"(?<!\\)\|", linha)]


def caronas_de(texto):
    """Preserves the rides counter: resetting it on every run would disarm the ladder to D3."""
    d = {}
    for l in texto.splitlines():
        if not l.startswith("|"):
            continue
        p = _celulas(l)
        if len(p) >= 7 and p[1].startswith("**"):
            d[p[1].strip("*")] = p[6]
    return d


def marcadores_de(texto):
    """Preserves the WAIT marker of the `step` cell (`D1 ⏸evento 2026-09-30`), as `caronas_de`
    preserves the counter. Phase B of the rides counter: the marker is put BY HAND in a GENERATED
    source, and without this the next run of the `post-commit` hook would erase it silently -- the
    wait would vanish and the frozen rides would go back to adding and blocking, with nobody having
    decided. Returns only the suffix from the `⏸` on; the kind (`D1`/`RULE`) keeps coming from the
    generator."""
    d = {}
    for l in texto.splitlines():
        if not l.startswith("|"):
            continue
        p = _celulas(l)
        if len(p) >= 7 and p[1].startswith("**") and "⏸" in p[5]:
            d[p[1].strip("*")] = p[5][p[5].index("⏸"):].strip()
    return d


def _esc(t):
    r"""The `|` of an ERE alternation BREAKS THE COLUMN of the table — the `gatilho.py` parser counts
    raw pipes and DISCARDS the whole row, warning but discarding. Measured: two regexes with
    alternation became '7 columns, expected 6' and both items vanished from the source. The backlog
    source already escaped as `\|`; look at the neighbour before generating."""
    return t.replace("|", "\\|")


def escreve(itens):
    antigas = FONTE.read_text(encoding="utf-8") if FONTE.exists() else ""
    car = caronas_de(antigas)
    esp = marcadores_de(antigas)
    pagas = linhas_pagas()
    out = [CABECALHO.rstrip("\n")]
    for it in itens:
        n = car.get(it["id"], "0")
        # A RULE takes no wait (it does not escalate anyway) -- the marker only comes back on a debt.
        degrau = it["degrau"]
        if it["id"] in esp and degrau != "RULE":
            degrau = "%s %s" % (degrau, esp[it["id"]])
        out.append("| **%s** | `%s` | %s | %s | %s | %s |" %
                   (it["id"], _esc(it["casa"]), _esc(it["diz"]), _esc(it["passo"]),
                    degrau, n))
    out.extend(pagas)
    FONTE.parent.mkdir(parents=True, exist_ok=True)
    FONTE.write_text("\n".join(out) + "\n", encoding="utf-8")


def recall_orfas():
    """Runs the instrument that already exists. If it is not here, the memory door goes MUTE and
    declares it — better than inventing its own recall and having two truths diverging."""
    r = RAIZ / "scripts" / "memoria-recall.py"
    if not r.exists():
        return None
    saida = sh("python3", str(r), "--nunca")
    nomes = [l.strip() for l in saida.splitlines()
             if l.startswith("  ") and re.match(r"^\s+[a-z][a-z0-9_]+$", l)]
    return nomes or None


def monta():
    itens = []
    itens += porta_mapa()
    itens += porta_oraculo()
    itens += porta_memoria(recall_orfas())
    itens += placar()
    return itens


def selftest():
    ok = ruim = 0

    def diz(bom, rot, extra=""):
        nonlocal ok, ruim
        if bom:
            ok += 1
            print("  \033[32m✓\033[0m %s %s" % (rot, extra))
        else:
            ruim += 1
            print("  \033[31m✗\033[0m %s %s" % (rot, extra))

    #   The WAIT survives regeneration (phase B of the rides counter, 2026-09-30). Runs FIRST and on a
    # TEMPORARY source: it does not depend on the tree (a mutant fixture runs in an empty repo) and
    # it does not write the real `porta.md`.
    global FONTE
    import tempfile
    _guarda = FONTE
    try:
        with tempfile.TemporaryDirectory() as td:
            FONTE = Path(td) / "porta.md"
            FONTE.write_text(CABECALHO +
                             "| **PX** | `x` | says | step | D1 ⏸evento 2026-09-30 | 7 |\n"
                             "| **PY** | `y` | says | step | D1 | 2 |\n", encoding="utf-8")
            escreve([{"id": i, "casa": i.lower(), "diz": "says", "passo": "step", "degrau": "D1"}
                     for i in ("PX", "PY")])
            _deg = {p[1].strip("*"): p[5] for p in map(_celulas, FONTE.read_text().splitlines())
                    if len(p) >= 7 and p[1].startswith("**")}
    finally:
        FONTE = _guarda
    diz(_deg.get("PX") == "D1 ⏸evento 2026-09-30",
        "the ⏸ marker of the step survives regeneration", "(PX=%r)" % _deg.get("PX"))
    diz(_deg.get("PY") == "D1", "and an item without a marker stays plain D1 (control)", "(PY=%r)" % _deg.get("PY"))

    itens = monta()
    ids = [i["id"] for i in itens]
    diz(len(itens) > 0, "the pipeline detects at least one item", "(%d)" % len(itens))
    diz("PORTA-PLACAR" in ids, "the scoreboard ALWAYS comes out — it measures the pipeline itself", "")
    diz(all(i["passo"].strip() for i in itens), "every item has a NEXT STEP (contract, 6 columns)", "")
    diz(all(i["degrau"] in ("D1", "RULE") for i in itens), "step only D1 or RULE", "")
    diz(sum(1 for i in itens if i["degrau"] == "RULE" and i["id"] != "PORTA-PLACAR") == 0,
        "only the scoreboard is RULE — a debt that does not expire does not escalate to D3", "")

    # CONTROL of the oracle PREDICATE — fixture, because the reading belongs to oraculo.py
    diz(_decide_oraculo([("magra", 100, 9000)]) == [],
        "NEGATIVE: a source at 1% of the ceiling does not become an item", "")
    diz(_decide_oraculo([("quase", 7649, 9000)]) == [],
        "EDGE: 84% (one byte under the warning) does not light", "")
    got = _decide_oraculo([("gorda", 8600, 9000)])
    diz(len(got) == 1 and "GORDA" in got[0]["id"],
        "POSITIVE: a source at 95% of the ceiling LIGHTS", "(%d item)" % len(got))
    diz(_fontes_do_oraculo() is not None,
        "and the real reading answers — a blind door declares, it does not go mute", "")

    # CONTROL of MEMORY — triaged and decided is not an orphan; a new one keeps accusing
    diz(porta_memoria(["feedback_ask_the_code_first"]) == [],
        "TRIAGED: a memory cited in a channel does not come back as an orphan", "")
    #   The POSITIVE control is the OLD orphan ("a NEW memory lights" was the old law, and exactly
    # the defect the floor fixes). A fixture on both ends (birth and today) so it does not depend on
    # the calendar.
    _fix, _hoje = "memoria_que_nao_existe_xyz", datetime.date(2026, 9, 9)
    _po = porta_memoria([_fix], nascimento={_fix: "2026-01-01"}, hoje=_hoje)
    diz(len(_po) == 1, "POSITIVE: an OLD orphan outside the channels LIGHTS", "(%d item)" % len(_po))
    diz(porta_memoria([_fix], nascimento={_fix: "2026-09-05"}, hoje=_hoje) == [],
        "NEGATIVE: a 4-day orphan is NEWBORN and does not light (floor %dd)" % IDADE_MIN_DIAS, "")
    diz(porta_memoria([_fix], nascimento={"outra": "2026-01-01"}, hoje=_hoje) == [],
        "NEGATIVE: no commit yet = just born, does not light", "")
    diz(porta_memoria([_fix], nascimento={}, hoje=_hoje) != [],
        "BLIND: without git history the floor does not filter — fails towards ACCUSING", "")

    # CONTROL of the AGGREGATE — settlement is against the TARGET (proven failing: the settled
    # fixture returned 1 item and the warning said "-8 B above the TARGET")
    diz(_agregado([("f", 15000, 9000), ("g", 15300, 9000)], 36068, 30325, 0) == [],
        "SETTLED: aggregate at the target (30300 of 30325) does not become an item", "")
    _ag = _agregado([("f", 15000, 9000), ("g", 15400, 9000)], 36068, 30325, 0)
    diz(len(_ag) == 1 and _ag[0]["id"] == "PORTA-ORAC-AGREGADO",
        "POSITIVE: aggregate above the target (30400) LIGHTS", "(%d item)" % len(_ag))

    # CONTROL: the paid rows survive regeneration
    if FONTE.exists():
        antes = len(linhas_pagas())
        escreve(itens)
        diz(len(linhas_pagas()) == antes, "the ~~paid~~ rows survive regeneration",
            "(%d)" % antes)

    diz(_esc(r"(a|b)") == r"(a\|b)", "escapes the | of the alternation — otherwise the row is DISCARDED", "")
    _l = r"| **X** | `(a\|b)` | diz | passo | D1 | 7 |"
    diz(len(_celulas(_l)) == 8 and _celulas(_l)[6] == "7",
        "and the READING unescapes: rides comes from the number, not the text",
        "(%d fields, rides=%s)" % (len(_celulas(_l)), _celulas(_l)[6]))
    diz(all("|" not in _esc(i["casa"]).replace("\\|", "") for i in itens),
        "no raw pipe left in the generated regexes", "")

    #   EVERY WARNING THAT PUBLISHES BYTES DECLARES THE QUANTITY. This system has TWO similar measures
    # — extracted ruler (what the guard collects) and file bytes (what the historical series has) —
    # and they appear in the same context, side by side. Confusing them once produced an inverted
    # verdict and an invented deadline.
    com_byte = [i for i in itens if re.search(r"\d+ B\b", i["diz"])]
    sem_grandeza = [i["id"] for i in com_byte
                    if not re.search(r"extracted ruler|of file|FILE", i["diz"] + i["passo"])]
    diz(not sem_grandeza, "every warning with bytes declares the QUANTITY (ruler × file)",
        "(%d with bytes%s)" % (len(com_byte),
                               "" if not sem_grandeza else " · MUTE: " + ", ".join(sem_grandeza)))

    print("== %d ok · %d failure(s) ==" % (ok, ruim))
    return 0 if ruim == 0 else 1


if __name__ == "__main__":
    # ANTI-LOOP: post-commit calls this; a commit from here would fire the hook again.
    #   IT ONLY APPLIES TO THE AUTOMATIC CALL. The first version also locked `--seco` and
    # `--selftest`, and the symptom was cruel: right after the pipeline ran, HEAD starts with
    # `porta:` and the whole tool went mute with exit 0 — indistinguishable from "nothing to do".
    #   AN EARLY EXIT OF A DIAGNOSTIC TOOL MUST SAY WHY IT EXITED. Silence with exit 0 is the only
    # answer that cannot be told apart from "all is well".
    manual = any(a.startswith("--") for a in sys.argv[1:])
    if not manual:
        if os.environ.get("PORTA_EM_EXECUCAO"):
            print("porta: PORTA_EM_EXECUCAO is set — anti-loop, measured nothing", file=sys.stderr)
            sys.exit(0)
        if sh("git", "log", "-1", "--format=%s").startswith("porta:"):
            print("porta: HEAD is already my commit — anti-loop, measured nothing", file=sys.stderr)
            sys.exit(0)

    if "--selftest" in sys.argv:
        print("== porta --selftest ==")
        sys.exit(selftest())

    itens = monta()
    if "--seco" in sys.argv:
        for i in itens:
            print("  [%s] %s" % (i["degrau"], i["id"]))
            print("      %s" % i["diz"][:160])
        sys.exit(0)
    escreve(itens)
    print("porta: %d item(s) in %s" % (len(itens), FONTE))
