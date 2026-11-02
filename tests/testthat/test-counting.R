library(testthat)

# testthat runs the files in this folder with the folder as working directory
source(file.path("..", "..", "v6_poc_count_r", "r", "counting.R"))

persons <- function(male, female, other = integer(0)) {
  ids <- c(rep(8507L, male), rep(8532L, female), other)
  data.frame(person_id = seq_along(ids), gender_concept_id = ids)
}

as_counts <- function(rows) setNames(lapply(rows, `[[`, "count"), vapply(rows, `[[`, "", "value"))

test_that("count_values counts per gender", {
  result <- count_values(persons(653, 689))
  expect_equal(result$total, 1342)
  expect_equal(result$counts, list("8507" = 653L, "8532" = 689L))
})

test_that("count_values handles another column, decimals and missing values", {
  df <- data.frame(x = c("1.0", "1.0", "2.0", NA))
  result <- count_values(df, "x")
  expect_equal(result$total, 4)
  expect_equal(result$counts, list("1" = 2L, "2" = 1L, "(missing)" = 1L))
})

test_that("count_values of an empty dataframe is empty", {
  result <- count_values(data.frame(gender_concept_id = character(0)))
  expect_equal(result$total, 0)
  expect_length(result$counts, 0)
})

test_that("an unknown column is an error", {
  expect_error(count_values(persons(1, 1), "nope"), "not found")
})

test_that("min_cell_size masks small cells", {
  result <- count_values(persons(10, 3), min_cell_size = 5)
  expect_equal(result$counts, list("8507" = 10L, "8532" = NA_integer_))
  expect_equal(result$total, 13)
})

test_that("min_cell_size refuses a tiny dataframe", {
  expect_error(count_values(persons(2, 1), min_cell_size = 5), "fewer rows")
})

test_that("a negative min_cell_size is an error", {
  expect_error(count_values(persons(1, 1), min_cell_size = -1), "0 or larger")
})

test_that("combine_counts matches the POC data (two nodes: 1342 and 1352 persons)", {
  combined <- combine_counts(list(count_values(persons(653, 689)), count_values(persons(668, 684))))
  expect_equal(combined$total, 2694)
  expect_equal(combined$organizations, 2)
  expect_equal(
    combined$table,
    list(
      list(value = "8507", label = "MALE", count = 1321L),
      list(value = "8532", label = "FEMALE", count = 1373L)
    )
  )
})

test_that("combine_counts keeps a value that occurs at one node only", {
  a <- list(total = 3, counts = list("8507" = 3L))
  b <- list(total = 2, counts = list("8532" = 2L))
  expect_equal(as_counts(combine_counts(list(a, b))$table), list("8507" = 3L, "8532" = 2L))
})

test_that("a suppressed cell stays suppressed in the total", {
  a <- list(total = 10, counts = list("8507" = 7L, "8532" = NA_integer_))
  b <- list(total = 20, counts = list("8507" = 5L, "8532" = 15L))
  combined <- combine_counts(list(a, b))
  expect_equal(as_counts(combined$table), list("8507" = 12L, "8532" = NA_integer_))
  expect_equal(combined$total, 30)
})

test_that("combine_counts treats a null from JSON (NULL in R) as suppressed", {
  a <- list(total = 10, counts = list("8507" = 7L, "8532" = NULL))
  b <- list(total = 20, counts = list("8507" = 5L, "8532" = 15L))
  expect_equal(as_counts(combine_counts(list(a, b))$table)[["8532"]], NA_integer_)
})

test_that("labels are only used for the gender column", {
  results <- list(list(total = 1, counts = list("8507" = 1L)))
  expect_equal(combine_counts(results, "gender_concept_id")$table[[1]]$label, "MALE")
  expect_equal(combine_counts(results, "race_concept_id")$table[[1]]$label, "8507")
})

test_that("numbers are sorted numerically and (missing) comes last", {
  results <- list(list(total = 4, counts = list("10" = 1L, "9" = 1L, "(missing)" = 1L, "abc" = 1L)))
  order <- vapply(combine_counts(results, "x")$table, `[[`, "", "value")
  expect_equal(order, c("9", "10", "abc", "(missing)"))
})
