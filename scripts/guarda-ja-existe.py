#!/usr/bin/env python3
"""THE WRITE GUARD -- "does this already exist?" enters the PATH of a Write to memory or rule doc.

WHY THIS EXISTS
  A rule was saved into a memory as a "new nuance" while it ALREADY EXISTED in three places -- a
  law of the map, the How-to-apply of the very memory being edited, and another memory. **Nothing
  warned.** The owner's words: *"you wrote something that was already somewhere else and nothing
  told you"*.
    The cost is not extra text: it is two truths diverging on their own, now inside the memory
  itself. And the hole is an INSTRUMENT hole -- the source `docs/gatilhos/duplicado.md` only
  matches on COMMANDS (a regex over the target of the touch); written content went through no
  question at all. The rule "check before saving" exists in the memory instructions, and a rule
  that is loaded is not a rule that is on the path.

WHAT IT IS -- AND WHAT IT IS NOT
  A WARNING, NEVER A BLOCK. It runs on `PostToolUse` (the only channel that speaks without
  interrupting -- see `docs/gatilhos/CANAIS.md §1`), lights up listing WHERE the thing already
  exists, and lets it pass. Blocking would produce false reds, and a false red becomes
  `--no-verify` by habit.
    It does NOT understand the sentence. A guard that needs to ASSOCIATE does not converge; a guard
  that checks overlap in one fixed place does. Here it is LEXICAL overlap of discriminating terms
  against THREE fixed surfaces. The verdict is the agent's; the guard supplies the candidate line.

THE PREDICATE, in four cheap steps
  1. Fixed surfaces, sliced into BLOCKS (the index per entry, the law table per row, prose per
     paragraph) -- the block is what the warning quotes.
  2. Terms come out of the new text: no accents, lower case, >=3 chars, outside the stopwords.
  3. A DISCRIMINATING term is one that appears in FEW blocks of the surface. The frequency cut
     alone kills what no stopword list would ever cover (the project's own everyday words): a
     term that matches everywhere points nowhere.
  4. A block with >=MIN_TERMOS DISTINCT discriminating terms is a candidate. Without that, one
     rare term shared by chance would light up on its own.

THE OBSERVER DOES NOT ENTER THE POPULATION -- three exclusions, each one already produced an error
  · The surface that IS the file being written leaves the search. Otherwise the guard matches its
    own prose and lights up 100% of the time, lying green.
  · The index block that cites the NAME (or the `[N]` id) of the target file leaves: that is its
    own pointer, not a duplicate. It is what the index exists to do.
  · Fenced code and backtick spans leave the new text before tokenizing -- a predicate has to
    filter comments before asking.
  And this script is never a surface: the three are fixed and none is `scripts/`. It contains the
  terms it looks for and, by construction, cannot accuse itself.

USAGE
  guarda-ja-existe.py --evento post-tool   (stdin = hook JSON)   the warning
  guarda-ja-existe.py --selftest           the two controls + the population
  guarda-ja-existe.py --varrer             runs the predicate over the store: N of M would light
  guarda-ja-existe.py --medir <file>       what THIS text would match today
"""
import functools, json, os, re, sys, unicodedata
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipo_config as HC  # noqa: E402

RAIZ = Path(HC.REPO)
MEMDIR = Path(os.environ.get("GJE_MEMDIR", HC.MEMORY_DIR))
# Per-session state lives in the hooks' state dir (hipo_config: HIPO_STATE_DIR), not in $HOME.
CACHE = Path(os.environ.get("GJE_CACHE", os.path.join(HC.STATE_DIR, "guarda-ja-existe")))

# The THREE surfaces where the rule may already live -- fixed on purpose (one single place
# converges). A new surface here is a decision, not a convenience: each one that enters widens the
# population and loosens the frequency cut for all the others.
def superficies():
    return [("MEMORY.md",   MEMDIR / "MEMORY.md"),
            ("mapa/1_CONTRATO.md", RAIZ / "docs/mapa/1_CONTRATO.md"),
            ("mapa/3_DECIDIDO.md", RAIZ / "docs/mapa/3_DECIDIDO.md")]

# Where the guard fires. Outside of here it is MUTE -- writing code, phase docs and scratch does
# not go through this question, and should not: the question is about RULES, which is what
# duplicates expensively.
ALVOS = re.compile(r"(\.claude/projects/[^/]+/memory/(?!MEMORY\.md)[^/]+\.md$"
                   r"|/docs/mapa/[^/]+\.md$"
                   r"|/docs/oraculo/[^/]+\.md$)")

