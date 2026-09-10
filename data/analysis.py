"""
Analytical helpers: STL trend decomposition + linear trend projection.

Adapted from the Upper Peninsula Economic Report's analysis module. Real-estate
listing data is monthly (Realtor.com via FRED), so the defaults here are monthly
(period=12) rather than quarterly. The projection horizon is expressed in months.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL


def _next_month_dates(last_date: pd.Timestamp, periods: int) -> pd.DatetimeIndex:
    """The next `periods` month-start dates after `last_date`."""
    start = (last_date + pd.offsets.MonthBegin(1)).normalize()
    return pd.date_range(start=start, periods=periods, freq="MS")


def periods_to_current_month(
    last_date: pd.Timestamp, today: pd.Timestamp | None = None
) -> int:
    """Number of months from `last_date` to the current calendar month (>= 0)."""
    today = pd.Timestamp.today() if today is None else today
    diff = (today.to_period("M") - last_date.to_period("M")).n
    return max(0, diff)


def project_trend(
    trend: pd.Series,
    periods: int = 3,
    lookback: int = 6,
    log_transform: bool = False,
) -> pd.Series:
    """Linear-extrapolation projection of a monthly trend series.

    Fits OLS to the last `lookback` non-NaN points (in log space if requested)
    and returns the next `periods` projected values, indexed at the next
    `periods` month-start dates after the trend's last observation.

    Returns an empty Series if there are fewer than `lookback` valid points.
    """
    s = trend.dropna().sort_index()
    if len(s) < lookback:
        return pd.Series(dtype=float)

    tail = s.tail(lookback)
    x = np.arange(len(tail))
    y = np.log(tail.values) if log_transform else tail.values
    slope, intercept = np.polyfit(x, y, 1)

    future_x = np.arange(len(tail), len(tail) + periods)
    future_y = slope * future_x + intercept
    if log_transform:
        future_y = np.exp(future_y)

    return pd.Series(future_y, index=_next_month_dates(tail.index[-1], periods))


def deseasonalize_trend(
    series: pd.Series,
    period: int = 12,
    seasonal: int = 13,
    log_transform: bool = False,
) -> pd.Series:
    """STL trend component for a monthly series.

    Falls back to the raw series when there are fewer than 2*period observations
    (STL requires at least two full cycles). `log_transform=True` suits
    multiplicatively-growing series like prices.
    """
    s = series.dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if len(s) < 2 * period:
        return series.copy()

    work = np.log(s) if log_transform else s
    result = STL(work, period=period, seasonal=seasonal, robust=True).fit()
    trend = np.exp(result.trend) if log_transform else result.trend
    return trend.reindex(series.index)
