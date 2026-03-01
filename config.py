"""
Shared configuration for WarDashboard.
Year range and timeouts. Supports optional env-based overrides (WAR_DASHBOARD_*).
"""

import os


def _int_env(name: str, default: int) -> int:
    """Read integer from env or return default."""
    val = os.environ.get(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


# Year range used to filter losses and economics to historical data only
YEAR_MIN = _int_env("WAR_DASHBOARD_YEAR_MIN", 2022)
YEAR_MAX = _int_env("WAR_DASHBOARD_YEAR_MAX", 2025)

# HTTP request timeout (seconds) for external API calls
REQUEST_TIMEOUT = _int_env("WAR_DASHBOARD_REQUEST_TIMEOUT", 60)
REQUEST_TIMEOUT_SHORT = _int_env("WAR_DASHBOARD_REQUEST_TIMEOUT_SHORT", 30)