MIN_TERMOS = 4          # distinct discriminating terms in common to become a candidate
TETO_FREQ = 0.06        # a term present in more than 6% of the blocks is common: it does not discriminate
#   OVERLAP COEFFICIENT: |matched| / min(|paragraph terms|, |block terms|).
# Normalizing by the BLOCK (the first attempt) penalizes long blocks: a long law scored 0.23 while
# being the exact duplicate of what had been written. Normalizing by the SMALLER of the two sides
# asks the right thing -- "is the smaller one contained in the other?" -- and treats the long law
# of the map and the one-line index entry alike.
MIN_SOBREPOSICAO = 0.60
MIN_TERMOS_PAR = 8      # a paragraph smaller than this does not state a rule: it is not compared
MAX_ACHADOS = 4         # the warning quotes the best ones; a long list is not read

# Portuguese and English stopwords (the corpus may be in either). Tokens are compared after
# `normaliza`, so only the unaccented forms can ever match.
STOP = set("""
nao sim ele ela eles elas que com por uma uns umas dos das nas nos aos seu sua tao mas ate ser sao
foi era tem vai vem dar deu dia dois tres mil ver vez ora pra pro num numa isso este essa tal ali
aqui bem mal fez faz ficam entra sair saiu vao vou pode podem deve devem quer querem sabe sabem
para pela pelo pelos pelas como quando onde porque porem mais menos muito pouco todo toda
todos todas cada outro outra outros outras mesmo mesma sobre entre desde ate apos ante
sem com sob contra segundo conforme isso isto aquilo esse essa este esta aquele aquela seja sejam
ser sao era eram foi foram sera tem tinha tinham teve tiveram haver havia ter estar
esta estao fica ficar ficou vale valer nao sim tambem ainda entao
agora depois antes assim aqui ali logo bem mal maior menor primeiro segundo terceiro
que qual quais quem cujo cuja dele dela deles delas meu minha seus suas nosso nossa
fazer faz feito feita dizer diz dito coisa coisas jeito modo forma vez vezes lugar caso casos
numero numeros dado dados linha linhas texto arquivo arquivos nome nomes tipo tipos
the and that this these those with from have has had was were are been being for not but you
your yours they them their there then than when where which while who whom whose what into onto
over under about after before again also only just more most much many some such very will would
could should shall must might can may does did done doing its our ours his her hers him she
all any both each few other others same own too off out upon because through during until
against between here how why yes nor one two three first second third new old way ways thing
things time times make makes made say says said line lines text file files name names type types
number numbers data case cases
""".split())


# ---------------------------------------------------------------- normalization and tokens

def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


#   MEMOIZED. `normaliza` and `tokens` are PURE functions (text -> text, text -> terms), and the
# sweep of the store called them ~350 thousand times over the SAME ~400 blocks (measured with
# cProfile: most of the run time). Keeping the result does not change a byte of the output;
# `tokens` returns a COPY, so that no caller mutates what is in the cache.
@functools.lru_cache(maxsize=None)
def normaliza(s):
    """Lower case and no accents -- an index mixes accented and unaccented spellings.

    Without this half of the store does not match the other half because of accents, and the guard
    goes green by a comparison defect, not by the absence of a duplicate.
    """
    return sem_acento(s).lower()


# THE SECOND BRANCH EXISTS BECAUSE THE MOST DISCRIMINATING TERMS ARE SHORT. The first version
# required 4+ characters and lost ids like `p9`, `r12`, `v2`, `db1` -- precisely the law and release
# identifiers, which point at ONE block and no other. The original case failed to match the tester
# memory because of this: its short id never became a token.
_PALAVRA = re.compile(r"[a-z][a-z0-9_]{2,}|[a-z]{1,2}\d+")


def tokens(txt):
    return set(_tokens(txt))


@functools.lru_cache(maxsize=None)
def _tokens(txt):
    """The terms of the text. An identifier with `_` ALSO yields its parts.

    The memory index is made of FILE NAMES (`feedback_tester_is_user0.md`), and memory bodies talk
    in prose (*"the test runs as user0"*). Without splitting the identifier, the two halves of the
    store do not see each other: the whole name is a single token nothing else matches.
    """
    out = set()
    for t in _PALAVRA.findall(normaliza(txt)):
        if t.isdigit() or t in STOP:
            continue
        out.add(t)
        if "_" in t:
            out.update(p for p in t.split("_") if len(p) >= 3 and p not in STOP)
    return frozenset(out)


