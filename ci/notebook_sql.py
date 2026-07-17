"""Extract runnable SQL statements from Databricks SQL notebook-source files.

Databricks notebooks store cells as `.sql` with `-- COMMAND ----------` cell
separators and `-- MAGIC` prefixes for non-SQL cells (markdown, python). Neither
sqlfluff nor the SQL Statement Execution API understand those markers, so this
module strips them and returns just the executable SQL statements. Widget
management statements (CREATE/REMOVE WIDGET) are dropped since they only exist to
back the :param markers.
"""

import argparse
import pathlib
import re
import sys

_COMMAND_SEP = re.compile(r"^--\s*COMMAND\s*-+\s*$")
_WIDGET_STMT = re.compile(r"(?is)^\s*(CREATE|REMOVE)\s+WIDGET\b")
_LINE_COMMENT = re.compile(r"--.*$", re.MULTILINE)
_HEADER = "-- Databricks notebook source"


def _uncommented(stmt: str) -> str:
    """Strip -- line comments, for deciding what a fragment really is."""
    return _LINE_COMMENT.sub("", stmt).strip()


def extract_statements(path: str | pathlib.Path) -> list[str]:
    text = pathlib.Path(path).read_text()
    cells: list[list[str]] = [[]]
    for line in text.splitlines():
        if _COMMAND_SEP.match(line):
            cells.append([])
        else:
            cells[-1].append(line)

    statements: list[str] = []
    for cell in cells:
        code = "\n".join(
            ln
            for ln in cell
            if not ln.strip().startswith("-- MAGIC") and ln.strip() != _HEADER
        )
        for raw in code.split(";"):
            stmt = raw.strip()
            probe = _uncommented(stmt)
            if probe and not _WIDGET_STMT.match(probe):
                statements.append(stmt)
    return statements


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    parser.add_argument(
        "--emit-dir",
        help="Write each extracted statement to <dir>/<file>_<n>.sql for linting.",
    )
    args = parser.parse_args()

    for f in args.files:
        statements = extract_statements(f)
        if args.emit_dir:
            out = pathlib.Path(args.emit_dir)
            out.mkdir(parents=True, exist_ok=True)
            stem = pathlib.Path(f).stem
            for i, stmt in enumerate(statements, 1):
                (out / f"{stem}_{i}.sql").write_text(stmt + "\n")
        else:
            for stmt in statements:
                print(stmt + "\n;")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
