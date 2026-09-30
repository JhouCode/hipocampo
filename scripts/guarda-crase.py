#!/usr/bin/env python3
"""
BACKTICK GUARD -- blocks the command BEFORE the shell eats the text.

WHY IT EXISTS (the owner's order): *"backticks in an inline message turned into command
substitution -- make a hook that always runs before you create the bash commands, formalizing the
text so this error never happens again."*

  This class of error happened **five times in a single day**, each in a different form:

    1. an unquoted heredoc ate `` `LOOK` `` and left `\\LOOK\\` in a C++ source comment;
    2. the same heredoc turned `` `3 ticks...` `` into a **control byte 0x03** in the middle of the
       file -- the backtick vanished together with the digit, and nothing complained;
    3. an unescaping `sed` written from memory, never matched against the real output;
    4. the message of a `git commit -m "..."` with `` `restore` `` inside: the shell tried to
       EXECUTE it and returned *"restore: command not found"*;
    5. the same thing, again, with `` `replace` ``.

  The pattern is always the same and it is not distraction: **technical prose has function names,
function names go between backticks -- and the backtick is the oldest operator of the shell.** The
text is right; the transport destroys it. And it destroys it SILENTLY, which is what makes this
expensive: in cases 1 and 2 the file went to disk corrupted and only showed up hours later, in a
`cat -A`.

WHAT IT BLOCKS
  · `-m "..."` (git commit and friends) with a backtick inside the double quotes;
  · an **unquoted** heredoc (`<<EOF`, not `<<'EOF'`) whose body has a backtick or `$`.

WHAT IT DOES NOT BLOCK -- and this list matters as much as the one above, because a guard that
gets in the way of legitimate work is a guard someone turns off:
  · a backtick in SINGLE quotes (the shell does not interpret it);
  · a quoted heredoc `<<'EOF'` (literal by construction -- it is the RIGHT form);
  · real command substitution in `$(...)`;
  · a backtick outside any quotes, which is the deliberate use;
  · the **herestring `<<<`** -- it is another operator, and it never opens a heredoc;
  · the **body of a quoted heredoc**, even when that body TALKS about heredocs: inside `<<'EOF'`
    nothing is interpolated, so a `<<PY` there is text, not an opening.

  The last two came in after a FALSE RED: the guard blocked a legitimate `cat > script.sh <<'EOF'`
whose body contained the string `<<< DIVERGE`. It matched the last two `<` of the herestring and
read the body of the quoted heredoc as if it were shell. The symptom measured the size of the
defect: **it was impossible to write this guard's test from inside the shell** -- the test file is
a quoted heredoc that talks about heredocs, and the guard blocked itself.
  This is not a regex detail: a guard that blocks right work is a guard someone turns off the third
time, and `--no-verify` does not tell a false red from a real one. That is why the three cases
became selftest rows -- a workaround that does not become a case comes back.

OUTPUT: exit 2 = blocks, and the stderr text goes back to the agent (PreToolUse convention).
        exit 0 = lets it pass.
"""
import json
import re
import sys


#   `(?<!<)` discards bash's `<<<` -- a herestring is NOT a heredoc. Without it the regex matches the
# last two `<` of a `<<<` and invents a heredoc labelled with the next word.
ABERTURA = r"(?<!<)<<-?\s*([\"']?)([A-Za-z_][A-Za-z0-9_]*)\1"


def _fim_do_corpo(cmd, inicio, rotulo):
    """Offset in `cmd` where the heredoc body ends -- the line that holds only the label."""
    resto = cmd[inicio:]
    fim = re.search(r"^\s*%s\s*$" % re.escape(rotulo), resto, re.MULTILINE)
    return inicio + (fim.start() if fim else len(resto))


def _apaga_corpo_dos_citados(cmd):
    """Returns `cmd` with the body of each QUOTED heredoc replaced by spaces (offsets preserved).

    Inside `<<'EOF'` **nothing** is interpolated -- what looks like a second heredoc opening there
    is text. Without this, writing a script that CONTAINS heredocs was blocked, and the guard even
    prevented its own test from being written."""
    saida = list(cmd)
    for m in re.finditer(r"(?<!<)<<-?\s*([\"'])([A-Za-z_][A-Za-z0-9_]*)\1", cmd):
        for i in range(m.end(), _fim_do_corpo(cmd, m.end(), m.group(2))):
            if saida[i] != "\n":      # the newline stays: the `^...$` of the other labels needs it
                saida[i] = " "
    return "".join(saida)


def corpo_dos_heredocs_nao_citados(cmd):
    """Returns (label, body) for each heredoc whose delimiter is NOT quoted.

    `<<'EOF'` and `<<"EOF"` are literal -- the shell does not touch the content. `<<EOF` is
    interpolated, and that is where a backtick becomes execution.

    The opening is searched in the text with the quoted bodies ERASED, but the returned body comes
    from the ORIGINAL `cmd`: inside an unquoted heredoc everything is interpolated, including what
    looks like a quoted block there -- erasing that span would blind the guard to the backtick in it."""
    achados = []
    for m in re.finditer(ABERTURA, _apaga_corpo_dos_citados(cmd)):
        citado, rotulo = m.group(1), m.group(2)
        if citado:
            continue
        achados.append((rotulo, cmd[m.end():_fim_do_corpo(cmd, m.end(), rotulo)]))
    return achados


def strings_de_mensagem(cmd):
    """The content of each `-m "..."` / `-F "..."` -- the commit message is the champion case."""
    return [m.group(1) for m in re.finditer(r'-m\s+"((?:[^"\\]|\\.)*)"', cmd)]