def limpa_texto_novo(txt):
    """Removes frontmatter, fenced blocks and backtick spans BEFORE tokenizing.

    The memory that EXPLAINS a regex cites the regex; the one that documents a command cites the
    command. Matching inside them is the guard eating its own prose.
    """
    txt = re.sub(r"\A---\n.*?\n---\n", "", txt, flags=re.S)
    txt = re.sub(r"```.*?```", " ", txt, flags=re.S)
    txt = re.sub(r"`[^`\n]*`", " ", txt)
    # CITING IS NOT DUPLICATING -- and this was the dominant false positive. Measured on a sample of
    # the lit ones: most matched because the memory LINKS another (`[[name]]`) and the file name
    # also lives in the index, so the link's terms matched the whole index entry. The memory
    # system TELLS you to link liberally; punishing the pointer would be the guard fighting the
    # rule it should defend. Bare `name.md` go too, for the same reason, and of a markdown link
    # only the TEXT matters.
    txt = re.sub(r"\[\[[^\]]*\]\]", " ", txt)
    txt = re.sub(r"\]\([^)]*\)", "] ", txt)
    return re.sub(r"\b[a-z0-9_][a-z0-9_-]*\.md\b", " ", txt)


# ---------------------------------------------------------------- the surface blocks

def blocos_de(rotulo, path):
    """Slices the surface in the unit it uses itself -- the block is what the warning quotes.

    THE GRANULARITY IS THE INSTRUMENT. The index groups several entries on one line separated by
    ` · `: treating the whole line as a unit would add up terms of unrelated entries, and the score
    would say "matched a lot" about a block that does not exist. The law table is already one law
    per row. Prose becomes paragraphs, otherwise a 100-char line dilutes the terms and nothing
    reaches the minimum.
    """
    try:
        linhas = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    out, buf, ini = [], [], 0
    def fecha():
        if buf and " ".join(buf).strip():
            out.append((rotulo, ini, " ".join(buf).strip()))
        buf.clear()
    for n, linha in enumerate(linhas, 1):
        crua = linha.strip()
        if not crua or crua.startswith("#"):
            fecha()
            continue
        if crua.startswith("|"):                       # table: one row = one unit
            fecha()
            if not set(crua) <= set("|-: "):
                out.append((rotulo, n, crua))
            continue
        if " · " in crua:                              # index: one entry = one unit
            fecha()
            for pedaco in crua.split(" · "):
                if pedaco.strip():
                    out.append((rotulo, n, pedaco.strip()))
            continue
        if not buf:
            ini = n
        buf.append(crua)
    fecha()
    return out


_CACHE_BLOCOS = {}


def _chave_exclusao(excluir):
    """The cache key is the EXCLUDED surface, not the target.

    The key used to be the target path, and the sweep passes ~435 targets that are NOT surfaces --
    435 distinct keys for the SAME set of blocks, and the index rebuilt 438 times (cProfile: half
    of the run). A target that is not a surface excludes nothing: its key is "", as with no target.
    """
    if not excluir:
        return ""
    r = Path(excluir).resolve()
    for _rot, path in superficies():
        if path.resolve() == r:
            return str(r)
    return ""


def carrega(excluir=None):
    """Every block of the surfaces. `excluir` removes the surface that IS the file being written.

    MEMOIZED. On a real touch this runs once, but the sweep of the store calls `avalia` hundreds of
    times, and reading+slicing+indexing three files on each call made the selftest unaffordable
    inside the guard battery. An expensive guard is a guard someone turns off.
    """
    chave = _chave_exclusao(excluir)
    if chave not in _CACHE_BLOCOS:
        todos = []
        for rotulo, path in superficies():
            if excluir and path.resolve() == Path(excluir).resolve():
                continue
            todos.extend(blocos_de(rotulo, path))
        _CACHE_BLOCOS[chave] = todos
    return _CACHE_BLOCOS[chave]


_CACHE_INDICE = {}
_CACHE_DISC = {}


def indice(blocos, chave):
    if chave not in _CACHE_INDICE:
        _CACHE_INDICE[chave] = indexa(blocos)
    return _CACHE_INDICE[chave]


