# data/ -- the aggregated measurements behind the article's figures

These are the aggregated tables the article's figures and tables were drawn from. They are
here so a reader can check a number without trusting the prose. They are not a benchmark and
they describe one installation (one operator, one machine set, July to September 2026).

What is NOT here, on purpose: the per-request, per-message and per-session tables (they carry
session ids, message text or conversation titles), and the figure generator (it reads the
article's working drafts and the private repository's git history, so it does not run outside
it). Two per-event tables ship with the session id column removed: `compactacoes.csv` and
`ciclos_toques.csv`. In `hooks_por_evento.csv` the absolute folder is written `<YOUR_FOLDER>/`
and one lab-only hook is named `lab-only-production-guard`. The two `*_excl_article_session`
files are the same tables without the session in which the article itself was written.

Time of day is not published. Every timestamp is reduced to its date (`YYYY-MM-DD`): the columns
once named `ts` (and `ts_brt` in `bastao/`) are now `date`, and `inicio_ciclo` keeps its name
but holds a date. Dates of per-event rows (`compactacoes`, `ciclos_toques`,
`bastao/previa_entregas`) are UTC; dates of the git series are the commit's local date. In
`audio_resumo.csv` the first and last request of the session are reduced to `first_date` and
`last_date`. The commit hashes of the private repository are gone: in the git series
(`guardas_serie`, `indice_pool`, `indice_serie_git`, `oraculo_bytes_serie`,
`regua_extraida_serie`, `bastao/git_versoes`, `bastao/previa_git`) the `commit` / `versao` column
is replaced by `n`, a sequential index 1..N in file order (oldest first, one row per commit). Free-text cells (descriptions, phases, populations, metric names) are
translated to English; every number is unchanged.

Column names are kept as measured (Portuguese), except `date` and `n`. The dictionary below covers
the recurring ones.

| column | meaning |
|---|---|
| `date`, `dia`, `semana`, `semana_inicio` | date of the event (no time of day), day, ISO week, first day of the week |
| `req`, `requisicoes` | model requests |
| `sessoes` | sessions (conversations) |
| `ctx_*` | context size of a request, in tokens (input + cache read + cache creation) |
| `out_*` | output tokens |
| `cache_read_pct`, `cache_creation_pct`, `novo_input_pct` | share of the input served from cache, written to cache, or new |
| `abertura`, `1a_req` | the opening: the first request of a session |
| `pre`, `post` (`preTokens`, `postTokens`) | context size before and after a compaction |
| `trigger` | `manual` (`/compact`) or `auto` |
| `toques_no_ciclo` | tool calls ("touches") between two compactations |
| `falas`, `citadas`, `literais`, `evaporadas` | operator messages before a compaction; how many the summary cited, quoted literally, or lost |
| `msgs_dele`, `mensagens_dele` | messages written by the operator |
| `lado` | `before` / `after` a change (the date in `marco`) |
| `fase` | the four phases F0 before, F1 construction, F2 consolidated, F3 window+hipocampo |
| `C_llm`, `R_llm`, `F_llm` | operator messages labelled by a model as Correction, Repetition (re-teaching), Failure report |
| `corr_regex` | corrections found by a regular expression (the cheaper, noisier label) |
| `n` | sequential index of a commit of the private repository, 1..N in file order (the series follow the git history; hashes are not published) |
| `linhas`, `unidades`, `unidades_utf16`, `bytes` | size of the memory index in lines, UTF-16 units and bytes |
| `citacoes_N`, `ids_distintos`, `arquivos_memoria` | citations `[N]` in the index, distinct ids, memory files |
| `folga_*`, `vinculante` | headroom to the 200-line / 25,000-unit cap, and which of the two binds |
| `guardas`, `provadas_falhando` | guards in the battery, and how many were proven failing |
| `cpp`, `db`, `scripts`, `build`, `_comum` | the area rulers of the private repository (bytes or extracted rule size) |
| `persistido` | the hook output passed the 10,000-unit cap and only its preview reached the context |
| `cabeca_fixa_bytes`, `estado_vivo_*` | the baton's fixed head, and where its live state starts / how much of it the preview carried |

Which files feed a figure (checked against the figure generator): `hooks_por_evento` (section 3);
`indice_serie_git`, `indice_pool`, `regua_extraida_serie` (5.3); `bastao/git_diario`,
`bastao/previa_git`, `bastao/previa_entregas` (5.4); `custo_semanal_excl_article_session`,
`custo_fases_excl_article_session` (5.7); `audio_resumo` (6.1); and, in figures without a section
tag, `compactacoes`, `ciclos_toques`, `efeito_janela`, `guardas_serie`, `chats_por_dia`. The other
files back numbers quoted in the text and tables.
