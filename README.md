# Hipocampo

The reference repository of the article *Hipocampo: the memory I built around Claude Code, piece by
piece, and what each piece measures*
([English](https://ksmit.com.br/en/blog/hipocampo) · [Português](https://ksmit.com.br/blog/hipocampo)).

Hipocampo is an arrangement of native Claude Code features: hook events in a `settings.json`, the
native memory index (`MEMORY.md`), `CLAUDE.md`, one compaction setting, a skill, and a git
pre-commit. The hooks call shell and Python scripts over plain text files. There is no server, no
MCP, no database and no third-party package.

This repository exists to be **read**: how each piece receives its input, what it returns, and how
it is proven failing. Nothing here installs itself, by choice (article, section 8 item 3): the rules
of one operator came from that operator's corrections and do not serve somebody else's project.
What transfers is the structure — regimes, slices, the escalator, the revolving door and the
guards. The content (the real memories, the real map, the real baton) stays private; each piece
ships with a **mold** and invented example content.

**Came here from a thread?** The [FAQ](docs/FAQ.md) answers the questions people asked there, with
the measurement and the code behind each answer.

Written and tested on Linux. Dependencies: **bash**, **python3** (standard library only) and **git**,
plus the usual GNU userland the scripts call (`awk`, `sed`, `grep`, `cut`, `tr`, `wc`, `head`,
`tail`, `tac`, `seq`, `cksum`, `mktemp`, `find`, `date`). `scripts/memoria-espelho.sh` also uses
`rsync` and `flock`, and its `--status` reads `crontab`; `tests/smoke.sh` uses `timeout`. No `jq`:
the map hook reads its JSON through python3.

## Words used below

- **Regimes**: the three ways a piece of information reaches the model. *Resident* arrives before
  the first decision, every session (the map, the index, the baton); *paged* arrives only if someone
  opens it (`CLAUDE.md`, docs, each memory file); *interrupt* arrives when a touched path or command
  matches a registered source (the escalator).
- **Slices**: the map is split into several hook commands because the runtime caps each command's
  output at 10,000 units; each command prints one slice, labelled "part N of M".
- **Escalator**: a debt noted in a source file is first *warned* at the touch (`PostToolUse`), then
  *charged* when the turn ends without paying it (`Stop`), then *blocked* with a permission question
  (`PreToolUse`) after it missed its **rides** (each touch of the path that did not pay it is a ride).
- **Revolving door**: for something to enter the resident layer, something must leave; a tare and a
  target in bytes make the rule measurable.
- **Baton**: a file with the live state of the work in flight, delivered by a hook right after a
  compaction, so the state survives the summary.
- **Desk**: the session that thinks, designs and writes briefings, and does not operate (the skill in
  `skills/desenho/`); the session that operates is the *worker*.
- **Oracle** (area ruler): the rules of the area being touched (scripts, database, build...), injected
  before the work starts.

## What is here

| path | what it is |
|---|---|
| `scripts/` | the pieces, one script each (names kept as in the article, which cites them) |
| `scripts/hipo_config.py`, `scripts/hipo-config.sh` | the one place where paths are resolved |
| `hipocampo.conf.example` | the configuration: copy to `hipocampo.conf` and point it at your folders |
| `settings.example.json` | the hook registration, with `<YOUR_FOLDER>` for this checkout |
| `docs/` | the design (`HIPOCAMPO.md`), the context and compaction facts (`CONTEXTO.md`), the memory format (`MEMORIA.md`), the revolving door (`PORTA.md`), the guard histories (`guardas/`), the trigger channels and sources (`gatilhos/`), the map in five layers (`mapa/`), the area rulers (`oraculo/`), the baton (`mesa/`) — all molds with example content |
| `examples/memory/` | a short `MEMORY.md` and example memories in the real format |
| `skills/desenho/` | the skill of the "desk" session (thinks, designs, writes briefings; does not operate) |
| `guards/memory-guards.sh` | the memory guards (run at commit time) |
| `guards/prove-fixture.sh`, `fixtures/guards/` | the prover: each guard green on its control, red on each named mutant |
| `guards/check-private.py`, `.githooks/pre-commit` | this repository's own guard against private data |
| `tests/smoke.sh` | the reproduction smoke test: fake `HOME`, assemble the example, run every proof |
| `data/` | the aggregated measurements behind the article's figures |
| `docs/FAQ.md` | the questions people asked in public threads, each answered in a few lines and routed to the doc that holds the measurement |

File and folder names are kept in Portuguese where the article and the scripts cite them
(`docs/mapa/`, `docs/gatilhos/`, `docs/mesa/BASTAO.md`, `scripts/gatilho.py`...). Glossary:
*mapa* map · *gatilho* trigger · *oráculo* area ruler · *porta* (revolving) door · *mesa* desk ·
*bastão* baton · *memória* memory · *contexto* context · *janela* window · *teto* ceiling ·
*guarda* guard · *estacionar/retomar* park/resume · *espelho* mirror · *vizinhos* neighbours ·
*horizonte* horizon · *crase* backtick · *controle/mutante* control/mutant · *verde/vermelho* green/red.

## Configuration

Every absolute path the scripts had now comes from one place. Copy `hipocampo.conf.example` to
`hipocampo.conf` and set, at least, `HIPO_WORKDIR` (the folder you open sessions from; Claude Code
names its session store after it). Any key can also be given as an environment variable. Then
replace `<YOUR_FOLDER>` in `settings.example.json` with the absolute path of this checkout and merge
its `hooks` into your `~/.claude/settings.json`.

```
python3 scripts/hipo_config.py        # prints every resolved path: check them before wiring hooks
```

## Step zero: assemble the example

```
cp hipocampo.conf.example hipocampo.conf          # then set HIPO_WORKDIR (and anything else)
python3 scripts/hipo_config.py                    # check the resolved paths
eval "$(python3 scripts/hipo_config.py)"
mkdir -p "$HIPO_MEMORY_DIR" && cp examples/memory/*.md "$HIPO_MEMORY_DIR/"
sed "s#<YOUR_FOLDER>#$PWD#g" settings.example.json > /tmp/hipocampo-settings.json
```

Merge the `hooks` object of `/tmp/hipocampo-settings.json` into your `~/.claude/settings.json`
(append to each event's list; do not replace what you already have). `autoCompactWindow` is a
top-level key of `settings.json`, a sibling of `hooks`, not an entry inside it.
`tests/smoke.sh` does exactly these steps in a temporary folder.

**Minimum and optional hooks.** The minimum set is the map slices (`mapa-hook.sh --parte N` in
`UserPromptSubmit` and in `SessionStart` with matcher `compact`), the index probe
(`memory-cap-probe.py --hook` in `SessionStart`) and the escalator (`gatilho.py` in `PostToolUse`,
`Stop` and `PreToolUse`). Everything else in `settings.example.json` is optional: the area ruler
(`oraculo.py`), the baton (`bastao-entrega.py --emitir` and the `PostCompact` pair), the context
measurer (`contexto-medir.py`), neighbours (`vizinhos-hook.py`), and the touch-time checks
(`horizonte.py`, `guarda-ja-existe.py`, `mapa-orcamento-hook.sh`, `janela-teto.py`,
`guarda-crase.py`).

**Two behaviours to know before wiring them.** `guarda-crase.py` **blocks** (exit 2) a Bash command
whose unquoted heredoc (`<<EOF`) or `-m "..."` message carries a backtick or `$`: quote the
delimiter (`<<'EOF'`) or write the text to a file. The hooks keep small state files (turn counters,
caches, locks) under `HIPO_STATE_DIR`.

## The pieces and the native feature each one uses

(Table 3.1 of the article.)

| piece | native Claude Code feature | what runs underneath |
|---|---|---|
| map in slices | `UserPromptSubmit` (one command per slice) and `SessionStart` with matcher `compact` | `scripts/mapa-hook.sh` and `docs/mapa/*.md` |
| index with a ceiling | native memory: the `MEMORY.md` the runtime loads every turn | `examples/memory/MEMORY.md` and `scripts/memory-cap-probe.py` at `SessionStart` |
| `CLAUDE.md` | nested memory: only arrives when a `Read` touches its folder | a markdown file (yours) |
| area ruler | `UserPromptSubmit` and `PostToolUse` (matcher `Edit\|Write\|Bash`) | `scripts/oraculo.py` and `docs/oraculo/*.md` |
| warn-charge-block escalator | `PostToolUse` (`additionalContext`), `Stop` and `PreToolUse` (`permissionDecision: "ask"`) | `scripts/gatilho.py` and the sources in `docs/gatilhos/` |
| the two revolving doors | escalator source at touch time; ceiling at commit time | `scripts/porta.py`, `scripts/mapa-orcamento-hook.sh`, generated `docs/gatilhos/porta.md` |
| baton | `SessionStart` with matcher `compact`, which delivers a cut emitted by a hook; on manual `/compact`, `PostCompact` | `docs/mesa/BASTAO.md` and `scripts/bastao-entrega.py --emitir` |
| park and resume | editing `MEMORY.md` by command; touch-time notice by the escalator | `scripts/memoria-estaciona.py` |
| post-mortem | the law arrives in the map, by `UserPromptSubmit`; the memory is the native folder | the agent writes |
| compaction ceiling | the `autoCompactWindow` key of `settings.json` | none |
| guards | none: they run in the git pre-commit | `guards/memory-guards.sh` |
| skills | `SKILL.md`, versioned in the repository | `skills/desenho/SKILL.md` |

Also here, used by the pieces above: `scripts/memoria_ids.py`, `memoria-resolve.py`,
`memoria-id-assign.py` (the `[N]` citation table), `guarda-indice-citacao.py`, `guarda-cascata.py`
(index and method-case checks), `memoria-espelho.sh` (mirror of the memory folder into git),
`contexto-medir.py`, `contexto-consumo.py`, `memoria-recall.py` (the measuring instruments),
`janela-teto.py`, `horizonte.py` (window and horizon warnings), `guarda-ja-existe.py` ("does this
rule already exist?"), `guarda-crase.py` (backticks in heredocs), `vizinhos-hook.py` (dirty files
that are not yours).

## The order

(Section 11 of the article.) Each step ends the same way: break the piece on purpose and wait for
the red. Without that, the proof falls behind the population.

1. **Declare the regimes and measure the starting point.** Three lists (resident, paged, interrupt)
   and the count of injected recalls in your transcripts:
   `python3 scripts/memoria-recall.py` over your own store (`HIPO_PROJECT_DIR`). The zero comes
   with its control on the same channel: the script first counts how many times the index
   (`MEMORY.md`) arrived as an `instructions` attachment, and only then prints how many memory
   files arrived the same way. If the index was never seen, it prints no zero: a blind scan and a
   real zero look the same. The honest reading of a zero is "nothing arrived through the channel
   that delivers the index". Files the runtime sends again after a compaction, or when an open file
   changes, are listed apart with their origin (opened before, or no opening found) and do not
   count as recall. `--injecao` prints only this part.
2. **Index, gloss and the ceiling arithmetic.** The native index loads up to 200 lines or 25,000
   units, whichever cuts first. Format: `docs/MEMORIA.md`, example: `examples/memory/`. The index guard's own
   ceiling is 24,576 bytes (24 KiB): UTF-8 bytes are never fewer than UTF-16 units, so a byte ceiling
   under 25,000 keeps a margin below the runtime's unit cut. The probe:
   `python3 scripts/memory-cap-probe.py --selftest`, then registered at `SessionStart`.
   It predicts the cut; it does not measure what the session loaded.
3. **Commit hook and prover.** `bash guards/memory-guards.sh` over your memory folder;
   `bash guards/prove-fixture.sh --todas` proves each guard (the mirror of step 7 is optional: without it
   the index guard warns in yellow; once configured, its absence is red): the control must come out green and
   each copy with a planted defect red, each case in a temporary repository.
4. **Map in slices.** One command per slice, registered in two events: the message sent and the
   restart after compacting. Molds in `docs/mapa/`; `bash scripts/mapa-hook.sh --selftest`.
5. **The revolving door of the layers**, which blocks the commit that grows the resident layer
   without paying: `bash guards/door-guard.sh` (the map past its slice budget; wired into
   `.githooks/pre-commit`) and the index guard in `guards/memory-guards.sh` (the index past
   24,576 B or 200 lines). What leaves and to where: `docs/PORTA.md`, `python3 scripts/porta.py --seco`.
6. **The escalator**, starting with one real debt of yours: a source in `docs/gatilhos/`,
   `python3 scripts/gatilho.py --selftest`.
7. **The optional ones:** park and resume (`scripts/memoria-estaciona.py --selftest`), window warning
   (`scripts/janela-teto.py`), the baton (`docs/mesa/`, `scripts/bastao-entrega.py`), and the mirror
   of the memory into git (`scripts/memoria-espelho.sh`, run by your scheduler).

The registration of step 4 with two slices (each extra slice is one more line in each event):

```json
{ "hooks": {
  "UserPromptSubmit": [{ "hooks": [
    { "type": "command", "command": "<YOUR_FOLDER>/scripts/mapa-hook.sh --parte 1", "timeout": 10 },
    { "type": "command", "command": "<YOUR_FOLDER>/scripts/mapa-hook.sh --parte 2", "timeout": 10 } ]}],
  "SessionStart": [{ "matcher": "compact", "hooks": [
    { "type": "command", "command": "<YOUR_FOLDER>/scripts/mapa-hook.sh --parte 1", "timeout": 10 },
    { "type": "command", "command": "<YOUR_FOLDER>/scripts/mapa-hook.sh --parte 2", "timeout": 10 } ]}]
}}
```

## The proof that it arrived

`hook success` says the command ran without error, with its output whole or cut. The delivery
proof compares what the command emitted with what the transcript recorded as model context, byte by
byte. Run it in a new session, after `/compact`, and after every Claude Code update, because the
channels that accept context change with the version. For the index, the proof is finding its text
in the first message of the transcript. It proves delivery; whether the model used what it
received, it does not measure.

(Table 11.1 of the article.)

| piece | native feature | proof | measured trap |
|---|---|---|---|
| index with gloss | `MEMORY.md` | the index text in the transcript's first message | cuts at 200 lines or 25,000 units, whichever comes first, and the binding limit changes over time; the index is per project folder, and a session opened in another folder does not load it |
| paged memory | files next to the index, opened by `Read` | openings counted in the transcripts (`memoria-recall.py`) | no automatic recall (nothing arrives through the channel that delivers the index); after a compaction the runtime may send again a memory already opened; fewer than half of the memories were ever opened |
| map in slices | `UserPromptSubmit` and `SessionStart` (`compact`) hooks | emitted × transcript, byte by byte | 10,000-unit cap per registered command; above it the window receives a preview of the first 2,000 units (about 2 KB) |
| resume after compacting | `SessionStart` with matcher `compact` | the same comparison, at the first compaction | `PostCompact` creates no context attachment: its output only arrives through the echo of a manual `/compact`, never on automatic compaction |
| contract outside `CLAUDE.md` | `CLAUDE.md` | the memory attachment in the transcript | in a subfolder it only arrives through `Read` |
| escalator | `PostToolUse` warns, `Stop` charges, `PreToolUse` blocks | tool denied on the 3rd ride | without it, the written list of pending items was almost never paid |
| guards | git commit hook | green control and red defective copy | the new guard is born before its proof |
| compaction ceiling | `autoCompactWindow` in settings | the size before the cut, in the record of each compaction | a session opened before the change still passes the new ceiling |
| baton | `SessionStart` (`compact`), with a cut emitted by a hook; on manual `/compact`, the whole file through the `PostCompact` echo | live state inside what arrived (`bastao-entrega.py`) | the fixed head of the file filled the preview, and the state did not arrive until the fix |

## Reproduce it here

```
bash tests/smoke.sh
```

It builds a temporary folder with a fake `HOME`, assembles the example following this README
(configuration, example memory, settings with `<YOUR_FOLDER>` filled in), runs each example hook and
checks what it emits, runs each memory guard green on the example and red on its mutant, and runs
every selftest. Every `.py` compiles and every `.sh` parses.

## This repository's own guard

`guards/check-private.py` refuses a commit that carries private data: IP addresses, home folders,
e-mails, UUIDs, tokens, MAC addresses, document ids, and a list of private terms and regexes
(`re:name=<label>:<regex>`) that lives **outside** the tracked tree (`.private-terms`, ignored by
git — a committed list of private words or codename formats would publish them).
`python3 guards/check-private.py --selftest` runs 3 controls: clean folder green; planted IP, home
folder and host alias red, each named; a labelled regex term red under its own label. Enable
the hook with `git config core.hooksPath .githooks`.

## Not included

The lab-specific pieces the article mentions but that only serve that lab: the production-touch
guard, the game-server and core guards, the scoreboard and claim-proving scripts, the full CI battery
(74 guards; only the memory family is here), the routing of guards by radius, the divergence
ledger guard, and the figure generator (it reads the article's working drafts and private history).
The real memories, map, baton and rulers stay private.

## Known limits

- The numbers in `docs/` come from one installation where Claude Code runs from the filesystem
  root (`/`), not from a project folder, and most of the files worked on live on other hosts,
  reached over ssh. Two things follow. From `/`, every project's `CLAUDE.md` is a nested one and
  loads only when something under it is read ([`CONTEXTO.md` §2.2](docs/CONTEXTO.md)); a session
  started inside the repository gets it at startup. And one memory index serves every project, so
  it is crowded: that is why projects are parked out of it ([`MEMORIA.md` §5](docs/MEMORIA.md)),
  and why the triggers match the Bash command text as well as `file_path`, since an edit over ssh
  never passes through a local `Read` (`alvo_do_hook` in [`gatilho.py`](scripts/gatilho.py)).
  Rates measured here are rates for that setup.
- Selftests whose cases need a population a fresh clone does not have **skip** those cases and
  say so (`skipped: needs ...`), instead of failing: `memoria-recall.py` (a `user_profile.md` memory
  and real transcripts; 19 ok · 5 skipped in a fresh clone), `contexto-consumo.py` (real subagent
  transcripts; 4 ok · 1 skipped), `guarda-ja-existe.py` (more than 100 rule blocks; 21 ok · 1
  skipped), `horizonte.py` (a git repository with a `memoria/` folder imported in one commit and
  `docs/` grown commit by commit; 5 ok · 3 skipped). A skipped case proves nothing: run it again
  once your own store has the population.
- `bastao-entrega.py --validar` compares its preview emulation against real previews and exits 2,
  saying so, when there are none yet.
- `contexto-consumo.py --prova-corte` needs a baseline: `--base CHARS`, or two listings in your own
  recent sessions; `--prefixos` names the plugin prefixes to count.
- Some identifiers, frontmatter keys (`escopo`, `prova`, `regra`), verdict tokens (`VERDE`,
  `SEM_ESTADO`, `verde`, `vermelho`) and the column names in `data/` stay in Portuguese: code and
  fixtures compare them byte for byte. The glossary above covers the file names.
- The article's figure of the seven steps (section 11) is not reproduced here; the order is given
  as text above.

## License

MIT, see `LICENSE`.
