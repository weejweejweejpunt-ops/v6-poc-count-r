# v6-poc-count-r

A small [vantage6](https://vantage6.ai) v5 algorithm for a proof of concept: **count the rows of a dataframe per value of one
column over all participating nodes, with the counting done in R**. By default it counts persons per gender
(`gender_concept_id` of the OMOP `person` table) and labels the OMOP gender concepts (8507 = MALE, 8532 = FEMALE, ...).

It is the R variant of [v6-poc-count-py](https://github.com/weejweejweejpunt-ops/v6-poc-count-py): same functions, same arguments, same
result. Use the two side by side to compare how an R algorithm fits in vantage6.

Only counts leave a node, never rows. The result of the central function contains a `table`, which the vantage6 portal shows as a
table (see `ui_visualizations` in `algorithm_store.json`).

## How R fits in

The vantage6 algorithm wrapper (input, output, function lookup, the `@federated`, `@central` and `@dataframe` decorators, the client
that creates subtasks) exists for **Python only**. The two functions the wrapper calls are therefore Python, but they contain no
counting logic:

```
vantage6 wrapper (Python)
  partial_count   (partial.py)   writes the dataframe to a temporary CSV  ->  Rscript run.R count   ->  count_values()   (counting.R)
  central_count   (central.py)   creates the subtasks, collects results   ->  Rscript run.R combine ->  combine_counts() (counting.R)
```

| File | Language | Does |
|---|---|---|
| `v6_poc_count_r/r/counting.R` | R | all counting logic: `count_values()`, `combine_counts()`, labels, sorting, minimum cell size |
| `v6_poc_count_r/r/run.R` | R | command line entry point; prints the result as JSON |
| `v6_poc_count_r/r_bridge.py` | Python | writes the input, runs `Rscript`, reads the JSON; no logic |
| `v6_poc_count_r/partial.py`, `central.py` | Python | the two vantage6 entry points; thin |

Notes:

- The image is the vantage6 `algorithm-base` image (Debian bookworm, Python 3.13) plus R from Debian (`r-base-core`, `r-cran-jsonlite`; R 4.2.x).
  It is larger than the Python-only version (not measured). The tests were run with R 4.5.2 on Windows; the Dockerfile has not been built
  locally, the first CI build is its first test.
- The dataframe is written as CSV in a temporary folder **inside the algorithm container** and deleted afterwards. It does not leave the
  node. For a very large dataframe this is slow and uses memory twice; a later version could pass only the needed column or use Parquet.
- The result is JSON, readable from any language (not `RData`).
- Errors from R (for example "Column 'x' not found in the dataframe") come back as the error of the task.

## Functions

| Function | Step type | Runs | Arguments |
|---|---|---|---|
| `central_count` | `central_compute` | on one node; creates the partial tasks and adds up | `column_name` (default `gender_concept_id`), `min_cell_size` (default `0`) |
| `partial_count` | `federated_compute` | on every node, on its own dataframe | `column_name`, `min_cell_size` |

Both take one dataframe (`@dataframe(1)`), which is created beforehand with a data-extraction algorithm such as
`ghcr.io/vantage6/algorithm/extract-basics` (`read_parquet`, `read_csv`, `read_sql_database`, ...).

Result of `central_count`:

```json
{
  "total": 2694,
  "organizations": 2,
  "table": [
    {"value": "8507", "label": "MALE", "count": 1321},
    {"value": "8532", "label": "FEMALE", "count": 1373}
  ]
}
```

### Disclosure control (basic)

`min_cell_size > 0` reports a value that occurs fewer times at a node as `null`, and a node refuses to answer if its whole dataframe has
fewer rows than that. A `null` at one node stays `null` in the total. This is a first step, **not** complete disclosure control: the
`total` is not masked, so a suppressed cell can be estimated from the other cells, and the partial results are visible to the researcher.
Agree the real rules with the data holders before using this on real data.

## Tests

You need Python 3.13 and R with the package `jsonlite` (and `testthat` for the R tests). On Windows, `Rscript` is often not on the PATH:
set the environment variable `RSCRIPT` to its full path.

```bash
uv sync
uv run pytest
```

- `tests/testthat/test-counting.R`: the counting logic in R, on its own (run through `tests/test_r_unit.py`, or directly with
  `Rscript -e "testthat::test_dir('tests/testthat')"` from the repository root).
- `tests/test_r_bridge.py`: the Python call of R (CSV with commas, quotes and accents, missing values, errors, the POC numbers).
- `tests/test_store_json.py`: checks `algorithm_store.json` against the functions in the code (names, arguments, defaults, allowed types).
- `tests/test_mock_network.py`: runs central and partial in vantage6's `MockNetwork` with Parquet files and the same `read_parquet`
  function as `extract-basics` (skipped when vantage6 or R is not installed).

## Build and release (CI/CD, not from a laptop)

The Docker image is built by GitHub Actions. Push a tag with a version number:

```bash
git tag 0.1.0
git push origin 0.1.0
```

`.github/workflows/release.yml` calls the shared vantage6 workflow (pinned to a commit), which runs `make image` and pushes
`ghcr.io/weejweejweejpunt-ops/v6-poc-count-r:<version>-v6-<vantage6 version>`, `:latest` and `:<vantage6 major>`.

**Image format.** The algorithm store looks up the digest of an image with an `Accept` header for the plain Docker v2 manifest only
(`get_digest` in vantage6-common 5.0.3). The `Makefile` therefore builds with `--provenance=false --sbom=false`, on a `docker-container`
builder, and exports with `oci-mediatypes=false`; the last job of the release workflow (`verify-store-compatible`) checks this and fails
the release otherwise. Without provenance there is no build attestation in the image: a reviewer has to check the CI run and the digest.

After the first push, open the package on GitHub (Packages > `v6-poc-count-r` > Package settings) and set the visibility to **public**, otherwise
the nodes cannot pull the image without a pull secret. Also check under the repository Settings > Actions > General that workflows are allowed.

## Algorithm store

Submit `algorithm_store.json` in the algorithm store (portal: Algorithm store > add algorithm > upload JSON). The store resolves the image
digest from the registry when you submit, so the store must be able to reach `ghcr.io`. A reviewer has to approve the algorithm before it
can be run from the portal. Every new version is a new image, so a new submission and a new review.

## Layout

```
v6_poc_count_r/r/counting.R   counting logic in R, no vantage6 or Python dependencies
v6_poc_count_r/r/run.R        command line entry point (JSON on stdout)
v6_poc_count_r/r_bridge.py    runs Rscript; no logic
v6_poc_count_r/partial.py     partial_count (federated_compute)
v6_poc_count_r/central.py     central_count (central_compute)
algorithm_store.json          store metadata, incl. the table visualization
Dockerfile, Makefile          image on top of ghcr.io/vantage6/infrastructure/algorithm-base:5.0, plus R
.github/workflows/            tests and release
```

No licence has been chosen yet; add a `LICENSE` file before sharing the code beyond this proof of concept.
