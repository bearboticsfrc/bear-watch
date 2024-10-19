from datetime import datetime, timedelta

from config import FORCE_LOGOUT_HOUR


def compute_logout_timedelta() -> float:
    """
    Computes the time until the next scheduled forced logout.

    Returns:
        float: The number of seconds until the next logout time.
    """
    dt = datetime.now().replace(hour=FORCE_LOGOUT_HOUR, minute=0, second=0)

    # If the current hour is past the forced logout hour, schedule for the next day.
    if datetime.now().hour >= FORCE_LOGOUT_HOUR:
        dt += timedelta(days=1)

    return (dt - datetime.now()).total_seconds()
