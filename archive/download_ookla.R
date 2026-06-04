#' Download Ookla Performance Tiles Using Multiple Methods
#'
#' @description Downloads Ookla broadband performance data using multiple fallback methods
#' when AWS CLI is not available. Tries HTTP access, curl, and wget as alternatives.
#'
#' @param service Character. Either "mobile" or "fixed"
#' @param year Numeric. Year of interest (2019 or later)
#' @param quarter Numeric. Quarter of interest (1, 2, 3, or 4)
#' @param return_sf Logical. Whether to return data as sf object (default: TRUE)
#' @param filter_region Optional sf object to filter tiles to specific geographic area
#' @param temp_dir Character. Directory for temporary files (default: tempdir())
#' @param keep_file Logical. Whether to keep the downloaded parquet file (default: FALSE)
#' @param method Character. Download method: "auto", "http", "curl", "wget", or "aws"
#'
#' @return Data frame or sf data frame with Ookla performance metrics
#'
#' @export
download_ookla_tiles_robust <- function(service = c("mobile", "fixed"),
                                        year,
                                        quarter,
                                        return_sf = TRUE,
                                        filter_region = NULL,
                                        temp_dir = tempdir(),
                                        keep_file = FALSE,
                                        method = "auto") {
  
  # Validate inputs
  service <- match.arg(service)
  method <- match.arg(method, c("auto", "http", "curl", "wget", "aws"))
  
  if (!is.numeric(year) || year < 2019) {
    stop("Year must be numeric and 2019 or later")
  }
  
  if (!is.numeric(quarter) || !quarter %in% 1:4) {
    stop("Quarter must be numeric and between 1 and 4")
  }
  
  # Construct the file paths
  quarter_dates <- c("01-01", "04-01", "07-01", "10-01")
  date_str <- paste0(year, "-", quarter_dates[quarter])
  filename <- sprintf("%s_performance_%s_tiles.parquet", date_str, service)
  
  # Try HTTP URL first (Ookla sometimes provides HTTP access)
  http_url <- sprintf("https://ookla-open-data.s3.amazonaws.com/parquet/performance/type=%s/year=%d/quarter=%d/%s",
                      service, year, quarter, filename)
  
  # S3 URL for AWS CLI
  s3_url <- sprintf("s3://ookla-open-data/parquet/performance/type=%s/year=%d/quarter=%d/%s",
                    service, year, quarter, filename)
  
  # Create local file path
  local_filename <- if (keep_file) {
    file.path(temp_dir, paste0("ookla_", service, "_", year, "_Q", quarter, ".parquet"))
  } else {
    tempfile(pattern = "ookla_", tmpdir = temp_dir, fileext = ".parquet")
  }
  
  # Ensure temp directory exists
  if (!dir.exists(temp_dir)) {
    dir.create(temp_dir, recursive = TRUE)
  }
  
  message(sprintf("Downloading %s network performance data for Q%d %d...", 
                  service, quarter, year))
  
  # Define download methods
  download_methods <- list(
    http = function() {
      message("Attempting HTTP download...")
      tryCatch({
        download.file(http_url, local_filename, mode = "wb", quiet = FALSE)
        if (file.exists(local_filename) && file.info(local_filename)$size > 0) {
          return(TRUE)
        }
        return(FALSE)
      }, error = function(e) {
        message("HTTP download failed: ", e$message)
        return(FALSE)
      })
    },
    
    curl = function() {
      if (Sys.which("curl") == "") {
        message("curl not available")
        return(FALSE)
      }
      
      message("Attempting curl download...")
      curl_cmd <- sprintf('curl -L -o "%s" "%s"', local_filename, http_url)
      result <- system(curl_cmd, ignore.stdout = TRUE)
      
      if (result == 0 && file.exists(local_filename) && file.info(local_filename)$size > 0) {
        return(TRUE)
      }
      return(FALSE)
    },
    
    wget = function() {
      if (Sys.which("wget") == "") {
        message("wget not available")
        return(FALSE)
      }
      
      message("Attempting wget download...")
      wget_cmd <- sprintf('wget -O "%s" "%s"', local_filename, http_url)
      result <- system(wget_cmd, ignore.stdout = TRUE)
      
      if (result == 0 && file.exists(local_filename) && file.info(local_filename)$size > 0) {
        return(TRUE)
      }
      return(FALSE)
    },
    
    aws = function() {
      if (Sys.which("aws") == "") {
        message("AWS CLI not available")
        return(FALSE)
      }
      
      message("Attempting AWS CLI download...")
      aws_cmd <- sprintf('aws s3 cp "%s" "%s" --no-sign-request', s3_url, local_filename)
      result <- system(aws_cmd, ignore.stdout = TRUE, ignore.stderr = TRUE)
      
      if (result == 0 && file.exists(local_filename) && file.info(local_filename)$size > 0) {
        return(TRUE)
      }
      return(FALSE)
    }
  )
  
  # Determine which methods to try
  if (method == "auto") {
    methods_to_try <- c("http", "curl", "wget", "aws")
  } else {
    methods_to_try <- method
  }
  
  # Try each method until one succeeds
  success <- FALSE
  for (method_name in methods_to_try) {
    if (method_name %in% names(download_methods)) {
      if (download_methods[[method_name]]()) {
        message(sprintf("Successfully downloaded using %s method", method_name))
        success <- TRUE
        break
      }
    }
  }
  
  if (!success) {
    stop("All download methods failed. The file may not exist or there may be network issues.")
  }
  
  file_size <- file.info(local_filename)$size
  message(sprintf("Downloaded file size: %.2f MB", file_size / 1024^2))
  
  # Read the parquet file
  if (!requireNamespace("arrow", quietly = TRUE)) {
    stop("The 'arrow' package is required to read parquet files. Install with: install.packages('arrow')")
  }
  
  message("Reading parquet file...")
  tiles <- arrow::read_parquet(local_filename)
  
  message(sprintf("Loaded %d tiles with %d columns", nrow(tiles), ncol(tiles)))
  
  # Convert to sf object if requested
  if (return_sf) {
    if (!requireNamespace("sf", quietly = TRUE)) {
      stop("The 'sf' package is required for spatial operations. Install with: install.packages('sf')")
    }
    
    message("Converting to spatial data...")
    tiles <- sf::st_as_sf(tiles, wkt = "tile", crs = 4326)
  }
  
  # Apply spatial filter if provided
  if (!is.null(filter_region)) {
    if (!return_sf) {
      warning("Converting to sf format for spatial filtering")
      if (!requireNamespace("sf", quietly = TRUE)) {
        stop("The 'sf' package is required for spatial filtering")
      }
      tiles <- sf::st_as_sf(tiles, wkt = "tile", crs = 4326)
    }
    
    message("Applying spatial filter...")
    
    # Ensure same CRS
    if (sf::st_crs(tiles) != sf::st_crs(filter_region)) {
      filter_region <- sf::st_transform(filter_region, sf::st_crs(tiles))
    }
    
    # Perform spatial filter
    original_count <- nrow(tiles)
    tiles <- sf::st_filter(tiles, filter_region)
    message(sprintf("Filtered from %d to %d tiles within specified region", 
                    original_count, nrow(tiles)))
  }
  
  # Clean up temporary file if not keeping
  if (!keep_file && file.exists(local_filename)) {
    unlink(local_filename)
    message("Temporary file cleaned up")
  } else if (keep_file) {
    message("File saved to: ", local_filename)
  }
  
  # Add metadata as attributes
  attr(tiles, "ookla_metadata") <- list(
    service = service,
    year = year,
    quarter = quarter,
    download_date = Sys.Date(),
    tile_size = "~610.8m x 610.8m at equator",
    zoom_level = 16,
    download_method = method_name,
    local_file = if (keep_file) local_filename else NULL
  )
  
  return(tiles)
}

