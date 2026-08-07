#!/usr/bin/env python3
"""
Shared Data Utilities
=====================
Centralized helpers for data cleaning and safe value access used across the
data-fetching and analysis layers. Keeping these in one place avoids the
previously scattered, slightly-different NaN-cleanup implementations.
"""

from typing import Optional

import numpy as np
import pandas as pd


def clean_close_nan(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    """Drop rows whose ``close`` price is NaN.

    NaN close rows appear when a fetch happens while the market is still open
    (an incomplete daily bar). They must be removed before any indicator
    calculation. This is the single source of truth for that cleanup.

    Args:
        df: A price DataFrame that may contain a ``close`` column.

    Returns:
        The same DataFrame with NaN-close rows removed. If ``df`` is None,
        empty, or has no ``close`` column, it is returned unchanged.
    """
    if df is None or df.empty or 'close' not in df.columns:
        return df
    return df.dropna(subset=['close'])


def safe_float(value, default: float = 0.0) -> float:
    """Convert a value to float, returning ``default`` for NaN/None/invalid.

    Args:
        value: Any scalar (number, string, None, NaN).
        default: Value to return when conversion is not possible.

    Returns:
        A finite float, or ``default``.
    """
    try:
        if value is None:
            return default
        result = float(value)
        if np.isnan(result) or np.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default