# ---------------------------------------------------------------- the match

def indexa(blocos):
    """term -> how many blocks contain it. The frequency cut comes from here."""
    freq = {}
    toks = []
    for b in blocos:
        t = tokens(b[2])
        toks.append(t)
        for x in t:
            freq[x] = freq.get(x, 0) + 1
    return freq, toks


def paragrafos(texto):
    """Slices the NEW TEXT in the same unit as the surfaces -- the paragraph.

    THIS IS THE FIX THE MEASUREMENT FORCED. The first version compared the WHOLE FILE against each
    block: the sweep of the store gave **98.7% of the memories lighting up**, with both direct
    controls green. A guard that lights on almost everything distinguishes nothing -- and the
    defect was the unit, not the cut. An 80-line file joins many subjects; three of its terms
    coinciding with a block is expected, not a signal. Paragraph against block puts both units at
    the same size, and then the overlap means something again.
    """
    return [p for p in re.split(r"\n\s*\n", limpa_texto_novo(texto)) if p.strip()]


def avalia(texto_novo, alvo=None, min_termos=MIN_TERMOS, teto=TETO_FREQ,
           sobreposicao=MIN_SOBREPOSICAO):
    """Returns (findings, discriminants). Finding = (label, line, excerpt, matched terms).

    Two conditions, and both are necessary:
      · N ABSOLUTE TERMS in common -- one rare term shared by chance does not light on its own.
      · COVERAGE of the existing block -- the matched terms have to be a FRACTION of it. Without
        this a long paragraph covers any block by volume, and the number goes up with no signal.

    A term that appears in NO block is not discriminating -- it is new. It is exactly what the new
    writing should be bringing, and it has nothing to match. Counting it as a signal would be
    counting absence as presence.
    """
    blocos = carrega(excluir=alvo)
    if not blocos:
        return [], set()
    chave = _chave_exclusao(alvo)
    freq, toks = indice(blocos, chave)
    limite = max(1, int(len(blocos) * teto))
    disc_de = lambda t: {x for x in t if 0 < freq.get(x, 0) <= limite}

    # The index block that cites the NAME of the target file is ITS OWN pointer, not a duplicate.
    nome_alvo = Path(alvo).stem if alvo else None
    #   AND WHEN THE INDEX CITES BY `[N]`, NOT BY NAME, the exclusion above goes BLIND: every memory
    # written afterwards lit against ITS OWN index line (measured: the population rose from 15% to
    # 25% with no duplicated rule at all). The own pointer is also recognized by the TOP-LEVEL id
    # of the frontmatter (the one `memoria_ids` reads), besides the name.
    id_alvo = None
    if alvo and Path(alvo).is_file():
        try:
            _cab = Path(alvo).read_text(encoding="utf-8", errors="replace")[:2000]
            _m = re.search(r"^id:\s*(\d+)\s*$", _cab, re.M)
            id_alvo = _m.group(1) if _m else None
        except OSError:
            id_alvo = None
    _re_id = re.compile(r"\[%s\]" % id_alvo) if id_alvo else None

    def ponteiro_proprio(b):
        if nome_alvo and nome_alvo in normaliza(b[2]):
            return True
        return bool(_re_id and b[0] == "MEMORY.md" and _re_id.search(b[2]))

    # The discriminants of each block do not depend on the new text -- compute them once per
    # (surface, cut) and not once per paragraph. Without this the sweep of the store never ends.
    ck = (chave, teto)
    if ck not in _CACHE_DISC:
        _CACHE_DISC[ck] = [(b, disc_de(t)) for b, t in zip(blocos, toks)]
    preparados = [(b, db) for b, db in _CACHE_DISC[ck]
                  if db and not ponteiro_proprio(b)]

    disc_total, melhor = set(), {}
    for par in paragrafos(texto_novo):
        tp = tokens(par)
        if len(tp) < MIN_TERMOS_PAR:
            continue
        dp = disc_de(tp)
        disc_total |= dp
        for (rotulo, linha, trecho), db in preparados:
            casados = dp & db
            if len(casados) < min_termos:
                continue
            if len(casados) / min(len(dp), len(db)) < sobreposicao:
                continue
            chave = (rotulo, linha)
            if len(casados) > len(melhor.get(chave, (0, 0, 0, ()))[3] or ()):
                melhor[chave] = (rotulo, linha, trecho, sorted(casados))
    achados = sorted(melhor.values(), key=lambda a: -len(a[3]))
    return achados, disc_total