#' Check Available Download Methods
#'
#' @description Checks which download methods are available on the system
#'
#' @return Named logical vector indicating available methods
#'
#' @export
check_download_methods <- function() {
  methods <- c(
    http = TRUE,  # download.file is always available
    curl = Sys.which("curl") != "",
    wget = Sys.which("wget") != "",
    aws = Sys.which("aws") != ""
  )
  
  cat("Available download methods:\n")
  for (method in names(methods)) {
    status <- if (methods[method]) "✓ Available" else "✗ Not available"
    cat(sprintf("  %s: %s\n", method, status))
  }
  
  return(methods)
}

#' Install AWS CLI (Helper Function)
#'
#' @description Provides instructions for installing AWS CLI
#'
#' @export
install_aws_cli_help <- function() {
  cat("To install AWS CLI:\n\n")
  cat("Option 1 - Using pip:\n")
  cat("  pip install awscli\n\n")
  cat("Option 2 - Using conda:\n")
  cat("  conda install -c conda-forge awscli\n\n")
  cat("Option 3 - Download installer:\n")
  cat("  Visit: https://aws.amazon.com/cli/\n\n")
  cat("Option 4 - On Ubuntu/Debian:\n")
  cat("  sudo apt-get install awscli\n\n")
  cat("Option 5 - On macOS with Homebrew:\n")
  cat("  brew install awscli\n\n")
  cat("After installation, verify with: aws --version\n")
}

