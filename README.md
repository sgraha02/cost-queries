# cost-queries

Ad hoc cost/consumption queries, version-controlled and promoted from a dev
workspace to a customer workspace via Databricks **Git folders**.

## Workflow

GitHub is the sync layer between two isolated workspaces:

1. **Dev (employee workspace)** — Git folder tracks the `dev` branch. Iterate on
   queries here, then commit + push to `dev`.
2. **Promote** — open a PR / merge `dev` → `main` when a query is ready.
3. **Prod (customer VDI workspace)** — Git folder tracks `main`. Pull to pick up
   promoted queries. Treat as read-only; don't edit here.

## Parameterization

Queries must not hardcode catalog/schema/warehouse, since dev and prod differ.
Run each query from a notebook that defines widgets, and reference them in SQL:

```sql
-- in a SQL notebook cell, after widgets are created
SELECT * FROM ${catalog}.${schema}.some_table
```

Set the widget defaults per workspace (dev vs. customer) so the same file runs
correctly in both places.

## Layout

- `queries/` — the SQL / notebook queries
- `ci/` — CI helpers (`notebook_sql.py` SQL extractor, `dryrun.py` EXPLAIN check)
- `.github/workflows/ci.yml` — GitHub Actions pipeline

## CI

Runs on PRs into `main` and pushes to `dev`:

1. **Lint** — `notebook_sql.py` strips the `-- MAGIC` / `-- COMMAND` notebook
   markers and extracts the raw SQL cells, then `sqlfluff` lints them. We lint
   the *extracted* SQL (not the notebook) because sqlfluff misreads notebook
   markers. Note: `sqlfluff fix` is **not** safe on notebook-source files — it
   deletes `-- COMMAND ----------` cell separators. CI only ever runs `lint`.
2. **dev dry-run** — `dryrun.py` runs `EXPLAIN` on each statement against a dev
   SQL warehouse, catching missing columns / tables / syntax errors before
   promotion. `:param` markers are bound to sample values.

The dry-run reads three secrets from the `dev` GitHub environment:
`DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_WAREHOUSE_ID`. Until those are
set the dry-run self-skips with a warning; lint still runs. The customer VDI is
never contacted by CI — promotion into it stays a manual Git-folder Pull of
`main`.
