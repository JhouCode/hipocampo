#!/usr/bin/env python3
"""THE DISPATCHER -- warns, charges and blocks debts when a touch matches their trigger.

WHY THIS EXISTS
  An opportunistic backlog ("when you touch X, also do Y") only works if someone OPENS it at the
  right moment, and it is not in the agent's context when the touch happens. So it is not slow,
  it is MUTE. Measured on the original backlog: the files it named received dozens of commits
  while their items stayed open -- dozens of free rides with an opportunity, one item paid in
  two and a half months.

WHAT IT IS NOT
  It is not a backlog reminder. It is a generic CALL ORDER: the sources are data
  (`docs/gatilhos/*.md`), the engine does not know what they talk about, and a new front
  (dependencies, duplication) enters as a NEW FILE -- zero lines here. If a new front ever needs a
  line in the engine, the contract is wrong, and that is a finding.

THE THREE STEPS -- escalation replaces the pivot
  D1 WARN    `PostToolUse`  -> speaks at the touch, once per session
  D2 CHARGE  `Stop`         -> the turn closed without payment: increments `rides` on the row
  D3 BLOCK   `PreToolUse`   -> `rides >= 3`: the touch does not pass without the owner's decision

  Promotion belongs to the COUNTER, not to the agent. D1 failing PRODUCES D2; D2 failing PRODUCES
  D3. No step depends on the agent noticing that the previous one failed and changing plans.

  The three live on DIFFERENT EVENTS on purpose (see `docs/gatilhos/CANAIS.md`): an update that
  closes one channel takes down one step, not the ladder.

USAGE
  gatilho.py --evento post-tool   (stdin = hook JSON)   D1
  gatilho.py --evento stop        (stdin = hook JSON)   D2
  gatilho.py --evento pre-tool    (stdin = hook JSON)   D3
  gatilho.py --selftest           proves the predicates, negative controls included
  gatilho.py --historico <days>   how many rides it WOULD have lit in the git log (positive control)
"""
import json, os, re, sys, subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipo_config as HC  # noqa: E402

RAIZ = Path(HC.REPO)
FONTES = RAIZ / "docs" / "gatilhos"
CACHE = Path(os.environ.get("GATILHO_CACHE", str(Path(HC.STATE_DIR) / "gatilho")))
TETO_D3 = 3

# The GUARD surface: D3 does not block here. The owner's decision: guards may be updated by the
# agent without his approval. The debt KEEPS speaking through D1/D2 (PostToolUse/Stop) -- it only
# loses the `ask`. What stays his (deleting a guard, loosening one that blocks the agent's own
# commit) was never protected by this `ask`: the control for that is the commit body, not the prompt.
#   The paths are THIS repository's guard surfaces: the battery and the checker in `guards/`, their
# histories in `docs/guardas/`, the mutants in `fixtures/guards/`, and the guard scripts in `scripts/`.
_GUARDA = re.compile(r"\bguards/|docs/guardas/|scripts/provar-|scripts/guarda-|(^|/)fixtures/")

# The columns of the source contract, in order. New source = new file with these columns.
COLUNAS = ["id", "quando", "dizer", "proximo", "degrau", "caronas"]


# ---------------------------------------------------------------- reading the sources

