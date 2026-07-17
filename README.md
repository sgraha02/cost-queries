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
