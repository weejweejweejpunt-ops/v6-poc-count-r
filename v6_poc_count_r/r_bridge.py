"""Call the R code that does the counting.

This module contains no counting logic: it writes the input for R to a temporary file, runs ``r/run.R`` with
``Rscript`` and reads the JSON that R prints. It has no vantage6 imports, so it can be tested on its own.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

R_SCRIPT = Path(__file__).parent / "r" / "run.R"


def _rscript() -> str:
    """The Rscript executable: the RSCRIPT environment variable, else the one on the PATH."""
    executable = os.environ.get("RSCRIPT") or shutil.which("Rscript")
    if not executable:
        raise RuntimeError("Rscript was not found. Install R, or set the RSCRIPT environment variable.")
    return executable


def _workdir() -> tempfile.TemporaryDirectory:
    """A temporary folder that disappears afterwards; the session folder if the default one is not writable."""
    try:
        return tempfile.TemporaryDirectory()
    except OSError:
        folder = os.environ.get("SESSION_FOLDER")
        if not folder:
            raise
        return tempfile.TemporaryDirectory(dir=folder)


def _run(*arguments: str) -> dict:
    completed = subprocess.run(
        [_rscript(), "--vanilla", str(R_SCRIPT), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        # R reports its own error message, for example "Column 'x' not found in the dataframe"
        raise ValueError(completed.stderr.strip() or "The R script failed without a message")
    return json.loads(completed.stdout)


def count_values(df: pd.DataFrame, column_name: str, min_cell_size: int) -> dict:
    """Let R count the rows of a dataframe per value of one column (``count_values`` in counting.R)."""
    with _workdir() as folder:
        path = Path(folder) / "dataframe.csv"
        df.to_csv(path, index=False, na_rep="")
        return _run("count", str(path), column_name, str(min_cell_size))


def combine_counts(results: list[dict], column_name: str) -> dict:
    """Let R add up the results of all nodes (``combine_counts`` in counting.R)."""
    with _workdir() as folder:
        path = Path(folder) / "results.json"
        path.write_text(json.dumps(results), encoding="utf-8")
        return _run("combine", str(path), column_name)