def le_fontes(dir_fontes=None):
    """Reads every source and returns (items, problems).

    DECLARED POPULATION: returns ALL items, including those without `when it matches`. Filtering
    the uncovered ones here would hide the real coverage -- the caller counts `N of M` and prints
    both. `problems` carries what could not be read, because an unreadable source must shout,
    not vanish.
    """
    d = Path(dir_fontes) if dir_fontes else FONTES
    itens, problemas = [], []
    if not d.is_dir():
        problemas.append(f"source directory does not exist: {d}")
        return itens, problemas
    for md in sorted(d.glob("*.md")):
        if md.name in ("CANAIS.md", "README.md"):
            continue
        fonte = md.stem
        candidatas, dentro = 0, False
        for n, linha in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            # The item table is delimited by its HEADER, not by "starts with |". A source is also
            # a doc: it has prose tables, measurement tables, contract tables. Without this anchor
            # the column guard would have to be loosened -- and that guard is exactly what keeps
            # a malformed item from vanishing silently. Delimiting preserves both.
            if not linha.startswith("|"):
                dentro = False
                continue
            celulas = [c.strip() for c in parte_linha(linha)]
            if celulas[:2] == ["id", "when it matches"] and len(celulas) == len(COLUNAS):
                dentro = True
                continue
            if not dentro:
                continue
            if celulas[0] in ("id", "---") or set(celulas[0]) <= set("-: "):
                continue
            candidatas += 1
            # NEVER drop a row silently. A malformed row leaves the backlog without an alarm, and
            # the population shrinks together with the count -- the number stays coherent and
            # LIES. It happened at the debut: 8 of 30 items vanished and the selftest stayed green.
            if len(celulas) != len(COLUNAS):
                problemas.append(f"{fonte}:{n}: {len(celulas)} columns, expected {len(COLUNAS)}"
                                 f" -- item DISCARDED: {celulas[0][:40]}")
                continue
            it = dict(zip(COLUNAS, celulas))
            it["fonte"], it["linha_no"] = fonte, n
            it["pago"] = it["id"].startswith("~~")
            it["padrao"] = extrai_padrao(it["quando"])
            try:
                it["caronas_n"] = int(re.sub(r"\D", "", it["caronas"]) or 0)
            except ValueError:
                it["caronas_n"] = 0
            if it["padrao"] and not it["pago"]:
                try:
                    re.compile(it["padrao"])
                except re.error as e:
                    problemas.append(f"{fonte}#{it['id']}: invalid regex ({e})")
                    it["padrao"] = None
            itens.append(it)
        lidos = len([i for i in itens if i["fonte"] == fonte])
        if lidos != candidatas:
            problemas.append(f"{fonte}: {lidos} items read from {candidatas} table lines")
    return itens, problemas


def parte_linha(linha):
    """Splits a table row into columns, honouring the escaped `\\|` INSIDE the regexes.

    A regex such as `(git commit\\|push)` has a literal pipe; a naive split on `|` shatters it and
    the whole row becomes garbage. Markdown already requires the backslash there, so it rules.
    """
    return [c.replace("\\|", "|") for c in re.split(r"(?<!\\)\|", linha.strip().strip("|"))]


def extrai_padrao(celula):
    """The `when it matches` column holds the regex between backticks. `—` = uncovered, declared."""
    m = re.search(r"`([^`]+)`", celula)
    return m.group(1) if m else None


# ---------------------------------------------------------------- the match

def alvo_do_hook(d):
    """What was touched: the file path (Edit/Write) or the command text (Bash).

    Bash is in on purpose: many targets are REMOTE. Files that live on another host are touched
    over ssh -- a local Edit would never see them. Matching the command text catches
    `ssh buildhost vim .../router.py`. The false positive (`grep router.py`) is accepted and
    bounded by the once-per-session marker.
    """
    ti = d.get("tool_input") or {}
    return ti.get("file_path") or ti.get("command") or ""


# Signs that the command WRITES. Outside this list, Bash is treated as a read.
_ESCREVE = re.compile(
    r"(^|[;&|]\s*)(vim?|nano|emacs|tee|cp|mv|rm|mkdir|touch|chmod|chown|install|patch|dd)\b"
    # Redirection to a FILE. Excludes `2>&1` and `>/dev/null`: sending output to the bin is a pure
    # read, and an `ls ... 2>/dev/null` charged an undue ride in the second round exactly that way.
    r"|>>?\s*(?!&)(?!/dev/(null|stderr|stdout))[^\s;|&]"
    r"|\bsed\b[^|;]*-i"                   # sed in-place
    r"|\bgit\s+(commit|push|checkout|merge|rebase|apply|revert|reset)\b"
    r"|\bcat\s*<<"                        # heredoc writing a file
)


def e_escrita(d):
    """Was the touch a WRITE? Only a write counts as a missed ride.

    PILOT FINDING -- D2 charged three items on the first real turn and ALL THREE were wrong. One
    because the file had only been `grep`ped. **Reading is not an opportunity to pay**, and
    counting rides on reads inflates the counter until it promotes to D3 -- which then blocks work
    over a debt that never had a chance.
      The WARNING (D1) still applies to reads: knowing there is debt in the file being read is
    cheap and useful. It is the CHARGE that requires a write.
      Bash is a READ by default, on purpose: erring low lets one ride pass; erring high blocks the
    owner's work by mistake. The two errors do not cost the same.
    """
    nome = d.get("tool_name") or ""
    if nome in ("Edit", "Write", "NotebookEdit"):
        return True
    if nome == "Bash":
        return bool(_ESCREVE.search((d.get("tool_input") or {}).get("command") or ""))
    return False


def segmentos(cmd):
    """Splits the command into the pieces that run separately (`;` `&&` `||` `|` newline)."""
    return [s for s in re.split(r"[;\n]|&&|\|\||\|", cmd) if s.strip()]


