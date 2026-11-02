# Counting logic in R. This file has no vantage6 or Python dependencies, so it can be tested on its own
# (see tests/testthat). The Python functions in partial.py and central.py only call count_values() on every
# node and combine_counts() in the central step, through run.R.

GENDER_COLUMN <- "gender_concept_id"
MISSING <- "(missing)"

# Standard OMOP concepts of the Gender domain, used to label gender_concept_id.
GENDER_LABELS <- c(
  "8507" = "MALE",
  "8532" = "FEMALE",
  "8521" = "OTHER",
  "8551" = "UNKNOWN",
  "8570" = "AMBIGUOUS"
)

# Turn cell values into the string keys that are used in the JSON results.
# A whole number that a data frame stored as a decimal (8507.0) becomes 8507, and NA becomes "(missing)".
cell_key <- function(x) {
  x <- as.character(x)
  x <- sub("^(-?[0-9]+)\\.0+$", "\\1", x)
  x[is.na(x)] <- MISSING
  x
}

# Numeric keys first (numerically), then other keys (alphabetically), "(missing)" last.
sort_keys <- function(keys) {
  keys <- as.character(keys)
  is_number <- grepl("^-?[0-9]+$", keys)
  group <- ifelse(is_number, 0L, ifelse(keys == MISSING, 2L, 1L))
  number <- suppressWarnings(as.numeric(ifelse(is_number, keys, NA)))
  keys[order(group, number, keys, method = "radix")]
}

# Count the rows of a data frame per value of one column.
#
# min_cell_size is basic disclosure control: a value that occurs fewer than this many times is reported as NA
# (null in the JSON). If the whole data frame has fewer rows than this, the function refuses (stops). 0 switches
# this off.
#
# Returns list(total = <number of rows>, counts = <named list: value -> count or NA>).
count_values <- function(df, column_name = GENDER_COLUMN, min_cell_size = 0) {
  if (!column_name %in% names(df)) {
    stop(sprintf("Column '%s' not found in the dataframe", column_name), call. = FALSE)
  }
  if (min_cell_size < 0) {
    stop("min_cell_size must be 0 or larger", call. = FALSE)
  }
  if (nrow(df) > 0 && nrow(df) < min_cell_size) {
    stop(
      sprintf("The dataframe has fewer rows than the minimum cell size (%s)", format(min_cell_size)),
      call. = FALSE
    )
  }
  tab <- table(cell_key(df[[column_name]]))
  keys <- sort_keys(names(tab))
  counts <- stats::setNames(vector("list", length(keys)), keys)
  for (key in keys) {
    n <- as.integer(tab[[key]])
    counts[[key]] <- if (n > 0L && n < min_cell_size) NA_integer_ else n
  }
  list(total = nrow(df), counts = counts)
}

# Add up the results of count_values() of all nodes. `results` is a list with one such result per node.
#
# A value that is NA (suppressed) at one or more nodes stays NA in the total, because its true total is not known.
#
# Returns list(total, organizations, table = <list of list(value, label, count)>). The table is shown as a table in
# the portal.
combine_counts <- function(results, column_name = GENDER_COLUMN) {
  keys <- sort_keys(unique(unlist(lapply(results, function(r) names(r$counts)))))
  rows <- lapply(keys, function(key) {
    count <- 0
    for (r in results) {
      if (!key %in% names(r$counts)) next
      n <- r$counts[[key]]
      if (is.null(n) || is.na(n)) {
        count <- NA_real_
        break
      }
      count <- count + n
    }
    label <- key
    if (column_name == GENDER_COLUMN && key %in% names(GENDER_LABELS)) {
      label <- GENDER_LABELS[[key]]
    }
    list(value = key, label = label, count = if (is.na(count)) NA_integer_ else as.integer(count))
  })
  list(
    total = sum(vapply(results, function(r) as.numeric(r$total), numeric(1))),
    organizations = length(results),
    table = rows
  )
}