# ---------------------------------------------------------------- the warning

def formata(achados, disc, alvo):
    if not achados:
        return None
    linhas = [f"🔎 [already-exists] The new text in `{Path(alvo).name}` covers terms that ALREADY "
              f"LIVE on the rule surfaces -- {len(achados)} candidate block(s):"]
    for rotulo, n, trecho, casados in achados[:MAX_ACHADOS]:
        corte = trecho if len(trecho) <= 220 else trecho[:217] + "…"
        linhas.append(f"   · {rotulo}:{n} -- {corte}")
        linhas.append(f"     matched on: {', '.join(casados[:8])}")
    if len(achados) > MAX_ACHADOS:
        linhas.append(f"   · (+{len(achados) - MAX_ACHADOS} other block(s))")
    linhas.append("   NEXT STEP: open the blocks above BEFORE closing the write. What already "
                  "exists is not rewritten -- it is CITED. Save only the DELTA, with a pointer to "
                  "where the rest lives; an empty delta means what was missing was a READ, not a "
                  "write. This is a WARNING: nothing was blocked.")
    return "\n".join(linhas)


# ---------------------------------------------------------------- per-session state

def ja_disse(d, alvo, achados):
    """Silences the identical warning repeated in the same session -- a Write followed by Edits.

    The key is (file + blocks pointed at): if the set of blocks changes, the warning is another one
    and speaks again. It is not "once per file" -- it is "once per finding".
    """
    sid = re.sub(r"[^A-Za-z0-9_-]", "", d.get("session_id") or "no-session")
    chave = f"{Path(alvo).name}|" + ",".join(f"{a[0]}:{a[1]}" for a in achados)
    p = CACHE / f"{sid}.json"
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        visto = json.loads(p.read_text()) if p.exists() else []
    except Exception:
        visto = []
    if chave in visto:
        return True
    try:
        p.write_text(json.dumps(visto + [chave]))
    except Exception:
        pass
    return False


def texto_do_hook(d):
    """The NEW TEXT -- `content` on Write, `new_string` on Edit. Not the whole file.

    On purpose: re-reading the whole file would make the guard judge what was already there and
    already went through this question once. The new writing is the right population.
    """
    ti = d.get("tool_input") or {}
    return ti.get("content") or ti.get("new_string") or ""


# ---------------------------------------------------------------- the controls

# DECLARED RECONSTRUCTION. The real file of today was already FIXED (it cites the case and the
# delta), so using it would measure the fix, not the defect. This is the text in the shape it was
# written at the moment of the error: the whole set presented as a new nuance.
CASO_POSITIVO = """
Owner order: no new command unless he allows it, and no change on the client side without him
knowing that it exists. A command is a surface the customer sees, and a surface born without his
knowledge is a surface he cannot defend.

New nuance: the measurement goes to the LOG, never to the customer screen. My need to measure does
not pay the price of a new command surface. The test runs as user0 and the admin console only prepares.
"""

# A genuinely NEW fact from the same kind of store. A guard that is too wide is a guard that gets
# turned off, so the negative cannot be a text on another subject: it has to be operational, and
# pass anyway.
# THE LAW THE POSITIVE CASE DUPLICATES -- a FORGED row, appended to a copy of the real law table.
# The control must not depend on which laws a given map happens to hold: the example map, a new
# user's map and a store of hundreds of laws all get the same fixture. The id is chosen so it cannot
# collide with a real row: the check looks for the row that STARTS with `| F1 |`.
LEI_FORJADA = ("| F1 | ✅ IN FORCE 🕳 | **No new command without the owner's order.** A command is "
               "surface the customer sees; measuring does not pay for new surface — measurement "
               "goes to the log | owner, 2026-02-12 | no mechanism yet |")
ALVO_POSITIVO = "feedback_new_command_only_by_order.md"

CASO_NEGATIVO = """
The network cable of the bench switch comes loose by itself when the cabinet door touches it. Swap
it for the flat cable already in the drawer, because the latch of the current connector is broken.
"""