def escrita_do_item(d, it):
    """Did THIS item match in a WRITE segment? -- the command having some write is not enough.

    THIRD PILOT FINDING. A compound command `cp ...crontab... && ls -l .../backup.sh` charged a
    ride on the backup item: the `cp` marked the whole command as a write and the MENTION of
    `backup.sh` in the `ls` matched the item. A write in one piece contaminated the read in
    another -- and a ride only counts when there was an opportunity to pay IN THAT file.
    """
    nome = d.get("tool_name") or ""
    if nome in ("Edit", "Write", "NotebookEdit"):
        return True
    if nome != "Bash" or not it.get("padrao"):
        return False
    cmd = (d.get("tool_input") or {}).get("command") or ""
    return any(re.search(it["padrao"], seg) and _ESCREVE.search(seg) for seg in segmentos(cmd))


def e_regra(it):
    """PERMANENT item (`step: RULE`) -- always warns, counts, but NEVER promotes to D3.

    SECOND PILOT FINDING, deeper than the first. The sources have two kinds of item and only one
    had been designed:
      DEBT (the `backlog`) -- dies when paid. Accumulated rides = debt coming due, and escalating
        to D3 is the right answer: at some point it has to hurt.
      RULE (`dependencia`, `duplicado`) -- does NOT die. "Check the projection before editing"
        holds every time, forever. Counting rides as debt would bring every rule to 3 and make it
        block everything, **even when the rule is always obeyed** -- because D2 only knows that it
        warned, there was a write and the turn closed; it does not know whether it was paid.
    For a rule, the counter is a METRIC: a high number says "this rule lives on my path, it is
    worth revising or automating", not "time to block".
    """
    return it.get("degrau", "").strip().upper() == "RULE"


def casa(itens, alvo):
    if not alvo:
        return []
    return [it for it in itens
            if it["padrao"] and not it["pago"] and re.search(it["padrao"], alvo)]


# ---------------------------------------------------------------- per-session state

def arquivo_sessao(d):
    sid = d.get("session_id") or "no-session"
    CACHE.mkdir(parents=True, exist_ok=True)
    return CACHE / f"{re.sub(r'[^A-Za-z0-9_-]', '', sid)}.json"


def le_sessao(p):
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def grava_sessao(p, estado):
    try:
        p.write_text(json.dumps(estado, indent=1))
    except Exception:
        pass


# ---------------------------------------------------------------- the ride counter

def incrementa_carona(it):
    """Adds 1 to the `rides` column of the row, in the source file itself.

    Surgical per row: rewrites only that item's cell. It is the number that promotes the step, so
    it lives in the data, visible in the git diff -- not in a counter hidden in a cache.
    """
    md = FONTES / f"{it['fonte']}.md"
    try:
        linhas = md.read_text(encoding="utf-8").splitlines()
    except Exception:
        return False
    i = it["linha_no"] - 1
    if i >= len(linhas) or not linhas[i].startswith("|"):
        return False
    celulas = parte_linha(linhas[i])
    if len(celulas) != len(COLUNAS) or celulas[0].strip() != it["id"]:
        return False          # the row moved under me: do not write into the wrong item
    celulas[-1] = f" {it['caronas_n'] + 1} "
    linhas[i] = "|" + "|".join(c.replace("|", "\\|") for c in celulas) + "|"
    md.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return True


# ---------------------------------------------------------------- the steps

