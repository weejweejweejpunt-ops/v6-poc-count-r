from vantage6.algorithm.client import AlgorithmClient
from vantage6.algorithm.decorator.action import central
from vantage6.algorithm.decorator.algorithm_client import algorithm_client
from vantage6.common import info

from . import r_bridge
from .partial import GENDER_COLUMN


@central
@algorithm_client
def central_count(
    client: AlgorithmClient,
    column_name: str = GENDER_COLUMN,
    min_cell_size: int = 0,
) -> dict:
    """Count the rows over all nodes per value of a column (adding up is done in R).

    Asks every organization in the collaboration for its own counts
    (``partial_count``) and lets R add them up.

    Parameters
    ----------
    client : AlgorithmClient
        Injected by vantage6.
    column_name : str
        Column to count the values of. Default ``gender_concept_id``.
    min_cell_size : int
        Values that occur fewer times at a node are reported as ``None``; ``0``
        switches this off.

    Returns
    -------
    dict
        ``{"total": <rows>, "organizations": <nodes>, "table": [{"value", "label",
        "count"}, ...]}``
    """
    info("Collecting participating organizations")
    organizations = client.organization.list()
    ids = [organization.get("id") for organization in organizations]

    info("Requesting partial counts")
    task = client.task.create(
        method="partial_count",
        arguments={"column_name": column_name, "min_cell_size": min_cell_size},
        organizations=ids,
        name="partial-count",
        description="Count per value at each organization",
    )

    info("Waiting for results")
    results = client.wait_for_results(task_id=task.get("id"))
    info("Partial results are in; adding them up (in R)")
    return r_bridge.combine_counts(results, column_name)
