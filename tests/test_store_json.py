"""Check algorithm_store.json against the real functions in the code, without importing vantage6."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
STORE = json.loads((ROOT / "algorithm_store.json").read_text(encoding="utf-8"))

# Values the store accepts (vantage6 5.0.x: AlgorithmStepType, AlgorithmArgumentType, VisualizationType, Partitioning).
STEP_TYPES = {"data_extraction", "preprocessing", "federated_compute", "central_compute", "postprocessing"}
ARGUMENT_TYPES = {
    "column", "column_list", "string", "string_list", "integer", "integer_list", "float",
    "float_list", "boolean", "json", "organization", "organization_list",
}
VISUALIZATION_TYPES = {"table", "line"}
# Parameters that vantage6 injects; they are not arguments of the user.
INJECTED = {"client", "df1", "df2", "df3"}
TOP_LEVEL = {
    "name", "image", "vantage6_version", "code_url", "documentation_url", "partitioning",
    "description", "functions", "submission_comments",
}


def _functions_in_code() -> dict[str, dict]:
    """Function name -> {parameter name: default value as string or None}."""
    found = {}
    for path in (ROOT / "v6_poc_count_r").glob("*.py"):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not isinstance(node, ast.FunctionDef):
                continue
            args = node.args
            names = [a.arg for a in args.args]
            defaults = [None] * (len(names) - len(args.defaults)) + [
                ast.unparse(d) for d in args.defaults
            ]
            found[node.name] = dict(zip(names, defaults))
    return found


def test_top_level_fields():
    assert set(STORE) <= TOP_LEVEL
    for field in ("name", "image", "vantage6_version", "code_url", "partitioning", "functions"):
        assert STORE[field]
    assert STORE["partitioning"] in {"horizontal", "vertical"}
    assert ":" not in STORE["image"].split("/")[-1], "image without tag: the store resolves the tag and digest"


def test_functions_exist_and_arguments_match_the_code():
    code = _functions_in_code()
    for function in STORE["functions"]:
        assert function["step_type"] in STEP_TYPES
        assert function["name"] in code, f"{function['name']} not found in the code"
        parameters = {k: v for k, v in code[function["name"]].items() if k not in INJECTED}
        declared = {a["name"] for a in function["arguments"]}
        assert declared == set(parameters), f"{function['name']}: arguments differ from the code"


def test_arguments_are_valid_for_the_store():
    code = _functions_in_code()
    for function in STORE["functions"]:
        for argument in function["arguments"]:
            assert argument["type"] in ARGUMENT_TYPES
            assert isinstance(argument.get("is_frontend_only", False), bool)
            if "default_value" in argument:
                assert argument["has_default_value"] is True
                assert isinstance(argument["default_value"], str), "default values are strings in the store"
                if argument["type"] == "integer":
                    int(argument["default_value"])
            if argument.get("has_default_value"):
                code_default = code[function["name"]][argument["name"]]
                assert code_default is not None, f"{argument['name']} has a default in the JSON but not in the code"


def test_visualizations_are_valid():
    for function in STORE["functions"]:
        for visualization in function["ui_visualizations"]:
            assert visualization["type"] in VISUALIZATION_TYPES
            location = visualization["schema"].get("location", [])
            assert all(isinstance(part, str) for part in location)


def test_central_function_table_matches_what_the_code_returns():
    """The table visualization points at result['table'], which combine_counts (in R) produces."""
    central = next(f for f in STORE["functions"] if f["step_type"] == "central_compute")
    assert central["ui_visualizations"][0]["schema"]["location"] == ["table"]
    source = (ROOT / "v6_poc_count_r" / "r" / "counting.R").read_text(encoding="utf-8")
    assert "table = rows" in source