def selftest():
    ok = ruim = 0
    def checa(nome, cond, extra=""):
        nonlocal ok, ruim
        print(f"  {'✓' if cond else '✗'} {nome}{extra}")
        ok, ruim = (ok + 1, ruim) if cond else (ok, ruim + 1)

    # ABSENCE OF A STORE IS NOT A GUARD FAILURE. On a clone without `~/.claude` the memory does not
    # exist, and failing there would be red for lack of population -- the CI treats code 2 as yellow.
    faltando = [r for r, p in superficies() if not p.exists()]
    if faltando:
        print(f"  ⚠️ NO STORE on this host: {', '.join(faltando)} -- the predicate was not exercised")
        print("== 0 ok · 0 failure(s) · NO POPULATION ==")
        return 2

    pulados = 0

    def pula(nome, porque):
        # A case whose population is not on this host is SKIPPED, and says why: neither a pass
        # (it proved nothing) nor a failure (nothing is broken).
        nonlocal pulados
        print(f"  - {nome} -- skipped: {porque}")
        pulados += 1

    blocos = carrega()
    if 0 < len(blocos) <= 100:
        pula("the 3 surfaces load a real population",
             f"store too small ({len(blocos)} blocks, needs >100)")
    else:
        checa(f"the 3 surfaces load ({len(blocos)} blocks)", len(blocos) > 100)
    for rotulo, path in superficies():
        checa(f"surface exists: {rotulo}", path.exists())

    import tempfile as _tf
    _orig_sup = superficies
    _td = _tf.mkdtemp()

    def com_lei(linha):
        """avalia(CASO_POSITIVO) against the real surfaces with `linha` appended to the law table."""
        _p = Path(_td, "3_DECIDIDO.md")
        try:
            _real = (RAIZ / "docs/mapa/3_DECIDIDO.md").read_text(encoding="utf-8")
        except OSError:
            _real = ""
        _p.write_text(_real.rstrip("\n") + "\n" + linha + "\n", encoding="utf-8")
        _CACHE_BLOCOS.clear(); _CACHE_INDICE.clear(); _CACHE_DISC.clear()
        globals()["superficies"] = lambda: [
            ("MEMORY.md", MEMDIR / "MEMORY.md"),
            ("mapa/1_CONTRATO.md", RAIZ / "docs/mapa/1_CONTRATO.md"),
            ("mapa/3_DECIDIDO.md", _p)]
        try:
            return avalia(CASO_POSITIVO, alvo=str(MEMDIR / ALVO_POSITIVO))
        finally:
            globals()["superficies"] = _orig_sup
            _CACHE_BLOCOS.clear(); _CACHE_INDICE.clear(); _CACHE_DISC.clear()

    def aponta_forjada(achados):
        return any(a[0] == "mapa/3_DECIDIDO.md" and a[2].startswith("| F1 |") for a in achados)

    # -- POSITIVE CONTROL: the real case has to LIGHT UP, and point at the forged law F1 --------
    ach, disc = com_lei(LEI_FORJADA)
    checa("POSITIVE · the real case lights up", len(ach) > 0,
          f"  ({len(ach)} block(s), {len(disc)} discriminating terms)")
    checa("POSITIVE · the warning points at the forged law F1", aponta_forjada(ach))
    # DECLARED BLINDNESS, AND IT IS A TEST -- not a removed test.
    #   The real case had THREE sources; the guard reaches ONE, the law (many terms in common, high
    # overlap over the paragraph). The ONE-LINE index entry (`feedback_tester_is_user0`) stays
    # below the 0.60 cut, because an eight-term summary has no mass to match.
    #   MEASURED before accepting: lowering the cut until it reached it would take the noise on the
    # store from 15% to more than 63%, and a guard that speaks on two thirds of the writes is a
    # guard nobody reads. The predicate of this test asserts the blindness: if one day it LIGHTS,
    # this control drops and forces the number to be re-checked -- a limit that changes silently is
    # a limit nobody revisits.
    #   The way to pay it is not loosening: it is the right surface. The index is a SUMMARY of the
    # memory; what has the mass is its BODY, which today is not a surface.
    achou_testador = any(a[0] == "MEMORY.md" and "tester" in normaliza(a[2]) for a in ach)
    checa("declared blindness · the 1-line index entry is NOT reached (below 0.60)",
          not achou_testador)
    for rotulo, n, trecho, casados in ach[:4]:
        print(f"      -> {rotulo}:{n} [{len(casados)}] {trecho[:96]}")

    # -- NEGATIVE CONTROL: a new fact has to PASS quietly ---------------------------------------
    ach_n, disc_n = avalia(CASO_NEGATIVO, alvo=str(MEMDIR / "project_bench_switch_cable.md"))
    checa("NEGATIVE · a new fact passes WITHOUT a warning", len(ach_n) == 0,
          f"  ({len(ach_n)} block(s), {len(disc_n)} discriminating terms)")
    for rotulo, n, trecho, casados in ach_n[:3]:
        print(f"      ✗ false positive: {rotulo}:{n} {casados} {trecho[:80]}")

    # -- ROBUSTNESS TO A LIVE SURFACE: growing the law must not erase its control ---------------
    #   FOUND BY ANOTHER SESSION, and the most dangerous defect this piece had. Someone added text
    # to the law (legitimately, the same day) and measured `--selftest` from outside: with the law
    # 102 B longer the positive control went to **ZERO blocks**. The surface the guard watches is
    # EDITED BY OTHERS at the same time, so a control that depends on the size of a live line goes
    # red over someone else's legitimate work. And it did: **two commits went out with
    # `--no-verify` because of this guard** while it was in the gate, half-ready.
    #   The cause was the coverage metric (`matched/|block|`), which calibration had already
    # replaced by the overlap coefficient -- normalizing by the SMALLER side makes the result
    # indifferent to the block growing. One defect, two symptoms: losing the duplicate in a long
    # law, and breaking the control when the law grows.
    #   This test exists so that it does not come back silently. It varies the size of the forged
    # law row from 60% to 220% and requires the positive to light in all of them.
    _enche = (" Operational reinforcement about customer-facing surface, telemetry, collection "
              "cadence and structured server log records without touching the client.")
    _sobreviveu = []
    for _rot, _nova in [("60%", LEI_FORJADA[:int(len(LEI_FORJADA) * .6)] + " |"),
                        ("100%", LEI_FORJADA),
                        ("140%", LEI_FORJADA[:-1] + _enche + " |"),
                        ("220%", LEI_FORJADA[:-1] + _enche * 3 + " |")]:
        _a, _ = com_lei(_nova)
        _sobreviveu.append(aponta_forjada(_a))
    checa("live surface · growing/shrinking the law does NOT erase the positive control",
          all(_sobreviveu), f"  (60%/100%/140%/220% -> {_sobreviveu})")
    import shutil as _sh
    _sh.rmtree(_td, ignore_errors=True)

    # -- the observer: the guard cannot accuse itself -------------------------------------------
    idx = str(MEMDIR / "MEMORY.md")
    checa("observer · the surface being written leaves the search",
          len(carrega(excluir=idx)) < len(carrega()))
    ach_p, _ = avalia("new command only by his order; measurement goes to the log",
                      alvo=str(MEMDIR / "feedback_new_command_only_by_order.md"))
    checa("observer · the file's own pointer in the index is not a duplicate",
          not any(a[0] == "MEMORY.md" and "new_command_only_by_order" in a[2] for a in ach_p))

    # -- the path trigger ----------------------------------------------------------------------
    for p, esperado in [
        (str(MEMDIR / "feedback_x.md"), True),
        (str(RAIZ / "docs/mapa/3_DECIDIDO.md"), True),
        (str(RAIZ / "docs/oraculo/scripts.md"), True),
        (str(MEMDIR / "MEMORY.md"), False),
        (str(RAIZ / "docs/project/andamento/A_PHASE_BY_MAP.md"), False),
        (str(RAIZ / "scripts/guarda-ja-existe.py"), False),
        ("/tmp/scratch.md", False),
    ]:
        checa(f"path · {'fires' if esperado else 'does NOT fire'}: …{p[-42:]}",
              bool(ALVOS.search(p)) == esperado)

    # -- own-prose filter ----------------------------------------------------------------------
    checa("backtick span and fenced block leave before tokenizing",
          not tokens(limpa_texto_novo("look at the `command surface customer` here")) & {"command"})

    # -- INJECTED DEFECT: without the frequency cut the guard lights on everything ---------------
    # Without this the selftest is decoration. The cut is what separates "a term that points at a
    # place" from "a term that lives everywhere", and it is the only piece whose failure is
    # silent: it leaves the guard GREEN and noisy at the same time.
    ach_freq, _ = avalia(CASO_NEGATIVO, alvo=str(MEMDIR / "x.md"), teto=1.0,
                         min_termos=1, sobreposicao=0.0)
    checa("injected defect · with the frequency cut OFF the negative lights up",
          len(ach_freq) > 0, f"  ({len(ach_freq)} blocks)")
    ach_sob, _ = avalia(CASO_NEGATIVO, alvo=str(MEMDIR / "x.md"), sobreposicao=0.0, min_termos=1)
    checa("injected defect · with the overlap OFF the negative lights up",
          len(ach_sob) > 0, f"  ({len(ach_sob)} blocks)")

    # -- population ----------------------------------------------------------------------------
    n, m, detalhe = varre(silencioso=True)
    print(f"  ·· population · store: {n} of {m} existing memories would light today "
          f"({100*n/m:.1f}%)")
    # The ceiling is the MEASURED operating point (15%) with slack, not a chosen number: the
    # calibration series is 98.7% -> 41.7% -> 33% -> 15%, and each drop has a named defect behind it.
    checa("population · the predicate does NOT light on the whole store (too wide gets turned off)",
          m > 0 and n / m < 0.25, f"  (acceptance ceiling: 25% · measured at calibration: 15%)")
    print(f"  ·· blocks per surface: " +
          " · ".join(f"{r}={len([b for b in blocos if b[0]==r])}" for r, _ in superficies()))
    print(f"== {ok} ok · {ruim} failure(s) · {pulados} skipped ==")
    return 1 if ruim else 0


