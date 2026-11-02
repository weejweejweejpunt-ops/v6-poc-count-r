"""The Python side of the R call: r_bridge writes the input, runs Rscript and reads the JSON.

r_bridge.py is loaded directly: importing the package would import vantage6 (installed in the image, not needed here).
Skipped when Rscript (or the R package jsonlite) is not available.
"""

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "r_bridge", Path(__file__).parent.parent / "v6_poc_count_r" / "r_bridge.py"
)
r_bridge = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(r_bridge)

RSCRIPT = os.environ.get("RSCRIPT") or shutil.which("Rscript")


def _has_jsonlite() -> bool:
    if not RSCRIPT:
        return False
    check = subprocess.run(
        [RSCRIPT, "--vanilla", "-e", "quit(status = !requireNamespace('jsonlite', quietly = TRUE))"],
        capture_output=True,
        check=False,
    )
    return check.returncode == 0


pytestmark = pytest.mark.skipif(not _has_jsonlite(), reason="Rscript with the R package jsonlite not found (set RSCRIPT)")


def _persons(male: int, female: int, other=()) -> pd.DataFrame:
    ids = [8507] * male + [8532] * female + list(other)
    return pd.DataFrame({"person_id": range(len(ids)), "gender_concept_id": ids})


def test_count_values_per_gender():
    result = r_bridge.count_values(_persons(653, 689), "gender_concept_id", 0)
    assert result == {"total": 1342, "counts": {"8507": 653, "8532": 689}}


def test_a_float_column_with_missing_values():
    # pandas writes 1.0 and an empty cell for NaN; R reports the keys as 1, 2 and (missing)
    df = pd.DataFrame({"x": [1.0, 1.0, 2.0, np.nan]})
    result = r_bridge.count_values(df, "x", 0)
    assert result == {"total": 4, "counts": {"1": 2, "2": 1, "(missing)": 1}}


def test_empty_dataframe():
    result = r_bridge.count_values(pd.DataFrame({"gender_concept_id": []}), "gender_concept_id", 0)
    assert result == {"total": 0, "counts": {}}


def test_text_with_commas_quotes_and_accents():
    df = pd.DataFrame({"x": ["a,b", 'say "hi"', "café", "a,b"]})
    result = r_bridge.count_values(df, "x", 0)
    assert result["counts"] == {"a,b": 2, 'say "hi"': 1, "café": 1}


def test_unknown_column_is_a_value_error_with_the_r_message():
    with pytest.raises(ValueError, match="not found in the dataframe"):
        r_bridge.count_values(_persons(1, 1), "nope", 0)


def test_min_cell_size_masks_small_cells_as_null():
    result = r_bridge.count_values(_persons(10, 3), "gender_concept_id", 5)
    assert result["counts"] == {"8507": 10, "8532": None}


def test_min_cell_size_refuses_tiny_dataframe():
    with pytest.raises(ValueError, match="fewer rows"):
        r_bridge.count_values(_persons(2, 1), "gender_concept_id", 5)


def test_combine_counts_matches_poc_data():
    vm2 = r_bridge.count_values(_persons(653, 689), "gender_concept_id", 0)
    vm3 = r_bridge.count_values(_persons(668, 684), "gender_concept_id", 0)
    combined = r_bridge.combine_counts([vm2, vm3], "gender_concept_id")
    assert combined == {
        "total": 2694,
        "organizations": 2,
        "table": [
            {"value": "8507", "label": "MALE", "count": 1321},
            {"value": "8532", "label": "FEMALE", "count": 1373},
        ],
    }


def test_combine_counts_suppressed_cell_stays_null():
    a = {"total": 10, "counts": {"8507": 7, "8532": None}}
    b = {"total": 20, "counts": {"8507": 5, "8532": 15}}
    combined = r_bridge.combine_counts([a, b], "gender_concept_id")
    assert {row["value"]: row["count"] for row in combined["table"]} == {"8507": 12, "8532": None}
    assert combined["total"] == 30


def test_missing_rscript_gives_a_clear_error(monkeypatch):
    monkeypatch.setenv("RSCRIPT", "")
    monkeypatch.setattr(r_bridge.shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="Rscript was not found"):
        r_bridge.count_values(_persons(1, 1), "gender_concept_id", 0)
