#!/usr/bin/env python3
"""NEIGHBOUR NOTICE — what the other sessions did in the repo since your last turn.

WHY: with several agent sessions working the same checkout, commits and state collide. The defect
seen: one working tree carried the work of FOUR sessions at the same time, none aware of the others.
Two failed CI because of a third one's draft, and one of them blamed the wrong session. A commit
conflict between agents is not a lack of lock — git's lock already serializes — it is a lack of
INFORMATION: each session sees the repo as if it were its own.

REGIME: this hook is an INTERRUPTION (`docs/CONTEXTO.md`) — it runs on every prompt, but only speaks
when the repo MOVED since the previous turn OF THIS SESSION. Nothing changed = **zero bytes**, not
even a header: the window is paid on every request, and a notice that repeats becomes noise that
one learns to skip.

The baton and the design board are explicitly asked for: `docs/mesa/BASTAO.md` and
`docs/mesa/DESENHO.md` get their own mark when they show up — they are the two files where one
session writes what the others need to know (`docs/mesa/BASTAO_REGRAS.md`).
"""
import hashlib, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipo_config as HC  # noqa: E402

#   One shared checkout, no worktree per session. The two variables exist so the PROOF runs outside
# the real repo: the target of a ruler is born OUTSIDE the instrument, and staging a commit in the
# shared index is the very error this hook exists to fix.
REPO = os.environ.get("VIZINHOS_REPO", HC.REPO)
# The per-session state lives in the hooks' state dir (hipo_config: HIPO_STATE_DIR), not in $HOME.
CACHE = os.environ.get("VIZINHOS_CACHE", os.path.join(HC.STATE_DIR, "vizinhos"))
#   A LINE BUDGET, not two ceilings that add up with nobody adding: `10 commits` + `12 dirty` gives
# 26 lines on every window. The ceiling is for the WHOLE BLOCK, and the dirty list gives way first —
# it is the repetitive part; someone else's commit is what changes a decision.
TETO_LINHAS = 15
TETO_COMMITS = 6
MARCADOS = {"docs/mesa/BASTAO.md": "BATON", "docs/mesa/DESENHO.md": "DESIGN"}


def git(*args):
    try:
        r = subprocess.run(("git", "-C", REPO) + args, capture_output=True, text=True, timeout=10)
        return r.stdout.rstrip("\n") if r.returncode == 0 else ""
    except Exception:
        return ""


def assinatura(sha):
    """The [xx] comes from the commit's `Session:` trailer. No trailer = [??], and [??] is
    information: it says that commit did not declare an owner."""
    corpo = git("show", "-s", "--format=%B", sha)
    for linha in corpo.splitlines():
        if linha.lower().startswith("session:"):
            return "[" + linha.split(":", 1)[1].strip().strip("[]") + "]"
    return "[??]"


def estado():
    """HEAD + the dirty list. Together they are what "the repo moved" means to a neighbour:
    a published commit AND work in flight that is still going to collide."""
    head = git("rev-parse", "HEAD")
    #   `--untracked-files=all` is NOT zeal: without it git COLLAPSES an entire untracked directory
    # into one line (`?? docs/`), and the file that matters vanishes inside it. Measured in the
    # selftest: a new `docs/mesa/BASTAO.md` did not light the baton mark — precisely the file that
    # had to be announced. A collapsed population is a lost population.
    sujo = [l for l in git("status", "--short", "--untracked-files=all").splitlines() if l.strip()]
    return head, sujo


def chave(dados):
    #   The `session_id` CHANGES on compaction. Measured and accepted effect: one extra notice right
    # after compacting — without a state file, the hook records HEAD and reports only the DIRTY list,
    # never a flood of old commits. Erring towards LESS is the safe side.
    sid = str(dados.get("session_id") or dados.get("transcript_path") or "sem-id")
    return hashlib.sha1(sid.encode()).hexdigest()[:16]


def render(novos, sujo, primeira):
    if not novos and not sujo:
        return ""
    marcas = [nome for caminho, nome in MARCADOS.items()
              if any(caminho in l for l in sujo) or any(caminho in a for _, _, a in novos)]
    # what is already reserved in the budget: header, the mark, and the label of each section present
    gasto = 1 + (1 if marcas else 0) + (1 if novos else 0) + (1 if sujo else 0)

    linhas = []
    if novos:
        mostra = novos[:TETO_COMMITS]
        sobra = len(novos) - len(mostra)
        gasto += len(mostra) + (1 if sobra else 0)
        linhas.append(f"HEAD moved: {len(novos)} commit(s)")
        linhas += [f"  {sha} {sig} {assunto[:72]}" for sha, sig, assunto in mostra]
        if sobra:
            linhas.append(f"  +{sobra} older commit(s)")
    if sujo:
        cabem = max(1, TETO_LINHAS - gasto)          # floor 1: a list with no item is just a number
        if len(sujo) > cabem:
            cabem = max(1, cabem - 1)                # the `+K` line itself takes a slot in the budget
        mostra = sujo[:cabem]
        sobra = len(sujo) - len(mostra)
        linhas.append(f"DIRTY in the tree (not yours until you prove it): {len(sujo)} file(s)")
        linhas += [f"  {l[:78]}" for l in mostra]
        if sobra:
            linhas.append(f"  +{sobra} not shown")
    cab = "<!-- vizinhos: the repo moved since your last turn -->"
    if primeira:
        cab = "<!-- vizinhos: 1st reading of this session — current state only, no history -->"
    if marcas:
        linhas.append("⚠️ " + " and ".join(marcas) + " in the middle — it is where sessions write to each other")
    return cab + "\n" + "\n".join(linhas) + "\n"