def d1_avisa(d, itens):
    """PostToolUse -> additionalContext. Speaks once per item per session."""
    alvo = alvo_do_hook(d)
    achados = casa(itens, alvo)
    if not achados:
        return None
    p = arquivo_sessao(d)
    estado = le_sessao(p)
    # The write is judged PER ITEM, not for the whole command -- see `escrita_do_item`.
    # An item already warned on a READ is promoted to chargeable when the write arrives later. The
    # warning is not repeated (idempotence belongs to the warning), but the opportunity now counts.
    # A RULE seen on a READ speaks again when the WRITE arrives. Measured: a gate rule lit on an
    # investigation `grep` of a runbook and stayed MUTE twenty minutes later, when the sibling doc
    # was actually edited. The warning came on the read, when it did not matter, and was missing
    # on the write, when it gates the action. The gate was crossed.
    #
    # D1 idempotence is for the DEBT warning -- a warned debt becomes a ride, and repeating it is
    # noise. A RULE is different: the source contract says it "always warns" (`e_regra`), and the
    # code diverged from the contract it publishes.
    #
    # And it is not "every time": that would be noise per call. It is ONE second time, on the event
    # where the situation changes from reading to WRITING -- the only new moment there is.
    reavisar = []
    for it in achados:
        st = estado.get(it["id"])
        if escrita_do_item(d, it) and isinstance(st, dict):
            if e_regra(it) and not st.get("escrita"):
                reavisar.append(it)
            st["escrita"] = True
    novos = [it for it in achados if estado.get(it["id"]) is None]
    if not novos and not reavisar:
        grava_sessao(p, estado)
        return None
    for it in novos:
        estado[it["id"]] = {"estado": "avisado", "fonte": it["fonte"],
                            "alvo": alvo[:200], "escrita": escrita_do_item(d, it)}
    grava_sessao(p, estado)

    partes = []
    for it in novos + reavisar:
        if e_regra(it):
            grau = "RULE"
            perdidas = f" · seen {it['caronas_n']}×" if it["caronas_n"] else ""
            if it in reavisar:
                perdidas += " · 🚨 NOW IT IS A WRITE -- before you had only READ"
        else:
            grau = "D3" if it["caronas_n"] >= TETO_D3 else ("D2" if it["caronas_n"] >= 1 else "D1")
            perdidas = f" · {it['caronas_n']} missed ride(s)" if it["caronas_n"] else ""
        partes.append(f"⚠️ [{it['fonte']} #{it['id']} · {grau}{perdidas}] {it['dizer']}\n"
                      f"   NEXT STEP: {it['proximo']}")
    return "\n".join(partes)


def d2_cobra(d, itens):
    """Stop -> the turn closed. Every warned, still unpaid item gets +1 missed ride.

    The runtime schema guarantees the conversation CONTINUES after this event, so this is a charge
    with a chance to pay in the same turn -- not a farewell note.
    """
    p = arquivo_sessao(d)
    estado = le_sessao(p)
    # Only what was WRITTEN is charged. An item warned on a read is marked as seen and leaves the
    # scene without counting a ride -- see `e_escrita`, and the turn where the first 3 were false.
    lidos = [k for k, v in estado.items()
             if isinstance(v, dict) and v.get("estado") == "avisado" and not v.get("escrita")]
    for k in lidos:
        estado[k]["estado"] = "so-leitura"
    pendentes = [k for k, v in estado.items()
                 if isinstance(v, dict) and v.get("estado") == "avisado"]
    if not pendentes:
        grava_sessao(p, estado)
        return None
    por_id = {it["id"]: it for it in itens}
    cobrados = []
    for k in pendentes:
        it = por_id.get(k)
        if not it or it["pago"]:
            estado[k]["estado"] = "pago"
            continue
        if e_regra(it):
            # A RULE does not accumulate towards blocking -- see `e_regra`. The counter becomes a
            # metric: high there means "this rule lives on my path", not "debt overdue".
            estado[k]["estado"] = "regra"
            incrementa_carona(it)
            continue
        if incrementa_carona(it):
            estado[k]["estado"] = "cobrado"
            cobrados.append((it, it["caronas_n"] + 1))
    grava_sessao(p, estado)
    if not cobrados:
        return None
    linhas = []
    for it, n in cobrados:
        aviso = "  -> reaches D3 (BLOCK) on the next touch." if n >= TETO_D3 else ""
        linhas.append(f"↩︎ [{it['fonte']} #{it['id']}] missed ride #{n}: {it['dizer']}{aviso}")
    return ("The turn closed with open debt in the code that was touched:\n" + "\n".join(linhas) +
            "\nPaying now costs less than the next ride.")


def d3_barra(d, itens):
    """PreToolUse -> permissionDecision:ask when the item has already missed TETO_D3 rides."""
    alvo = alvo_do_hook(d)
    if _GUARDA.search(alvo):
        return None
    # Only a WRITE on the item's file blocks -- the same criterion that counts the ride
    # (`escrita_do_item`). Without this, a `grep`/`sed -n` on a file asked for `ask` over an
    # overdue debt, and reading was never an opportunity to pay. The read stays WARNED by D1.
    duros = [it for it in casa(itens, alvo)
             if it["caronas_n"] >= TETO_D3 and not e_regra(it) and escrita_do_item(d, it)]
    if not duros:
        return None
    it = max(duros, key=lambda x: x["caronas_n"])
    return (f"[{it['fonte']} #{it['id']}] has already missed {it['caronas_n']} rides on this path.\n"
            f"{it['dizer']}\nNEXT STEP: {it['proximo']}\n"
            f"Pay it together with this edit, or say why it stays open one more time?")


# ---------------------------------------------------------------- output to the hook

