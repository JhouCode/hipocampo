#!/usr/bin/env python3
"""HORIZON -- does the source cover the period I am making a claim about?

WHY IT EXISTS. A conversation opened with the number that defined the problem: *"182 of 200
memories were never touched after being created (91%). Thousands of lines added against a few
hundred removed. The cure does not exist as an event."* It was called devastating and clear.

  It was an artifact. The git mirror of the memory folder had been born two days earlier, with the
  200 memories entering at once. For that git, every memory was created on the same day -- so
  *"never revised"* there meant **"not touched in the last two days"**, which is not news.

  Git answered correctly. It was not the question being asked. **Nobody asked what period the
  source covers** -- the question was how many revisions, and the answer was used.

WHAT IT DOES: on `PostToolUse`, when a command measures history (`git log`/`shortlog`/`--since`/
`--numstat`) over a path, it answers the question that was not asked.

THE PREDICATE IS THE BULK IMPORT, not the age. An old path is not a problem; a path where most
files entered in a single commit is -- there the creation date is the import date, and every "per
lifetime" rate derived from it is false. It anchors on the objective FACT (how many files entered
together), not on an age heuristic.

WHAT IT DOES NOT CATCH, declared: a source that was born gradually but covers less than the
claimed window. Then the horizon shows up in the warning and the reading is the agent's.

OUTPUT: exit 0 + additionalContext when there is a bulk import; silent exit 0 when there is not.
        It never blocks -- this informs, it does not gate.
"""
import json
import os
import re
import subprocess
import sys

MEDE_HISTORIA = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?(?:log|shortlog|rev-list)\b|--numstat\b|--since\b")
LIMIAR_BLOCO = 0.5          # half of the files entering together already kills the creation date


def sem_heredoc(cmd):
    """A heredoc body is CONTENT being written, not a path being measured.

    LIVE FINDING, minutes after this guard went up: it lit on a `git commit` because the COMMIT
    MESSAGE (in a heredoc) cited the memory mirror's path. Writing about a path is not measuring it.
    It was the same defect just fixed in a sibling script -- and nobody asked how many siblings it
    had. A fix carries a population."""
    return re.sub(r"<<-?\s*(['\"]?)([A-Za-z_]\w*)\1.*?^\s*\2\s*$", " ", cmd, flags=re.S | re.M)


def caminhos(cmd):
    """Plausible targets: a token with a slash or that exists on disk. No metacharacter -- a search
    pattern is not a path."""
    # `*` and `?` are shell GLOB -- a legitimate path, not a search pattern. `\\ | [ ] ( ) ^ $`
    # belong to regex and give away a search argument. A glob reduces to its directory:
    # `memoria/*.md` is a question about `memoria/`. (Found by the selftest itself: without this,
    # `--numstat -- memoria/*.md`, the form actually used in the original mistake, slipped through.)
    fora = re.compile(r"[\\|\[\]()^$]")
    for t in cmd.split():
        t = t.strip("'\"")
        if t.startswith("-") or fora.search(t):
            continue
        if "*" in t or "?" in t:
            t = os.path.dirname(t)
            if not t:
                continue
        if "/" in t or os.path.exists(t):
            yield t.rstrip("/")


def git(args, cwd=None):
    try:
        return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                              timeout=20).stdout
    except Exception:
        return ""


def bloco(caminho):
    """Returns (date, n_in_biggest_commit, n_total) if there is a bulk import; otherwise None."""
    saida = git(["log", "--diff-filter=A", "--format=%H|%ad", "--date=short",
                 "--name-only", "--", caminho])
    if not saida.strip():
        return None
    por_commit, atual, data = {}, None, None
    for linha in saida.splitlines():
        if "|" in linha and not linha.startswith(" "):
            atual, data = linha.split("|", 1)
            por_commit.setdefault(atual, [data, 0])
        elif linha.strip() and atual:
            por_commit[atual][1] += 1
    total = sum(v[1] for v in por_commit.values())
    if total < 10:
        return None
    maior = max(por_commit.values(), key=lambda v: v[1])
    if maior[1] / total >= LIMIAR_BLOCO:
        return (maior[0], maior[1], total)
    return None