def main():
    try:
        dados = json.load(sys.stdin)
    except Exception:
        dados = {}
    os.makedirs(CACHE, exist_ok=True)
    alvo = os.path.join(CACHE, chave(dados) + ".estado")

    head, sujo = estado()
    if not head:
        return 0  # not a repo, or git unavailable — staying quiet is right, nothing to announce
    impressao = head + "|" + hashlib.sha1("\n".join(sujo).encode()).hexdigest()[:12]

    anterior = ""
    try:
        with open(alvo, encoding="utf-8") as f:
            anterior = f.read().strip()
    except OSError:
        pass

    if anterior == impressao:
        return 0  # NOTHING CHANGED — zero bytes, which is the contract

    primeira = not anterior
    novos = []
    if anterior and "|" in anterior:
        visto = anterior.split("|", 1)[0]
        bruto = git("log", "--format=%h%x09%s", f"{visto}..HEAD")
        for l in (bruto.splitlines() if bruto else []):
            sha, _, assunto = l.partition("\t")
            novos.append((sha, assinatura(sha), assunto))

    saida = render(novos, sujo, primeira)
    try:
        with open(alvo, "w", encoding="utf-8") as f:
            f.write(impressao)
    except OSError:
        pass
    if saida:
        sys.stdout.write(saida)
    return 0


# ---------------------------------------------------------------------------- selftest

def _sh(cwd, *args):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _chama(repo, cache, sid):
    """Runs the ARTIFACT as a process, with JSON on stdin — which is how the hook is invoked.
    Calling main() by import would measure a re-implementation, not what runs for real."""
    amb = dict(os.environ, VIZINHOS_REPO=repo, VIZINHOS_CACHE=cache)
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], input=json.dumps({"session_id": sid}),
                       capture_output=True, text=True, env=amb)
    return r.stdout


