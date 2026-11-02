"""Run the whole algorithm (central + partial, counting in R) in vantage6's MockNetwork with real Parquet files.

Skipped when vantage6 or Rscript (with jsonlite) is not installed. It uses the same ``read_parquet`` extraction
function as the ``extract-basics`` algorithm and the numbers of the POC nodes (1342 and 1352 persons).
"""

import os
import shutil
import subprocess

import pandas as pd
import pytest

pytest.importorskip("vantage6.algorithm.mock.network")
from vantage6.algorithm.mock.network import MockNetwork  # noqa: E402

_RSCRIPT = os.environ.get("RSCRIPT") or shutil.which("Rscript")
if not _RSCRIPT or subprocess.run(
    [_RSCRIPT, "--vanilla", "-e", "quit(status = !requireNamespace('jsonlite', quietly = TRUE))"],
    capture_output=True,
    check=False,
).returncode:
    pytest.skip("Rscript with the R package jsonlite not found (set RSCRIPT)", allow_module_level=True)


def _persons(path, male: int, female: int, other=()):
    ids = [8507] * male + [8532] * female + list(other)
    pd.DataFrame({"person_id": range(len(ids)), "gender_concept_id": ids}).to_parquet(path)
    return {"person": {"database": str(path), "db_type": "parquet"}}


def _run(tmp_path, arguments=None, nodes=((653, 689, ()), (668, 684, ()))):
    datasets = [_persons(tmp_path / f"p{i}.parquet", m, f, o) for i, (m, f, o) in enumerate(nodes)]
    network = MockNetwork(module_name="_mock_algorithm", datasets=datasets)
    client = network.user_client
    dataframe = client.dataframe.create(label="person", method="read_parquet", arguments={}, name="person")
    task = client.task.create(
        method="central_count",
        organizations=[network.organization_ids[0]],
        arguments=arguments or {},
        databases=[{"dataframe_id": dataframe["id"]}],
        action="central_compute",
    )
    return client.result.from_task(task["id"])[0]


def test_central_count_per_gender_over_two_nodes(tmp_path):
    result = _run(tmp_path)
    assert result["total"] == 2694
    assert result["organizations"] == 2
    assert result["table"] == [
        {"value": "8507", "label": "MALE", "count": 1321},
        {"value": "8532", "label": "FEMALE", "count": 1373},
    ]


def test_central_count_other_column(tmp_path):
    result = _run(tmp_path, arguments={"column_name": "person_id"}, nodes=((1, 1, ()), (1, 0, ())))
    assert result["total"] == 3
    assert {row["value"]: row["count"] for row in result["table"]} == {"0": 2, "1": 1}


def test_min_cell_size_suppresses_a_small_cell(tmp_path):
    # the second node has only 2 persons with the "other" gender: suppressed at that node, so unknown in the total
    result = _run(tmp_path, arguments={"min_cell_size": 5}, nodes=((20, 20, ()), (20, 20, [8521, 8521])))
    counts = {row["label"]: row["count"] for row in result["table"]}
    assert counts["MALE"] == 40
    assert counts["FEMALE"] == 40
    assert counts["OTHER"] is None
