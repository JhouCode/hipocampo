# Front `db` — the ruler that comes BEFORE

<!-- when-matches: \bmysql\b|\bmariadb\b|\bpsql\b|\bpostgres\w*|\bsql\b|\bselect\b|\binsert\b|\bupdate\s+\w+\s+set\b|\bdelete\s+from\b|\btable\b|\bschema\b|\bquery\b|\bdump\b|\bmigration\w* -->
<!-- when-touches: \bmysql\b|\bmysqldump\b|\bpsql\b|\.sql\b|\bSELECT\s|\bINSERT\s+INTO\b|\bUPDATE\s+\w+\s+SET\b|\bDELETE\s+FROM\b -->

> Example ruler (mold). The classic transport error lives here: double quotes inside single quotes
> inside `ssh`.

## PREMISES

### 1 · Blast radius before DELETE
Count the rows the `WHERE` selects with a `SELECT COUNT(*)` first, and state the number.
**Source:** `docs/mapa/1_CONTRATO.md` (What I do NOT do without the owner).

### 2 · A query through ssh goes in a file, not in nested quotes
**Source:** the shell quoting rules — each hop strips one level.
**What to do:** write the SQL to a file and pipe it: `ssh host 'psql' < query.sql`.