#' List Available Ookla Data Files via HTTP
#'
#' @description Lists available Ookla performance data files by attempting to
#' access known file patterns. Since AWS CLI may not be available, this function
#' uses HTTP HEAD requests to check file existence.
#'
#' @param service Character. Either "mobile" or "fixed"
#' @param years Numeric vector. Years to check (default: 2019:2024)
#' @param quarters Numeric vector. Quarters to check (default: 1:4)
#' @param method Character. Method to use: "http", "curl", or "aws"
#'
#' @return Data frame with columns: service, year, quarter, filename, exists, url
#'
#' @export
list_ookla_files_http <- function(service = c("mobile", "fixed"),
                                  years = 2019:2024,
                                  quarters = 1:4,
                                  method = "auto") {
  
  service <- match.arg(service)
  method <- match.arg(method, c("auto", "http", "curl", "aws"))
  
  # Determine which method to use
  if (method == "auto") {
    if (Sys.which("curl") != "") {
      method <- "curl"
    } else if (Sys.which("aws") != "") {
      method <- "aws"
    } else {
      method <- "http"
    }
  }
  
  # Generate all possible file combinations
  quarter_dates <- c("01-01", "04-01", "07-01", "10-01")
  results <- data.frame()
  
  message(sprintf("Checking availability using %s method...", method))
  
  for (year in years) {
    for (quarter in quarters) {
      date_str <- paste0(year, "-", quarter_dates[quarter])
      filename <- sprintf("%s_performance_%s_tiles.parquet", date_str, service)
      
      url <- sprintf("https://ookla-open-data.s3.amazonaws.com/parquet/performance/type=%s/year=%d/quarter=%d/%s",
                     service, year, quarter, filename)
      
      # Check if file exists
      exists <- check_file_exists(url, method)
      
      results <- rbind(results, data.frame(
        service = service,
        year = year,
        quarter = quarter,
        filename = filename,
        exists = exists,
        url = url,
        stringsAsFactors = FALSE
      ))
      
      if (exists) {
        message(sprintf("✓ Found: %s Q%d %d", service, quarter, year))
      }
    }
  }
  
  return(results)
}

#' Check if a file exists at a URL
#'
#' @description Helper function to check file existence using different methods
#'
#' @param url Character. URL to check
#' @param method Character. Method to use for checking
#'
#' @return Logical indicating if file exists
#'
check_file_exists <- function(url, method = "curl") {
  
  if (method == "curl" && Sys.which("curl") != "") {
    # Use curl to check HTTP status
    cmd <- sprintf('curl -s -I "%s" | head -n 1', url)
    result <- system(cmd, intern = TRUE, ignore.stderr = TRUE)
    
    if (length(result) > 0 && grepl("200", result[1])) {
      return(TRUE)
    }
    
  } else if (method == "http") {
    # Use R's built-in HTTP capabilities
    tryCatch({
      con <- url(url, method = "HEAD")
      open(con)
      close(con)
      return(TRUE)
    }, error = function(e) {
      return(FALSE)
    })
    
  } else if (method == "aws" && Sys.which("aws") != "") {
    # Convert HTTP URL to S3 URL for AWS CLI
    s3_url <- gsub("https://ookla-open-data.s3.amazonaws.com/", "s3://ookla-open-data/", url)
    cmd <- sprintf('aws s3 ls "%s" --no-sign-request', s3_url)
    result <- system(cmd, ignore.stdout = TRUE, ignore.stderr = TRUE)
    return(result == 0)
  }
  
  return(FALSE)
}

