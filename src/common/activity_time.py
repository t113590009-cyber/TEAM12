import datetime

from src.common.periods import period_index, time_ranges_overlap
from src.common.time_slot import PERIOD_TABLE, period_time_range


def is_valid_date(date):
    if not isinstance(date, str) or len(date) != 10:
        return False
    if date[4] != "-" or date[7] != "-":
        return False
    parts = date[0:4] + date[5:7] + date[8:10]
    if not parts.isascii() or not parts.isdigit():
        return False
    try:
        datetime.date(int(date[0:4]), int(date[5:7]), int(date[8:10]))
    except ValueError:
        return False
    return True


def _all_periods():
    return sorted(PERIOD_TABLE, key=period_index)


def activity_periods(activity):
    if not isinstance(activity, dict):
        return []
    date = activity.get("date")
    start = activity.get("start_time")
    end = activity.get("end_time")
    if not is_valid_date(date):
        return []
    if not isinstance(start, str) or not isinstance(end, str):
        return []
    day = datetime.date.fromisoformat(date).isoweekday()
    result = []
    for period in _all_periods():
        p_start, p_end = period_time_range(period)
        if time_ranges_overlap(start, end, p_start, p_end):
            result.append((day, period))
    return result