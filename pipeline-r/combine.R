# Join redistributed income + broadband onto civic polygons; derive metrics.
# Parallels pipeline/combine.py.
source("pipeline-r/config.R")
suppressPackageStartupMessages(library(sf))

tercile <- function(x) {
  # 1/2/3 labels by rank (robust to ties and NA), mirroring pandas qcut on ranks.
  r <- rank(x, ties.method = "first", na.last = "keep")
  br <- stats::quantile(r, probs = c(0, 1/3, 2/3, 1), na.rm = TRUE)
  cut(r, breaks = br, labels = c("1", "2", "3"), include.lowest = TRUE)
}

add_derived_metrics <- function(df) {
  df$income_speed_ratio <- ifelse(df$download_mbps > 0,
                                  df$mean_income / df$download_mbps, NA_real_)
  inc <- tercile(df$mean_income)
  spd <- tercile(df$download_mbps)
  df$bivariate_class <- paste0(as.character(inc), "-", as.character(spd))
  df
}

run_combine <- function() {
  civ <- sf::st_read(CIVIC_ASSOC, quiet = TRUE)[, c("geoid", "region_name")]
  income    <- read.csv(CIVIC_INCOME_R,    colClasses = c(geoid = "character"))
  broadband <- read.csv(CIVIC_BROADBAND_R, colClasses = c(geoid = "character"))
  civ$geoid <- as.character(civ$geoid)

  merged <- merge(civ, income, by = "geoid", all.x = TRUE)
  merged <- merge(merged, broadband, by = "geoid", all.x = TRUE)
  merged <- add_derived_metrics(merged)

  sf::st_write(merged, CIVIC_COMBINED_R, delete_dsn = TRUE, quiet = TRUE)
  cat(sprintf("Wrote %d combined civic-association rows -> %s\n",
              nrow(merged), CIVIC_COMBINED_R))
}

if (sys.nframe() == 0) run_combine()
