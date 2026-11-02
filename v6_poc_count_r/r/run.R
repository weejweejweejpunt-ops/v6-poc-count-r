# Command line entry point for the counting logic; called by r_bridge.py (never by the user).
#
#   Rscript --vanilla run.R count   <dataframe.csv> <column_name> <min_cell_size>
#   Rscript --vanilla run.R combine <results.json>  <column_name>
#
# The result is printed as JSON on stdout. An error is printed on stderr and gives exit status 1.

this_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1]))
source(file.path(this_dir, "counting.R"))

main <- function(args) {
  command <- args[[1]]
  if (command == "count") {
    # everything is read as text: the keys are strings anyway, and no type is guessed wrongly.
    # blank.lines.skip = FALSE: in a file with one column a missing value is an empty line, and that is a row.
    df <- utils::read.csv(
      args[[2]],
      colClasses = "character", na.strings = "", check.names = FALSE, encoding = "UTF-8",
      blank.lines.skip = FALSE
    )
    count_values(df, args[[3]], as.numeric(args[[4]]))
  } else if (command == "combine") {
    results <- jsonlite::fromJSON(args[[2]], simplifyVector = FALSE)
    combine_counts(results, args[[3]])
  } else {
    stop(sprintf("Unknown command '%s'", command), call. = FALSE)
  }
}

status <- tryCatch(
  {
    result <- main(commandArgs(trailingOnly = TRUE))
    cat(jsonlite::toJSON(result, auto_unbox = TRUE, na = "null", null = "null", digits = NA), "\n", sep = "")
    0L
  },
  error = function(e) {
    cat(conditionMessage(e), "\n", sep = "", file = stderr())
    1L
  }
)
quit(save = "no", status = status)
