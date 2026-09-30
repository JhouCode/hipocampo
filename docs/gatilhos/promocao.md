# Source `promocao` -- triggers that only arm when a build goes to production

> **The defect this fixes:** items that matched a FILE fired on every touch of it -- including a
> documentation cleanup, where the release step they asked for would be the ERROR. A right warning
> at the wrong time is noise, and noise trains people to ignore.
>
> **The rule of this source:** `when it matches` recognizes the **ACT of releasing**, never the
> file the release touches. Saving, committing, refactoring and documenting do **not** arm anything
> here.

## What counts as a release -- and that is why the predicates are these

| signal | why |
|---|---|
| `release/` | the directory the release script writes the artifact into; it is only written when releasing |
| `deploy.sh --production` | the only invocation that reaches production |

| id | when it matches | what to say | NEXT STEP | step | rides |
|---|---|---|---|---|---|
| PROMO-01 | `(deploy\.sh --production\|(^\|/)release/)` | Every build that reaches production updates `docs/VERSIONS.md` in the same commit -- checksum, date and the commit it came from | Edit the artifact rows in `docs/VERSIONS.md` from the built file, not from memory, and commit them with the release | RULE | 0 |
| PROMO-02 | `deploy\.sh --production` | After a release, the off-site backup still describes the previous version until the nightly run | Run the on-demand backup sync right after the health check passes | RULE | 0 |

## What does NOT live here

Code debt, file dependencies and duplication stay in `backlog.md`, `dependencia.md` and
`duplicado.md` -- **they hold at the touch**, which is exactly the opposite of these.
