import pytest
from src.common.activity_time import activity_periods


def make_activity(date="2026-10-15", start="15:10", end="16:00"):
    return {"date": date, "start_time": start, "end_time": end}


@pytest.mark.normal
def test_activity_periods_single_period():
    # 2026-10-15 是星期四
    assert activity_periods(make_activity()) == [(4, "7")]


@pytest.mark.normal
def test_activity_periods_multiple_periods():
    result = activity_periods(make_activity(start="15:30", end="17:20"))
    assert result == [(4, "7"), (4, "8"), (4, "9")]


@pytest.mark.boundary
def test_activity_periods_touching_end_not_overlap():
    # 結束時間剛好等於第 9 節開始 17:10，頭尾相接不算重疊
    result = activity_periods(make_activity(start="15:30", end="17:10"))
    assert result == [(4, "7"), (4, "8")]


@pytest.mark.boundary
def test_activity_periods_lunch_break_is_empty():
    assert activity_periods(make_activity(start="12:10", end="13:00")) == []


@pytest.mark.boundary
def test_activity_periods_gap_between_classes_is_empty():
    assert activity_periods(make_activity(start="09:00", end="09:10")) == []


@pytest.mark.boundary
def test_activity_periods_evening_periods():
    result = activity_periods(make_activity(start="18:30", end="20:10"))
    assert result == [(4, "a"), (4, "b")]


@pytest.mark.error
@pytest.mark.parametrize("bad", [None, "text", 123, []])
def test_activity_periods_non_dict_returns_empty(bad):
    assert activity_periods(bad) == []


@pytest.mark.error
def test_activity_periods_missing_time_returns_empty():
    assert activity_periods({"date": "2026-10-15"}) == []