def selftest():
    import shutil, tempfile
    base = tempfile.mkdtemp(prefix="vizinhos-prova-")
    repo, cache = os.path.join(base, "repo"), os.path.join(base, "cache")
    os.makedirs(repo)
    _sh(repo, "git", "init", "-q", "-b", "master")
    _sh(repo, "git", "config", "user.email", "prova@lab")
    _sh(repo, "git", "config", "user.name", "prova")
    open(os.path.join(repo, "raiz.txt"), "w").write("1\n")
    _sh(repo, "git", "add", "raiz.txt")
    _sh(repo, "git", "commit", "-q", "-m", "root\n\nSession: ax")

    casos, falhas = [], []

    def caso(rotulo, ok, detalhe=""):
        casos.append((rotulo, ok, detalhe))
        if not ok:
            falhas.append(rotulo)

    # 1st reading of each session: records HEAD, clean repo -> nothing to say
    a0, b0 = _chama(repo, cache, "A"), _chama(repo, cache, "B")
    caso("NEG 1 · 1st reading with a clean repo = 0 bytes", a0 == "" and b0 == "",
         f"A={len(a0)}B B={len(b0)}B")

    # POS 1 — a dirty file must appear, and for BOTH sessions
    open(os.path.join(repo, "novo.txt"), "w").write("x\n")
    a1, b1 = _chama(repo, cache, "A"), _chama(repo, cache, "B")
    caso("POS 1 · dirty file shows up for both sessions",
         "novo.txt" in a1 and "novo.txt" in b1, f"A={len(a1)}B B={len(b1)}B")

    # NEG 2 — NOTHING changed since the previous turn: zero bytes, not even a header. The contract.
    a2 = _chama(repo, cache, "A")
    caso("NEG 2 · nothing changed = 0 bytes", a2 == "", f"{len(a2)}B: {a2[:60]!r}")

    # POS 2 — a commit with a trailer: the neighbour session sees the [xx]
    _sh(repo, "git", "add", "novo.txt")
    _sh(repo, "git", "commit", "-q", "-m", "neighbour's work\n\nSession: qz")
    a3 = _chama(repo, cache, "A")
    caso("POS 2 · the neighbour's commit arrives signed [qz]",
         "HEAD moved" in a3 and "[qz]" in a3, a3.strip().replace("\n", " | ")[:100])

    # NEG 3 — sessions are INDEPENDENT: A having consumed it does not silence B
    b3 = _chama(repo, cache, "B")
    caso("NEG 3 · B sees the same commit after A consumed it",
         "[qz]" in b3, b3.strip().replace("\n", " | ")[:80])

    # POS 3 — without a trailer the commit is not invisible: it becomes [??], which is information
    open(os.path.join(repo, "anonimo.txt"), "w").write("y\n")
    _sh(repo, "git", "add", "anonimo.txt")
    _sh(repo, "git", "commit", "-q", "-m", "commit without a declared owner")
    a4 = _chama(repo, cache, "A")
    caso("POS 3 · a commit without a trailer becomes [??]", "[??]" in a4,
         a4.strip().replace("\n", " | ")[:80])

    # POS 4 — the BATON and the DESIGN board get a mark
    os.makedirs(os.path.join(repo, "docs", "mesa"), exist_ok=True)
    open(os.path.join(repo, "docs", "mesa", "BASTAO.md"), "w").write("estado\n")
    a5 = _chama(repo, cache, "A")
    caso("POS 4 · a dirty BASTAO gets its own mark", "BATON" in a5,
         a5.strip().splitlines()[-1][:80] if a5 else "(empty)")

    # POS 5 — the CEILING. `--custo` once showed 16 lines against a ceiling of 15 and no control
    # complained: a ruler only the report sees is not in the proof. Fat state on purpose.
    for i in range(12):
        open(os.path.join(repo, f"g{i}.txt"), "w").write("z\n")
        _sh(repo, "git", "add", f"g{i}.txt")
        _sh(repo, "git", "commit", "-q", "-m", f"fat commit {i}\n\nSession: kv")
    for i in range(25):
        open(os.path.join(repo, f"h{i}.txt"), "w").write("z\n")
    a6 = _chama(repo, cache, "A")
    n6 = len(a6.splitlines())
    caso(f"POS 5 · 12 commits + 25 dirty fit the ceiling of {TETO_LINHAS}", n6 <= TETO_LINHAS,
         f"{n6} line(s), {len(a6)} B")

    print("CONTROLS OF THE NEIGHBOUR NOTICE")
    for rotulo, ok, detalhe in casos:
        print(f"  {'✓' if ok else '✗'} {rotulo}")
        if detalhe:
            print(f"      {detalhe}")
    print(f"── {len(casos) - len(falhas)} of {len(casos)} controls passed")
    shutil.rmtree(base, ignore_errors=True)
    return 1 if falhas else 0


def custo():
    """The 3 states worth measuring. Ruler: bytes injected into the window."""
    import shutil, tempfile
    base = tempfile.mkdtemp(prefix="vizinhos-custo-")
    repo, cache = os.path.join(base, "repo"), os.path.join(base, "cache")
    os.makedirs(repo)
    _sh(repo, "git", "init", "-q", "-b", "master")
    _sh(repo, "git", "config", "user.email", "c@lab")
    _sh(repo, "git", "config", "user.name", "c")
    open(os.path.join(repo, "r.txt"), "w").write("1\n")
    _sh(repo, "git", "add", "r.txt")
    _sh(repo, "git", "commit", "-q", "-m", "root\n\nSession: ax")
    _chama(repo, cache, "M")
    def regua(rotulo, saida):
        n = len(saida.splitlines())
        alerta = "" if n <= TETO_LINHAS else f"  ⚠️ OVER the ceiling of {TETO_LINHAS}"
        print(f"  {rotulo:<30} {len(saida):5d} B · {n:2d} line(s){alerta}")

    regua("nothing changed", _chama(repo, cache, "M"))

    for i in range(1):
        open(os.path.join(repo, f"c{i}.txt"), "w").write("x\n")
        _sh(repo, "git", "add", f"c{i}.txt")
        _sh(repo, "git", "commit", "-q", "-m", f"commit {i}\n\nSession: qz")
    for i in range(3):
        open(os.path.join(repo, f"s{i}.txt"), "w").write("x\n")
    regua("1 commit + 3 dirty", _chama(repo, cache, "M"))

    for i in range(1, 11):
        open(os.path.join(repo, f"d{i}.txt"), "w").write("x\n")
        _sh(repo, "git", "add", f"d{i}.txt")
        _sh(repo, "git", "commit", "-q", "-m", f"long commit number {i}\n\nSession: kv")
    for i in range(20):
        open(os.path.join(repo, f"t{i}.txt"), "w").write("x\n")
    regua("10 commits + 20 dirty (ceiling)", _chama(repo, cache, "M"))
    shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--custo" in sys.argv:
        sys.exit(custo())
    sys.exit(main())