#' Get Ookla Data Summary
#'
#' @description Provides summary statistics and metadata for Ookla tiles
#'
#' @param tiles Data frame or sf object with Ookla data
#' @param detailed Logical. Whether to provide detailed statistics
#'
#' @return List with summary information
#'
#' @export
summarize_ookla_data <- function(tiles, detailed = TRUE) {
  
  if (nrow(tiles) == 0) {
    return(list(message = "No data to summarize"))
  }
  
  # Basic summary
  summary_info <- list(
    total_tiles = nrow(tiles),
    columns = ncol(tiles),
    column_names = names(tiles)
  )
  
  # Add metadata if available
  metadata <- attr(tiles, "ookla_metadata")
  if (!is.null(metadata)) {
    summary_info$metadata <- metadata
  }
  
  # Performance statistics (if columns exist)
  if ("avg_d_kbps" %in% names(tiles)) {
    summary_info$download_speed <- list(
      mean = round(mean(tiles$avg_d_kbps, na.rm = TRUE), 2),
      median = round(median(tiles$avg_d_kbps, na.rm = TRUE), 2),
      min = round(min(tiles$avg_d_kbps, na.rm = TRUE), 2),
      max = round(max(tiles$avg_d_kbps, na.rm = TRUE), 2),
      sd = round(sd(tiles$avg_d_kbps, na.rm = TRUE), 2)
    )
  }
  
  if ("avg_u_kbps" %in% names(tiles)) {
    summary_info$upload_speed <- list(
      mean = round(mean(tiles$avg_u_kbps, na.rm = TRUE), 2),
      median = round(median(tiles$avg_u_kbps, na.rm = TRUE), 2),
      min = round(min(tiles$avg_u_kbps, na.rm = TRUE), 2),
      max = round(max(tiles$avg_u_kbps, na.rm = TRUE), 2),
      sd = round(sd(tiles$avg_u_kbps, na.rm = TRUE), 2)
    )
  }
  
  if ("tests" %in% names(tiles)) {
    summary_info$tests <- list(
      total = sum(tiles$tests, na.rm = TRUE),
      mean_per_tile = round(mean(tiles$tests, na.rm = TRUE), 2),
      median_per_tile = round(median(tiles$tests, na.rm = TRUE), 2)
    )
  }
  
  if ("devices" %in% names(tiles)) {
    summary_info$devices <- list(
      total = sum(tiles$devices, na.rm = TRUE),
      mean_per_tile = round(mean(tiles$devices, na.rm = TRUE), 2)
    )
  }
  
  # Spatial information if sf object
  if (inherits(tiles, "sf")) {
    bbox <- sf::st_bbox(tiles)
    summary_info$spatial <- list(
      crs = as.character(sf::st_crs(tiles)),
      bbox = list(
        xmin = round(bbox["xmin"], 6),
        ymin = round(bbox["ymin"], 6),
        xmax = round(bbox["xmax"], 6),
        ymax = round(bbox["ymax"], 6)
      )
    )
  }
  
  class(summary_info) <- "ookla_summary"
  return(summary_info)
}

#' Print method for ookla_summary
#' @export
print.ookla_summary <- function(x, ...) {
  cat("Ookla Performance Data Summary\n")
  cat("==============================\n\n")
  
  if (!is.null(x$metadata)) {
    cat("Dataset Information:\n")
    cat(sprintf("  Service: %s\n", x$metadata$service))
    cat(sprintf("  Period: Q%d %d\n", x$metadata$quarter, x$metadata$year))
    cat(sprintf("  Downloaded: %s\n", x$metadata$download_date))
    cat(sprintf("  Method: %s\n", x$metadata$download_method))
    cat("\n")
  }
  
  cat("Data Structure:\n")
  cat(sprintf("  Total tiles: %s\n", format(x$total_tiles, big.mark = ",")))
  cat(sprintf("  Columns: %d\n", x$columns))
  cat("\n")
  
  if (!is.null(x$download_speed)) {
    cat("Download Speed (kbps):\n")
    cat(sprintf("  Mean: %s\n", format(x$download_speed$mean, big.mark = ",")))
    cat(sprintf("  Median: %s\n", format(x$download_speed$median, big.mark = ",")))
    cat(sprintf("  Range: %s - %s\n", 
                format(x$download_speed$min, big.mark = ","),
                format(x$download_speed$max, big.mark = ",")))
    cat("\n")
  }
  
  if (!is.null(x$upload_speed)) {
    cat("Upload Speed (kbps):\n")
    cat(sprintf("  Mean: %s\n", format(x$upload_speed$mean, big.mark = ",")))
    cat(sprintf("  Median: %s\n", format(x$upload_speed$median, big.mark = ",")))
    cat(sprintf("  Range: %s - %s\n", 
                format(x$upload_speed$min, big.mark = ","),
                format(x$upload_speed$max, big.mark = ",")))
    cat("\n")
  }
  
  if (!is.null(x$tests)) {
    cat("Speed Tests:\n")
    cat(sprintf("  Total tests: %s\n", format(x$tests$total, big.mark = ",")))
    cat(sprintf("  Mean per tile: %s\n", format(x$tests$mean_per_tile, big.mark = ",")))
    cat("\n")
  }
  
  if (!is.null(x$spatial)) {
    cat("Spatial Information:\n")
    cat(sprintf("  CRS: %s\n", x$spatial$crs))
    cat(sprintf("  Bounding box: (%.6f, %.6f) to (%.6f, %.6f)\n",
                x$spatial$bbox$xmin, x$spatial$bbox$ymin,
                x$spatial$bbox$xmax, x$spatial$bbox$ymax))
  }
}