def varre(silencioso=False):
    """Runs the predicate over ALL live memories: how many would light today?

    This is the measurement that decides whether the lexical approach is viable, and it does not
    measure accuracy -- it measures NOISE. A guard that lights on almost everything distinguishes
    nothing, and the honest answer would be not to build it. The store is the right population
    because almost every memory in it already went through the question once: what lights here is,
    mostly, real overlap with the map -- the same defect, older.
    """
    #   `indice_*_estacionado.md` IS NOT A RULE MEMORY -- it is a block of the index itself, parked
    # out of load (`scripts/memoria-estaciona.py`). By construction it "duplicates" the index: it
    # is the index. Counting it in the population lit 2 of 2 and pushed the rate across the ceiling
    # with no new rule written. The observer does not enter the population.
    arqs = sorted(p for p in MEMDIR.glob("*.md")
                  if p.name != "MEMORY.md" and not p.name.startswith("indice_"))
    acesos, detalhe = 0, []
    for p in arqs:
        try:
            ach, _ = avalia(p.read_text(encoding="utf-8"), alvo=str(p))
        except Exception:
            continue
        if ach:
            acesos += 1
            detalhe.append((p.name, len(ach), ach[0]))
    if not silencioso:
        print(f"== sweep of the store: {acesos} of {len(arqs)} memories would light "
              f"({100*acesos/max(1,len(arqs)):.1f}%) ==")
        for nome, n, top in sorted(detalhe, key=lambda x: -x[1])[:20]:
            print(f"  {n:3d}  {nome}\n       -> {top[0]}:{top[1]} {top[2][:88]}")
    return acesos, len(arqs), detalhe


