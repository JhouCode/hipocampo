#!/usr/bin/env python3
"""THE CASCADE GUARD -- the link has to SHOUT when it breaks, not vanish.

The paradigm splits each memory into a rule (`escopo: metodo`, the method) + a case
(`escopo: <domain>`), linked by pointer. The risk is not the number of files: it is the cascade
going SILENT -- the method surviving alone, claiming evidence that already died, or the case
becoming an orphan without a rule.

That is why the link carries a POPULATION (`prova: N`, the number of live cases), not only an
address. An address cannot be checked; a number can be recounted.

Field names and values are parsed as written (`escopo`, `prova`, `regra`, `estado`, `motivo`,
`revogados`; `metodo`, `fundido`, `vivo`, `morto`; case files start with `caso_`). See
docs/MEMORIA.md for their meaning.
"""
import os, re, sys, pathlib

def fm(txt, campo):
    m = re.search(r"^\s*%s:\s*(.+?)\s*$" % campo, txt, re.M)
    return m.group(1) if m else None

def sem_codigo(txt):
    """Strips fenced blocks and backtick spans BEFORE looking for pointers.

    Without this the guard eats its own prose: the memory that EXPLAINS the `[[name]]` syntax
    quotes the example, and one that documents a regex quotes `[[:space:]]`. A predicate has to
    filter comments before it asks."""
    txt = re.sub(r"\A---\n.*?\n---\n", "", txt, flags=re.S)   # frontmatter: summary, not body
    txt = re.sub(r"```.*?```", "", txt, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", txt)


def varre(d):
    d = pathlib.Path(d)
    arqs = {p.stem: p.read_text() for p in d.glob("*.md") if p.stem != "MEMORY"}
    falhas, fundidos = [], []
    for nome, txt in arqs.items():
        escopo, prova, regra = fm(txt,"escopo"), fm(txt,"prova"), fm(txt,"regra")
        estado = fm(txt,"estado") or "vivo"
        if estado == "morto" and not fm(txt,"motivo"):
            falhas.append("%s: dead WITHOUT `motivo:` -- a mute tombstone does not stop re-proposing what failed" % nome)

        # 1 · every [[link]] resolves -- a broken link is the classic silence
        for alvo in re.findall(r"\[\[([^\]]+)\]\]", sem_codigo(txt)):
            alvo = alvo.split("|")[0].strip()   # [[name|text]] -- the target is before the bar
            if alvo not in arqs:
                falhas.append("%s: dead pointer [[%s]]" % (nome, alvo))

        # 2 · a method declares its evidence, and the number HAS to match who points back
        if escopo == "metodo":
            # `prova: fundido` (merged) = the case EXISTS, but still inside the body of the rule
            # itself, without an address of its own. It is not folklore (folklore is a rule WITHOUT
            # a case); it is the debt of a bulk triage, when a whole store got a scope and almost
            # none had been split. Accepted on purpose, and COUNTED -- silent debt is what this
            # guard exists to kill.
            if prova == "fundido":
                fundidos.append(nome)
                continue
            if prova is None:
                falhas.append("%s: method without a `prova:` field -- a rule with no declared evidence" % nome)
            else:
                # counts only LIVE cases. Killing a case FORCES a touch on the method -- that is
                # how the cascade stops being silent: a revocation does not go unnoticed.
                reais = sum(1 for t in arqs.values()
                            if fm(t,"regra") == nome and (fm(t,"estado") or "vivo") == "vivo")
                mortos = sum(1 for t in arqs.values()
                             if fm(t,"regra") == nome and fm(t,"estado") == "morto")
                # A revocation demands an explicit ACCEPTANCE in the method (`revogados: M`).
                # Without it the guard would stay red forever after any death -- and a red that
                # never clears is what makes someone switch the guard off. The acceptance follows
                # the same principle: a declared number, which is recounted.
                aceitos = int(fm(txt,"revogados") or 0)
                if mortos != aceitos:
                    falhas.append("%s: %d REVOKED case(s), %d accepted -- check whether the rule "
                                  "still holds and declare `revogados: %d`" % (nome, mortos, aceitos, mortos))
                # `prova:` IS A NUMBER OR `fundido` -- and a value outside that used to bring down
                # the WHOLE instrument with a `ValueError`, not one memory. A guard that dies
                # instead of failing stops protecting everything after it, and the symptom
                # (a traceback) does not say which file has the wrong field.
                try:
                    esperado = int(prova)
                except ValueError:
                    falhas.append("%s: `prova: %s` is neither a number nor `fundido` -- the field counts "
                                  "how many cases point back (%d here)" % (nome, prova, reais))
                else:
                    if esperado != reais:
                        falhas.append("%s: says `prova: %s`, but %d case(s) point back"
                                      % (nome, prova, reais))
                if reais == 0:
                    falhas.append("%s: FOLKLORE -- a rule without any live case" % nome)

        # 3 · orphan case: points to a rule that does not exist, or to none
        if escopo and escopo != "metodo" and nome.startswith("caso_"):
            if not regra:
                falhas.append("%s: case without a `regra:` field -- evidence that proves nothing" % nome)
            elif regra not in arqs:
                falhas.append("%s: points to a missing rule `%s`" % (nome, regra))
    if fundidos:
        print('  \033[33m·\033[0m %d method(s) with the case MERGED in the body -- declared triage debt' % len(fundidos))
    return falhas

if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv)>1 else "."
    #   An absent or empty folder has no population: a green here would read as "cascade intact"
    # about memories that were never there. Zero is not a result.
    if not os.path.isdir(alvo) or not [p for p in os.listdir(alvo) if p.endswith(".md") and p != "MEMORY.md"]:
        print("  \033[31m✗\033[0m %s: %s" % (alvo, "no such folder" if not os.path.isdir(alvo) else "no memory file (*.md) to check"))
        print("\033[31mFAILED: no population -- the cascade was not checked\033[0m")
        sys.exit(1)
    f = varre(alvo)
    for x in f: print("  \033[31m✗\033[0m", x)
    print("\033[32mOK -- cascade intact\033[0m" if not f else "\033[31mFAILED: %d\033[0m" % len(f))
    sys.exit(1 if f else 0)
