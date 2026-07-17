"""Dry-run each SQL statement in the given notebooks against a dev SQL warehouse.

Runs `EXPLAIN <statement>`, which compiles the query plan (resolving tables and
columns) without materializing results — a cheap way to catch typos, missing
columns, and syntax errors before a query is promoted to main. The :param
markers are bound to harmless sample values so the plan can compile.

Requires DATABRICKS_HOST, DATABRICKS_TOKEN, and DATABRICKS_WAREHOUSE_ID.
"""

import os
import re
import sys

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem

from notebook_sql import extract_statements

# Values only need to type-check; EXPLAIN never reads data.
SAMPLE_PARAMS = {
    "warehouse_id": "0",
    "start_ts": "2000-01-01 00:00:00",
    "end_ts": "2000-01-02 00:00:00",
}


def _params_for(stmt: str) -> list[StatementParameterListItem]:
    return [
        StatementParameterListItem(name=name, value=value)
        for name, value in SAMPLE_PARAMS.items()
        if re.search(rf":{name}\b", stmt)
    ]


def main(paths: list[str]) -> int:
    client = WorkspaceClient()
    warehouse_id = os.environ["DATABRICKS_WAREHOUSE_ID"]
    failures = 0

    for path in paths:
        for i, stmt in enumerate(extract_statements(path), start=1):
            label = f"{path} [stmt {i}]"
            resp = client.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=f"EXPLAIN {stmt}",
                parameters=_params_for(stmt),
                wait_timeout="30s",
            )
            state = resp.status.state.value if resp.status and resp.status.state else "UNKNOWN"
            if state == "SUCCEEDED":
                print(f"PASS  {label}")
            else:
                detail = (
                    resp.status.error.message
                    if resp.status and resp.status.error
                    else state
                )
                print(f"FAIL  {label}: {detail}")
                failures += 1

    if failures:
        print(f"\n{failures} statement(s) failed dry-run.")
        return 1
    print("\nAll statements passed dry-run.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
