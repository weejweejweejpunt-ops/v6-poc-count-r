"""Run the R tests (tests/testthat) with testthat. Skipped when R or testthat is not available."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
RSCRIPT = os.environ.get("RSCRIPT") or shutil.which("Rscript")


@pytest.mark.skipif(not RSCRIPT, reason="Rscript not found (set RSCRIPT)")
def test_r_unit_tests_pass():
    check = subprocess.run(
        [RSCRIPT, "--vanilla", "-e", "quit(status = !requireNamespace('testthat', quietly = TRUE))"],
        capture_output=True,
        check=False,
    )
    if check.returncode != 0:
        pytest.skip("the R package testthat is not installed")
    completed = subprocess.run(
        [
            RSCRIPT,
            "--vanilla",
            "-e",
            "testthat::test_dir('tests/testthat', reporter = 'summary', stop_on_failure = TRUE)",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
