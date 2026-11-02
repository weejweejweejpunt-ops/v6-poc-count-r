"""Module for MockNetwork tests: this algorithm plus the standard Parquet extraction function.

In a real network the data-extraction step is done by the separate ``extract-basics`` algorithm;
the mock network needs both in the same module.
"""

from vantage6.algorithm.data_extraction import read_parquet  # noqa: F401
from v6_poc_count_r import *  # noqa: F401,F403
