# pipeline/utils.py
"""
Cross-cutting utility functions for the GDELT pipeline.

This module is imported by all other pipeline modules.
It provides the following shared tools:

    - logger            : standardized logging system for the entire pipeline
    - timer             : decorator measuring function execution time
    - create_directories: automatic creation of working directories
    - validate_dataframe: DataFrame validity check

Changes in v1.1:
    MAJ-02: Added functools.wraps to the timer decorator to preserve
            function metadata (__name__, __doc__, __module__).
    MAJ-03: Replaced logging.basicConfig() with a handler-safe setup
            that prevents duplicate log messages on multiple imports
            and does not pollute the root logger.
    MIN-03: Added pd.DataFrame type hint on validate_dataframe().
    MIN-06: Removed emojis from log messages for ASCII compatibility.

Author  : Team 7 - Benin Insights Challenge 2026
Date    : May 2026
Version : 1.2
"""

import os
import time
import logging
import functools
import pandas as pd
from .config import LOG_LEVEL, LOG_FORMAT


# ─────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────

def setup_logger(name: str = "gdelt_pipeline") -> logging.Logger:
    """
    Configure and return a standardized logger for the pipeline.

    MAJ-03: This implementation avoids calling logging.basicConfig()
    which adds a handler to the ROOT logger. Calling basicConfig()
    on multiple imports (or in a Jupyter notebook) adds duplicate
    handlers, producing repeated log messages.

    Instead, we configure a NAMED logger with:
    - Handler, level and propagate set inside the guard block
      to ensure consistent configuration on first initialization only
    - A single StreamHandler (checked before adding)
    - propagate=False to avoid bubbling up to the root logger
    - This prevents interference with BigQuery client logging,
      Streamlit, or any other library using Python logging.

    Log format:
        2026-05-01 10:32:15 - INFO - Message here

    Args:
        name: Logger name (default: 'gdelt_pipeline')

    Returns:
        logging.Logger: Configured logger ready to use
    """
    logger = logging.getLogger(name)

    # Guard block: configure only once to prevent duplicate handlers.
    # On multiple imports or Jupyter notebook reruns, getLogger(name)
    # returns the SAME logger instance already configured — skip setup.
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL))
        # Do not propagate to root logger to avoid interference
        # with third-party libraries (BigQuery, Streamlit, etc.)
        logger.propagate = False

    return logger


# Global logger instance — imported by all pipeline modules
# Usage in other modules: from .utils import logger
logger = setup_logger()


# ─────────────────────────────────────────────────────────────────
# TIMER DECORATOR
# ─────────────────────────────────────────────────────────────────

def timer(func):
    """
    Decorator that measures and logs the execution time of a function.

    Applied to all main pipeline functions to identify slow steps
    and document performance in logs. Useful for monitoring and debugging.

    MAJ-02: Uses @functools.wraps(func) to preserve the decorated
    function's metadata (__name__, __doc__, __module__).
    Without it, all decorated functions would appear as 'wrapper'
    in introspection, breaking documentation tools and test frameworks.

    Usage:
        @timer
        def my_function():
            ...

    Produces in logs:
        INFO - Starting: my_function
        INFO - Completed: my_function - 3.42s

    Args:
        func: Function to decorate

    Returns:
        function: Wrapped function with execution time measurement
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start  = time.time()
        logger.info(f"Starting: {func.__name__}")
        result = func(*args, **kwargs)
        duration = round(time.time() - start, 2)
        logger.info(f"Completed: {func.__name__} - {duration}s")
        return result
    return wrapper


# ─────────────────────────────────────────────────────────────────
# DIRECTORY CREATION
# ─────────────────────────────────────────────────────────────────

def create_directories(*paths) -> None:
    """
    Create required pipeline directories if they do not exist.

    Called at the start of each extraction and load step to ensure
    data/raw/, data/clean/ and data/sample/ exist before any
    write attempt.

    Uses os.makedirs with exist_ok=True — no error if the directory
    already exists. Also creates intermediate parent directories
    if necessary.

    Accepts both str and pathlib.Path objects.

    Args:
        *paths: One or more directory paths to create (str or Path)

    Example:
        create_directories(RAW_DIR, PROCESSED_DIR)
    """
    for path in paths:
        os.makedirs(path, exist_ok=True)
        logger.info(f"Directory ready: {path}")


# ─────────────────────────────────────────────────────────────────
# DATAFRAME VALIDATION
# ─────────────────────────────────────────────────────────────────

def validate_dataframe(df: pd.DataFrame, name: str = "dataframe") -> bool:
    """
    Verify that a pandas DataFrame is valid and non-empty.

    MIN-03: Added pd.DataFrame type hint on the df parameter
    for readability and compatibility with static analysis tools.

    Called between each pipeline step (after extraction, after
    transformation, before loading) to immediately detect any data
    issue and avoid propagating an empty or None DataFrame to
    subsequent steps.

    Logs:
        - Number of rows and columns
        - Missing values per column (if any)

    Args:
        df  : pandas DataFrame to validate
        name: Descriptive name of the DataFrame for log messages

    Returns:
        bool: True if the DataFrame is valid and non-empty,
              False if the DataFrame is None or empty

    Example:
        if not validate_dataframe(df, "raw data"):
            raise ValueError("Invalid DataFrame")
    """
    # Check that the DataFrame exists and is not empty
    if df is None or df.empty:
        logger.error(f"[ERROR] {name} is empty or None - pipeline interrupted")
        return False

    # Log dimensional summary
    logger.info(f"[OK] {name} - {len(df):,} rows x {len(df.columns)} columns")

    # Detect and log missing values per column
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        logger.warning("[WARN] Missing values detected:")
        for col, count in missing.items():
            pct = round(count / len(df) * 100, 1)
            logger.warning(f"  -> {col}: {count:,} missing ({pct}%)")

    return True