def main():
    try:
        dados = json.load(sys.stdin)
    except Exception:
        return 0                      # unreadable input is no reason to stop the work

    if dados.get("tool_name") != "Bash":
        return 0

    cmd = (dados.get("tool_input") or {}).get("command") or ""
    if "`" not in cmd and "<<" not in cmd:
        return 0                      # the common case leaves here, at no cost

    problemas = []

    for texto in strings_de_mensagem(cmd):
        if "`" in texto:
            problemas.append(
                "  · `-m \"...\"` with a BACKTICK inside double quotes.\n"
                "    The shell will try to EXECUTE what is between backticks before git sees it.\n"
                "    Excerpt: %s" % _amostra(texto))

    for rotulo, corpo in corpo_dos_heredocs_nao_citados(cmd):
        if "`" in corpo or "$" in corpo:
            problemas.append(
                "  · UNQUOTED heredoc `<<%s` with a backtick or `$` in the body.\n"
                "    The content is interpolated: a backtick executes, `$x` becomes empty, and the\n"
                "    file goes to disk corrupted WITHOUT an error. That is how a `3` became byte 0x03.\n"
                "    Excerpt: %s" % (rotulo, _amostra(corpo)))

    if not problemas:
        return 0

    sys.stderr.write(
        "🚫 BACKTICK GUARD -- the text would be destroyed by the shell before reaching its target.\n\n"
        + "\n".join(problemas)
        + "\n\nTHE FIX, and it is always one of these two:\n"
          "  1. commit message -> write it to a file with the Write tool and use\n"
          "     `git commit -F <file>`. Never `-m` with technical prose.\n"
          "  2. heredoc -> quote the delimiter: `<<'EOF'` instead of `<<EOF`.\n\n"
        "Why block instead of warn: the five times this bit in one day were ALL\n"
        "silent -- the command exited with success and the damage showed up later.\n")
    return 2


def _amostra(texto):
    i = texto.find("`")
    if i < 0:
        i = max(texto.find("$"), 0)
    return "..." + texto[max(0, i - 30):i + 40].replace("\n", "\\n") + "..."


#   THE SELFTEST, and it has BOTH halves.
#
#   Cases that MUST block prove that it sees. Cases that MUST pass prove that it is not too wide --
# and that half matters more here: a PreToolUse guard that blocks legitimate work is a guard
# someone turns off the third time, and then it protects nothing.
CASOS = [
    # (label, command, must_block)
    ("commit -m with a backtick",
     'git commit -m "fixes the `restore` of the script"', True),
    ("commit -m with two backticks",
     'git commit -m "the `replace` finds nothing, says nothing"', True),
    ("unquoted heredoc with a backtick",
     "python3 - <<PY\nx = 'the `3` becomes a control byte'\nPY", True),
    ("unquoted heredoc with a dollar",
     "cat <<EOF > f.txt\ncosts $HOME dollars\nEOF", True),

    ("QUOTED heredoc with a backtick -- the right form",
     "python3 - <<'PY'\nx = 'the `3` survives here'\nPY", False),
    ("commit -F file -- the right form",
     "git commit -F /tmp/msg.txt", False),
    ("backtick in SINGLE quotes",
     "grep 'the `filter` starts closed' file.c", False),
    ("real command substitution",
     'echo "today is $(date +%F)"', False),
    ("common command without any backtick",
     "ls -l /srv/app/repo", False),
    ("clean commit -m, no backtick",
     'git commit -m "fixes the restore of the script"', False),

    #   The three below were born from a real FALSE RED: the guard blocked a legitimate
    # `cat > script.sh <<'EOF'` because the body contained the string `<<< DIVERGE`. It matched the
    # last two `<` of the herestring AND read the body of the quoted heredoc as if it were shell.
    #   The symptom was expensive in the right way: its test could not even be WRITTEN from inside
    # the shell -- the test file is a quoted heredoc that talks about heredocs, and it was blocked
    # too. A false red in a guard is the known road to `--no-verify`, so the workaround became a case.
    ("herestring -- `<<<` never opens a heredoc",
     'tr a-z A-Z <<< DIVERGE && echo "done in $PWD"', False),
    ("quoted heredoc that TALKS about heredocs -- the body is literal",
     "cat > s.sh <<'EOF'\npython3 - <<PY\nprint(\"$x\")\nPY\nEOF", False),
    ("unquoted AFTER a closed quoted one -- the fix must not blind this",
     "cat > a.sh <<'EOF'\nliteral\nEOF\ncat > b.txt <<END\ncosts $HOME dollars\nEND", True),
]


def selftest():
    import io
    falhas = 0
    for rotulo, cmd, deve in CASOS:
        entrada = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
        sys.stdin = io.StringIO(entrada)
        erro = io.StringIO()
        real, sys.stderr = sys.stderr, erro
        try:
            codigo = main()
        finally:
            sys.stderr = real
        barrou = (codigo == 2)
        ok = (barrou == deve)
        if not ok:
            falhas += 1
        print("   %s %-42s %s" % ("\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m",
                                  rotulo,
                                  ("blocked" if barrou else "passed")
                                  + ("" if ok else "  <- expected to %s"
                                     % ("block" if deve else "pass"))))
    barram = sum(1 for _, _, d in CASOS if d)
    print("\n%s %d of %d cases (%d that must block, %d that must pass)"
          % ("✓" if not falhas else "✗ %d FAILURE(S) in" % falhas,
             len(CASOS) - falhas, len(CASOS), barram, len(CASOS) - barram))
    return 1 if falhas else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
