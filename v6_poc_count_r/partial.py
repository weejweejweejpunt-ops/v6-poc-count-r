import pandas as pd
from vantage6.algorithm.decorator.action import federated
from vantage6.algorithm.decorator.data import dataframe
from vantage6.common import info

from . import r_bridge

GENDER_COLUMN = "gender_concept_id"


@federated
@dataframe(1)
def partial_count(
    df1: pd.DataFrame, column_name: str = GENDER_COLUMN, min_cell_size: int = 0
) -> dict:
    """Count the rows of this node's dataframe per value of a column (the counting is done in R).

    Parameters
    ----------
    df1 : pandas.DataFrame
        Dataframe of this node (for example the OMOP ``person`` table).
    column_name : str
        Column to count the values of. Default ``gender_concept_id``.
    min_cell_size : int
        Values that occur fewer times are reported as ``None``; ``0`` switches this off.

    Returns
    -------
    dict
        ``{"total": <rows>, "counts": {<value>: <count or None>}}``
    """
    info(f"Counting rows per value of column {column_name} (in R)")
    return r_bridge.count_values(df1, column_name, min_cell_size)