#' Check System Requirements
#'
#' @description Comprehensive check of system requirements for Ookla data processing
#'
#' @return List with system information and recommendations
#'
#' @export
check_system_requirements <- function() {
  
  cat("System Requirements Check\n")
  cat("=========================\n\n")
  
  # Check R packages
  required_packages <- c("arrow", "sf", "dplyr")
  optional_packages <- c("ggplot2", "leaflet", "mapview")
  
  cat("Required R Packages:\n")
  for (pkg in required_packages) {
    installed <- requireNamespace(pkg, quietly = TRUE)
    status <- if (installed) "✓ Installed" else "✗ Missing"
    cat(sprintf("  %s: %s\n", pkg, status))
  }
  
  cat("\nOptional R Packages (for visualization):\n")
  for (pkg in optional_packages) {
    installed <- requireNamespace(pkg, quietly = TRUE)
    status <- if (installed) "✓ Installed" else "○ Not installed"
    cat(sprintf("  %s: %s\n", pkg, status))
  }
  
  # Check system tools
  cat("\nSystem Tools:\n")
  tools <- c("curl", "wget", "aws")
  available_tools <- c()
  
  for (tool in tools) {
    available <- Sys.which(tool) != ""
    status <- if (available) "✓ Available" else "○ Not available"
    cat(sprintf("  %s: %s\n", tool, status))
    if (available) available_tools <- c(available_tools, tool)
  }
  
  # Recommendations
  cat("\nRecommendations:\n")
  
  missing_required <- required_packages[!sapply(required_packages, function(x) requireNamespace(x, quietly = TRUE))]
  if (length(missing_required) > 0) {
    cat("  Install required packages:\n")
    cat(sprintf("    install.packages(c(%s))\n", 
                paste0('"', missing_required, '"', collapse = ", ")))
  }
  
  if (length(available_tools) == 0) {
    cat("  Consider installing curl or wget for more reliable downloads\n")
    cat("  Or install AWS CLI for direct S3 access\n")
  }
  
  # Return summary
  invisible(list(
    required_packages_installed = all(sapply(required_packages, function(x) requireNamespace(x, quietly = TRUE))),
    available_download_tools = available_tools,
    system_ready = all(sapply(required_packages, function(x) requireNamespace(x, quietly = TRUE))) && length(available_tools) > 0
  ))
}

#' Get Available Years and Quarters
#'
#' @description Returns information about available data periods
#'
#' @param service Character. Either "mobile" or "fixed"
#' @param check_online Logical. Whether to check online availability (slower)
#'
#' @return Data frame with available periods
#'
#' @export
get_available_periods <- function(service = c("mobile", "fixed"), check_online = FALSE) {
  
  service <- match.arg(service)
  
  # Known available periods (update this as new data becomes available)
  known_periods <- expand.grid(
    year = 2019:2024,
    quarter = 1:4,
    stringsAsFactors = FALSE
  )
  
  known_periods$service <- service
  known_periods$likely_available <- TRUE
  
  # Filter out future periods
  current_year <- as.numeric(format(Sys.Date(), "%Y"))
  current_quarter <- ceiling(as.numeric(format(Sys.Date(), "%m")) / 3)
  
  known_periods$likely_available <- 
    known_periods$year < current_year | 
    (known_periods$year == current_year & known_periods$quarter <= current_quarter)
  
  if (check_online) {
    message("Checking online availability (this may take a moment)...")
    availability <- list_ookla_files_http(service, unique(known_periods$year), 1:4)
    
    # Merge with online check results
    known_periods <- merge(
      known_periods,
      availability[, c("year", "quarter", "exists")],
      by = c("year", "quarter"),
      all.x = TRUE
    )
    
    known_periods$exists[is.na(known_periods$exists)] <- FALSE
  }
  
  return(known_periods[order(known_periods$year, known_periods$quarter), ])
}