def responde(evento, texto):
    """Each step speaks through the channel the runtime accepts for ITS event (docs/gatilhos/CANAIS.md)."""
    if not texto:
        sys.exit(0)
    if evento == "pre-tool":
        out = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                      "permissionDecision": "ask",
                                      "permissionDecisionReason": texto}}
    elif evento == "stop":
        out = {"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": texto}}
    else:
        out = {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": texto}}
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0)


# ---------------------------------------------------------------- historical positive control

def historico(dias, repo=None):
    """How many rides the dispatcher WOULD have lit -- the positive control of the past.

    THE UNIT IS THE COMMIT, not the touched file. A ride is an OPPORTUNITY to pay, and a commit
    that touches 5 templates is one opportunity, not five. Counting file-touches inflates: in the
    pilot it gave 43 where the answer was 31.

    And "0 rides" has TWO meanings that this report keeps apart: the item was measured and did not
    show up, or its code DOES NOT LIVE in this repo. Adding both into a single zero would be
    saying "I did not look" with the face of "I looked and there is none".
    """
    r = Path(repo) if repo else RAIZ
    itens, problemas = le_fontes()
    ativos = [it for it in itens if it["padrao"] and not it["pago"]]

    def git(*a):
        return subprocess.run(["git", "-C", str(r), *a],
                              capture_output=True, text=True, timeout=180).stdout

    try:
        rastreados = [l for l in git("ls-files").splitlines() if l]
        out = git("log", f"--since={dias} days ago", "--name-only", "--pretty=format:%H")
    except Exception as e:
        print(f"could not read the repo {r}: {e}")
        return 1
    if not rastreados:
        print(f"BLIND: {r} returned no tracked file at all")
        return 1

    # Groups by commit: the dict key is the hash, and each item counts ONCE per commit.
    commits, atual = {}, None
    for l in out.splitlines():
        l = l.strip()
        if re.fullmatch(r"[0-9a-f]{40}", l):
            atual, commits[atual] = l, set()
        elif l and atual:
            commits[atual].add(l)
    if not commits:
        print(f"BLIND: git log of {dias} days in {r} returned no commit at all")
        return 1

    contagem = {}
    for arquivos in commits.values():
        acesos = {it["id"] for arq in arquivos for it in casa(ativos, arq)}
        for i in acesos:
            contagem[i] = contagem.get(i, 0) + 1

    # An item whose pattern matches NO tracked file points outside this repo.
    def mora_aqui(it):
        return any(re.search(it["padrao"], a) for a in rastreados)

    medidos = [it for it in ativos if mora_aqui(it)]
    fora = [it for it in ativos if not mora_aqui(it)]

    print(f"== {dias} days · repo {r} · {len(commits)} commits · {len(rastreados)} files ==")
    for it in sorted(medidos, key=lambda x: -contagem.get(x["id"], 0)):
        n = contagem.get(it["id"], 0)
        print(f"  {n:4d}  [{it['fonte']} #{it['id']}] {it['dizer'][:66]}")
    total = sum(contagem.get(it["id"], 0) for it in medidos)
    zerados = len([it for it in medidos if not contagem.get(it["id"])])
    print(f"-- MEASURED: {total} rides over {len(medidos)} items ({zerados} with a real zero) --")
    if fora:
        print(f"-- NOT MEASURED: {len(fora)} items whose code does not live in this repo "
              f"(point --repo at the one where it does) --")
        for it in fora:
            print(f"        [{it['fonte']} #{it['id']}] `{it['padrao']}`")
    for p in problemas:
        print(f"  ⚠️ {p}")
    return 0


# ---------------------------------------------------------------- guards