def segmentos(cmd):
    """Splits on `&&`, `||`, `;` and `|`.

    The path has to be IN THE SAME segment as the verb that measures history. Live finding: a
    command with `git log --oneline origin/main..HEAD` AND a `diff -rq ... memoria/` lit up -- the
    `git log` was about the whole repo, and the path came from the `diff`. Measuring one piece does
    not authorize attributing the target of another; it is the same finding that `escrita_do_item`
    in `gatilho.py` already carried (*"a write in one piece contaminated the read in another"*)."""
    return re.split(r"&&|\|\||;|\|", cmd)


def avalia(cmd):
    cmd = sem_heredoc(cmd or "")
    for seg in segmentos(cmd):
        if not MEDE_HISTORIA.search(seg):
            continue
        r = _no_segmento(seg)
        if r:
            return r
    return None


def _no_segmento(cmd):
    for c in caminhos(cmd):
        b = bloco(c)
        if b:
            data, n, total = b
            return ("⚠️ SOURCE HORIZON -- `%s`: **%d of %d files entered in a single commit, on "
                    "%s**.\n   The creation date there is the IMPORT date, not the date of the fact. A "
                    "per-lifetime rate (\"never revised\", \"N per month\") computed over this is an "
                    "ARTIFACT -- that is exactly how a \"182 of 200 never revised\" was once born.\n   "
                    "Before publishing: say what period the source covers, or measure in another "
                    "source." % (c, n, total, data))
    return None


def main():
    try:
        dados = json.load(sys.stdin)
    except Exception:
        return 0
    if dados.get("tool_name") != "Bash":
        return 0
    aviso = avalia((dados.get("tool_input") or {}).get("command", ""))
    if aviso:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse", "additionalContext": aviso}}))
    return 0


def selftest():
    # Runs against the git repository of the current directory: `memoria/` must be a folder that
    # entered in bulk, and `docs/` one that grew commit by commit. The cases that need that SHAPE
    # carry it as a precondition: where the repository does not have it (a fresh clone is ONE
    # commit), the case is SKIPPED and says what it needs -- neither a pass nor a failure.
    tem_import = bloco("memoria/") is not None
    docs_gradual = bloco("docs/") is None
    pede_import = None if tem_import else (
        "needs a `memoria/` folder where >=10 files entered and most of them in ONE commit")
    pede_gradual = None if docs_gradual else (
        "needs a `docs/` folder grown commit by commit (here most of it entered in one commit)")
    casos = [
        ("git log on the mirror imported in bulk (the original case)",
         "git log --oneline -- memoria/", True, pede_import),
        ("numstat on the same mirror", "git log --numstat -- memoria/*.md", True, pede_import),
        # -- negatives: this is where a bad guard gives itself away -----------------------------
        ("git log on docs/, which grew commit by commit", "git log --oneline -- docs/", False,
         pede_gradual),
        ("git log without any path", "git log --oneline -5", False, None),
        ("command that only CITES git log in prose", "echo 'ran git log yesterday'", False, None),
        ("ls does not measure history", "ls -la memoria/", False, None),
        ("git log WITHOUT a path + diff in another segment citing memoria/ (live finding)",
         "git log --oneline origin/main..HEAD | wc -l; diff -rq a /srv/app/repo/memoria", False, None),
        ("git log on a commit whose MESSAGE cites memoria/ (live finding)",
         "cat > /tmp/m.txt <<'EOF'\nthe mirror repo/memoria/ was born on day one\nEOF\ngit commit -F /tmp/m.txt && git log --oneline -1", False, None),
    ]
    ok = pulados = 0
    for rotulo, cmd, esperado, pede in casos:
        if pede:
            pulados += 1
            print("   - %-52s skipped: %s" % (rotulo, pede))
            continue
        got = avalia(cmd) is not None
        acertou = got == esperado
        ok += acertou
        print("   %s %-52s %s" % ("\033[32m✓\033[0m" if acertou else "\033[31m✗\033[0m",
                                  rotulo, "warns" if got else "quiet"))
    rodados = [c for c in casos if not c[3]]
    pos = sum(1 for c in rodados if c[2])
    print("\n%s %d of %d  (%d that must warn, %d that must stay quiet) · %d skipped"
          % ("\033[32mOK\033[0m" if ok == len(rodados) else "\033[31mFAILED\033[0m",
             ok, len(rodados), pos, len(rodados) - pos, pulados))
    return 0 if ok == len(rodados) else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
