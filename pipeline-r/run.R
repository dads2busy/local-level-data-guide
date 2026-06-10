# Run the runnable R stages end to end (acquisition is a recipe; see
# pipeline-r/acquire-recipe.R). Parallels pipeline/run.py.
# Usage from the repository root: Rscript pipeline-r/run.R
source("pipeline-r/redistribute_income.R")
source("pipeline-r/redistribute_broadband.R")
source("pipeline-r/combine.R")
source("pipeline-r/redistribute_income_parcels.R")
source("pipeline-r/compare_methods.R")
source("pipeline-r/validate.R")

run_income()
run_broadband()
run_combine()
run_income_parcels()
run_compare()
run_validate()
cat("R pipeline complete.\n")