def selftest():
    ok = ruim = 0
    def checa(nome, cond):
        nonlocal ok, ruim
        print(f"  {'✓' if cond else '✗'} {nome}")
        ok, ruim = (ok + 1, ruim) if cond else (ok, ruim + 1)

    itens, problemas = le_fontes()
    ativos = [it for it in itens if not it["pago"]]
    com_padrao = [it for it in ativos if it["padrao"]]

    # -- the engine, against a synthetic control source ----------------------------------------
    falso = [
        {"id": "T1", "fonte": "test", "linha_no": 1, "pago": False, "caronas_n": 0,
         "dizer": "d", "proximo": "p", "padrao": r"templates/.*\.html$"},
        {"id": "T2", "fonte": "test", "linha_no": 2, "pago": False, "caronas_n": 5,
         "dizer": "d", "proximo": "p", "padrao": r"router\.py"},
        {"id": "T3", "fonte": "test", "linha_no": 3, "pago": True, "caronas_n": 0,
         "dizer": "d", "proximo": "p", "padrao": r"app\.py"},
    ]
    checa("positive · template path matches", len(casa(falso, "site/templates/base.html")) == 1)
    checa("positive · remote ssh command matches by its text",
          len(casa(falso, "ssh buildhost vim ~/src/service-a/src/app/routing/router.py")) == 1)
    # NEGATIVE CONTROL: without it a too-wide pattern "finds" anywhere.
    checa("negative · file without debt does NOT match", casa(falso, "docs/CHANGES.md") == [])
    checa("negative · command without a file name does NOT match", casa(falso, "ls -la") == [])
    checa("negative · empty target does NOT match", casa(falso, "") == [])
    # a paid item must leave circulation, otherwise the backlog never shrinks.
    checa("negative · PAID item does not match even on its own path", casa(falso, "site/app.py") == [])
    checa("step · item with rides>=3 enters D3", len([it for it in casa(falso, "router.py")
                                                       if it["caronas_n"] >= TETO_D3]) == 1)
    checa("step · new item does NOT enter D3", len([it for it in casa(falso, "templates/x.html")
                                                    if it["caronas_n"] >= TETO_D3]) == 0)

    # -- reading is NOT an opportunity to pay ---------------------------------------------------
    checa("write · Edit counts", e_escrita({"tool_name": "Edit", "tool_input": {"file_path": "a"}}))
    checa("write · Write counts", e_escrita({"tool_name": "Write", "tool_input": {"file_path": "a"}}))
    for cmd in ("sed -i s/a/b/ router.py", "vim router.py", "echo x > router.py",
                "git commit -m x", "cp a b", "ssh build 'cat > f.cpp'"):
        checa(f"write · command `{cmd[:28]}` counts", e_escrita({"tool_name": "Bash",
                                                               "tool_input": {"command": cmd}}))
    # NEGATIVE CONTROL -- what motivated the fix: a grep charged a real ride.
    for cmd in ("grep -n return router.py", "cat router.py", "git log --oneline",
                "git status --porcelain", "ls -la src/", "wc -l router.py 2>&1"):
        checa(f"read · command `{cmd[:28]}` does NOT count",
              not e_escrita({"tool_name": "Bash", "tool_input": {"command": cmd}}))
    checa("read · Read never counts", not e_escrita({"tool_name": "Read",
                                                     "tool_input": {"file_path": "a"}}))
    # Redirection to the BIN is a read. An `ls ... 2>/dev/null` charged an undue ride in round 2.
    for cmd in ("ls -l f 2>/dev/null", "grep x f >/dev/null", "diff a b &>/dev/null"):
        checa(f"read · redirection to the bin `{cmd[-12:]}` does NOT count",
              not e_escrita({"tool_name": "Bash", "tool_input": {"command": cmd}}))
    checa("write · redirection to a FILE counts",
          e_escrita({"tool_name": "Bash", "tool_input": {"command": "echo hi > f.cpp"}}))

    # -- write PER ITEM: a compound command does not contaminate ---------------------------------
    it_bk = {"id": "T_BK", "padrao": r"(backup\|push-offsite)\.sh".replace("\\|", "|"), "pago": False}
    it_rb = {"id": "T_RB", "padrao": r"rebuild-from-scratch\.sh", "pago": False}
    for cmd, it, esperado, porque in [
        ("cp x/*.cron y/ && ls -l z/backup.sh", it_bk, False, "cp writes SOMETHING ELSE; the item was only listed"),
        ("cp a.sh /srv/app/scripts/backup.sh", it_bk, True, "cp writing INTO the item's file"),
        ("grep x rebuild-from-scratch.sh | tee /tmp/o", it_rb, False, "tee writes /tmp/o; the item was only read"),
        ("sed -i s/a/b/ rebuild-from-scratch.sh", it_rb, True, "sed -i on the file itself"),
        ("ls backup.sh; echo hi > f", it_bk, False, "write in a segment WITHOUT the item"),
    ]:
        checa(f"per-item · {'counts' if esperado else 'does NOT count'}: {porque}",
              escrita_do_item({"tool_name": "Bash", "tool_input": {"command": cmd}}, it) == esperado)

    # -- RULE: a permanent item always warns and NEVER blocks ------------------------------------
    regra = [{"id": "R1", "fonte": "t", "linha_no": 1, "pago": False, "caronas_n": 9,
              "dizer": "d", "proximo": "p", "degrau": "RULE", "padrao": r"x\.py"}]
    divida = [dict(regra[0], id="R2", degrau="D1")]
    checa("RULE with 9 rides does NOT enter D3",
          d3_barra({"tool_name": "Edit", "tool_input": {"file_path": "x.py"}}, regra) is None)
    checa("DEBT with 9 rides enters D3",
          d3_barra({"tool_name": "Edit", "tool_input": {"file_path": "x.py"}}, divida) is not None)
    checa("overdue DEBT on a READ does not block (grep on the item's file)",
          d3_barra({"tool_name": "Bash", "tool_input": {"command": "grep -n x x.py"}}, divida) is None)
    checa("control: a Bash write on the item's file blocks",
          d3_barra({"tool_name": "Bash", "tool_input": {"command": "sed -i s/a/b/ x.py"}}, divida) is not None)
    nucleo = [dict(divida[0], id="R3", padrao=r"(3_DECIDIDO|memory-guards)")]
    checa("DEBT on a GUARD surface does NOT block (the owner's decision)",
          d3_barra({"tool_name": "Bash", "tool_input": {"command": "sed -i s/a/b/ guards/memory-guards.sh"}}, nucleo) is None)
    checa("control: the same debt outside the guard still blocks",
          d3_barra({"tool_name": "Edit", "tool_input": {"file_path": "docs/mapa/3_DECIDIDO.md"}}, nucleo) is not None)

    # -- idempotence: the 2nd touch in the same session stays quiet -----------------------------
    import tempfile
    global CACHE
    guarda_cache = CACHE
    CACHE = Path(tempfile.mkdtemp())
    hook = {"session_id": "selftest", "tool_input": {"file_path": "site/templates/base.html"}}
    primeiro = d1_avisa(hook, falso)
    segundo = d1_avisa(hook, falso)
    checa("idempotence · 1st touch speaks", bool(primeiro))
    checa("idempotence · 2nd touch in the same session is QUIET", segundo is None)
    outra = {"session_id": "selftest-2", "tool_input": {"file_path": "site/templates/base.html"}}
    checa("idempotence · another session speaks again", bool(d1_avisa(outra, falso)))

    # -- a RULE seen on a READ warns again when the WRITE arrives (the gate case) ----------------
    #    The positive is the fix; the two negatives prove it did not turn into per-call noise.
    gate = [{"id": "K1", "fonte": "test", "linha_no": 1, "pago": False, "caronas_n": 0,
             "dizer": "gate", "proximo": "note and move on", "degrau": "RULE",
             "padrao": r"(RUNBOOK|RECOVERY)"}]
    gate_divida = [dict(gate[0], id="K2", degrau="D1")]
    ler = lambda sid: {"session_id": sid, "tool_name": "Bash",
                       "tool_input": {"command": "grep -n restore docs/RUNBOOK.md"}}
    escrever = lambda sid: {"session_id": sid, "tool_name": "Edit",
                            "tool_input": {"file_path": "docs/RECOVERY.md"}}
    d1_avisa(ler("gate-1"), gate)
    checa("RULE · read then WRITE warns again", bool(d1_avisa(escrever("gate-1"), gate)))
    d1_avisa(ler("gate-2"), gate_divida)
    checa("DEBT · read then write stays QUIET", d1_avisa(escrever("gate-2"), gate_divida) is None)
    d1_avisa(escrever("gate-3"), gate)
    checa("RULE · write then write is QUIET (no per-call noise)",
          d1_avisa(escrever("gate-3"), gate) is None)
    CACHE = guarda_cache

    # -- INJECTED DEFECT: the parse guard has to LIGHT UP ---------------------------------------
    # Without this the selftest is decoration: it stayed green at the debut while 8 of 30 items
    # vanished. A guard only counts after failing on purpose, so the defect lives in here.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        Path(td, "fake.md").write_text(
            "| id | when it matches | what to say | NEXT STEP | step | rides |\n"
            "|---|---|---|---|---|---|\n"
            "| X1 | `ok\\.py` | good | step | D1 | 0 |\n"
            "| X2 | `a|b` | RAW pipe breaks the row | step | D1 | 0 |\n", encoding="utf-8")
        it_f, pr_f = le_fontes(td)
        checa("injected defect · malformed row is REPORTED, not dropped silently",
              len(it_f) == 1 and any("DISCARDED" in p for p in pr_f))
        checa("injected defect · the read-vs-candidate count also shouts",
              any("table lines" in p for p in pr_f))
    with tempfile.TemporaryDirectory() as td:
        # A source is also a doc: it has contract, measurement and prose tables. None of them may
        # become an item -- and the item table that comes after must still be read normally.
        Path(td, "fake.md").write_text(
            "| column | what it is |\n|---|---|\n| prose | documentation table |\n\n"
            "| id | when it matches | what to say | NEXT STEP | step | rides |\n"
            "|---|---|---|---|---|---|\n"
            "| Z1 | `ok\\.py` | good | step | D1 | 0 |\n", encoding="utf-8")
        it_p, pr_p = le_fontes(td)
        checa("PROSE table is ignored without becoming a problem",
              [i["id"] for i in it_p] == ["Z1"] and not pr_p)
    with tempfile.TemporaryDirectory() as td:
        Path(td, "fake.md").write_text(
            "| id | when it matches | what to say | NEXT STEP | step | rides |\n"
            "|---|---|---|---|---|---|\n"
            "| Y1 | `[unclosed` | invalid regex | step | D1 | 0 |\n", encoding="utf-8")
        _, pr_r = le_fontes(td)
        checa("injected defect · invalid regex is reported", any("invalid regex" in p for p in pr_r))
    with tempfile.TemporaryDirectory() as td:
        checa("absence control · a directory without sources does not return a silent 0",
              le_fontes(Path(td) / "does-not-exist")[1] != [])

    # -- the real sources -----------------------------------------------------------------------
    checa("sources readable (no parse problem)", not problemas)
    for p in problemas:
        print(f"      ⚠️ {p}")
    checa("at least one source has items", len(itens) > 0)

    # -- the source CONTRACT: a new item is not born without classification nor without a way out
    sem_saida = [it for it in ativos if len(it["proximo"]) < 10 or it["proximo"] in ("—", "-")]
    checa("every row has a non-empty NEXT STEP", not sem_saida)
    for it in sem_saida:
        print(f"      ✗ {it['fonte']}#{it['id']}: NEXT STEP empty -- it is what keeps the warning"
              f" from pulling the agent out of the plan of action")
    # `when it matches` only accepts a regex between backticks OR the DECLARED dash. A prose cell
    # ("when touching the site") matches nothing and would pass as covered.
    mal_classificados = [it for it in ativos if not it["padrao"] and it["quando"] not in ("—", "-")]
    checa("every row has `when it matches` as a regex OR a declared `—`", not mal_classificados)
    for it in mal_classificados:
        print(f"      ✗ {it['fonte']}#{it['id']}: `when it matches` = {it['quando'][:40]!r}"
              f" -- neither regex nor dash")
    ids = [it["id"] for it in itens]
    checa("ids are unique", len(ids) == len(set(ids)))
    # DECLARED POPULATION: coverage is `N of M`, and M includes the ones uncovered on purpose.
    print(f"  ·· population: {len(com_padrao)} of {len(ativos)} active items have `when it matches`"
          f" ({len(itens) - len(ativos)} paid)")
    por_fonte = {}
    for it in ativos:
        por_fonte.setdefault(it["fonte"], []).append(it)
    for fonte, lista in sorted(por_fonte.items()):
        cob = len([it for it in lista if it["padrao"]])
        marca = "🟡 BLIND SOURCE" if len(lista) < 5 else ""
        print(f"  ·· {fonte}: {cob} of {len(lista)} covered {marca}")
        # A source too small is not a source -- it is a note. Yellow, not red: a pilot starts small.

    print(f"== {ok} ok · {ruim} failure(s) ==")
    return 1 if ruim else 0


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        sys.exit(selftest())
    if "--historico" in args:
        i = args.index("--historico")
        sys.exit(historico(int(args[i + 1]) if len(args) > i + 1 else 60, args[args.index("--repo") + 1] if "--repo" in args else None))
    evento = "post-tool"
    if "--evento" in args:
        evento = args[args.index("--evento") + 1]
    try:
        d = json.load(sys.stdin)
    except Exception:
        sys.exit(0)          # a broken stdin never takes down the user's touch
    itens, _ = le_fontes()
    if evento == "stop":
        responde(evento, d2_cobra(d, itens))
    elif evento == "pre-tool":
        responde(evento, d3_barra(d, itens))
    else:
        responde(evento, d1_avisa(d, itens))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # THE DISPATCHER NEVER GETS IN THE WAY OF THE WORK. It runs on PreToolUse, on the path of
        # every edit, and several agent sessions may run at once -- a defect here would become
        # friction in a conversation that is not this one. Failing silently is the only acceptable
        # posture: the worst case becomes "the warning did not come", never "the touch did not pass".
        try:
            CACHE.mkdir(parents=True, exist_ok=True)
            (CACHE / "erros.log").open("a").write(f"{type(e).__name__}: {e}\n")
        except Exception:
            pass
        sys.exit(0)