# ---------------------------------------------------------------- entry point

def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        sys.exit(selftest())
    if "--varrer" in args:
        varre()
        sys.exit(0)
    if "--medir" in args:
        alvo = args[args.index("--medir") + 1]
        ach, disc = avalia(Path(alvo).read_text(encoding="utf-8"), alvo=alvo)
        print(formata(ach, disc, alvo) or f"(nothing matched · {len(disc)} discriminating terms)")
        sys.exit(0)

    try:
        d = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    alvo = (d.get("tool_input") or {}).get("file_path") or ""
    if not alvo or not ALVOS.search(alvo):
        sys.exit(0)
    texto = texto_do_hook(d)
    if len(texto) < 200:            # a surgical edit does not carry a new rule
        sys.exit(0)
    ach, disc = avalia(texto, alvo=alvo)
    if not ach or ja_disse(d, alvo, ach):
        sys.exit(0)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                             "additionalContext": formata(ach, disc, alvo)}},
                     ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # THE GUARD NEVER GETS IN THE WAY OF THE WORK. It runs on the path of every memory write,
        # and several agent sessions may run at once: a defect here would become friction in a
        # conversation that is not this one. Failing silently is the only acceptable posture -- the
        # worst case becomes "the warning did not come", never "the write did not pass".
        try:
            CACHE.mkdir(parents=True, exist_ok=True)
            (CACHE / "erros.log").open("a").write(f"{type(e).__name__}: {e}\n")
        except Exception:
            pass
        sys.exit(0)
