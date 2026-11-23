import pytest

from src.common.check_room_conflict import check_room_conflict
from src.common.state import State


def make_state(courses=None, activities=None):
    return State(
        courses=courses or {}, students={}, rooms={},
        activities=activities or {}, enrollments=set(), activity_signups=set(),
    )


def make_course(course_id="1150001", room_id="R101", slots=None,
                status="active", name="微積分"):
    return {
        "course_id": course_id, "name": name, "credits": 3,
        "category": "required", "teacher": "王大明", "capacity": 50,
        "room_id": room_id, "status": status,
        "slots": slots if slots is not None else [{"day": 2, "period": "3"}],
    }


@pytest.mark.normal
def test_same_room_same_slot_reports_room_conflict():
    state = make_state({"1150001": make_course()})
    result = check_room_conflict(state, "R101", [{"day": 2, "period": "3"}])
    assert result["ok"] is False
    assert [e["code"] for e in result["errors"]] == ["ROOM_CONFLICT"]
    assert result["errors"][0]["detail"] == {
        "day": 2, "period": "3", "with_kind": "course",
        "with_id": "1150001", "with_name": "微積分",
    }

@pytest.mark.normal
def test_different_room_same_slot_no_conflict():
    state = make_state({"1150001": make_course(room_id="R201")})
    result = check_room_conflict(state, "R101", [{"day": 2, "period": "3"}])
    assert result["ok"] is True
    assert result["errors"] == []


@pytest.mark.boundary
def test_adjacent_periods_no_conflict():
    state = make_state({"1150001": make_course(slots=[{"day": 2, "period": "3"}])})
    result = check_room_conflict(state, "R101", [{"day": 2, "period": "4"}])
    assert result["ok"] is True


@pytest.mark.boundary
def test_cancelled_course_does_not_conflict():
    state = make_state({"1150001": make_course(status="cancelled")})
    result = check_room_conflict(state, "R101", [{"day": 2, "period": "3"}])
    assert result["ok"] is True

@pytest.mark.boundary
def test_ignore_id_skips_own_course():
    state = make_state({"1150001": make_course()})
    result = check_room_conflict(
        state, "R101", [{"day": 2, "period": "3"}], ignore_id="1150001"
    )
    assert result["ok"] is True

@pytest.mark.boundary
def test_conflicts_sorted_by_day_then_period():
    state = make_state({
        "1150002": make_course(course_id="1150002", name="物理",
                               slots=[{"day": 4, "period": "5"}]),
        "1150001": make_course(course_id="1150001", name="微積分",
                               slots=[{"day": 2, "period": "3"}]),
    })
    new_slots = [{"day": 4, "period": "5"}, {"day": 2, "period": "3"}]
    result = check_room_conflict(state, "R101", new_slots)
    got = [(e["detail"]["day"], e["detail"]["period"]) for e in result["errors"]]
    assert got == [(2, "3"), (4, "5")]


@pytest.mark.boundary
def test_conflicts_sorted_letter_period_after_digit():
    both = [{"day": 1, "period": "a"}, {"day": 1, "period": "9"}]
    state = make_state({"1150001": make_course(slots=both)})
    result = check_room_conflict(state, "R101", both)
    got = [e["detail"]["period"] for e in result["errors"]]
    assert got == ["9", "a"]

@pytest.mark.error
def test_invalid_day_reports_invalid_period():
    state = make_state({"1150001": make_course()})
    result = check_room_conflict(state, "R101", [{"day": 8, "period": "3"}])
    assert result["ok"] is False
    assert [e["code"] for e in result["errors"]] == ["INVALID_PERIOD"]
    assert result["errors"][0]["detail"] == {"slot": {"day": 8, "period": "3"}}


@pytest.mark.error
def test_invalid_period_letter_reports_invalid_period():
    state = make_state({"1150001": make_course()})
    result = check_room_conflict(state, "R101", [{"day": 2, "period": "d"}])
    assert [e["code"] for e in result["errors"]] == ["INVALID_PERIOD"]


@pytest.mark.error
def test_empty_dict_slot_reports_invalid_period():
    state = make_state({"1150001": make_course()})
    result = check_room_conflict(state, "R101", [{}])
    assert [e["code"] for e in result["errors"]] == ["INVALID_PERIOD"]


@pytest.mark.error
def test_invalid_slot_does_not_hide_real_conflict():
    state = make_state({"1150001": make_course()})
    slots = [{"day": 8, "period": "3"}, {"day": 2, "period": "3"}]
    result = check_room_conflict(state, "R101", slots)
    assert [e["code"] for e in result["errors"]] == ["ROOM_CONFLICT", "INVALID_PERIOD"]


@pytest.mark.boundary
def test_empty_slots_list_is_ok():
    state = make_state({"1150001": make_course()})
    result = check_room_conflict(state, "R101", [])
    assert result["ok"] is True

@pytest.mark.boundary
def test_int_period_conflicts_with_string_period():
    state = make_state({"1150001": make_course()})
    result = check_room_conflict(state, "R101", [{"day": 2, "period": 3}])
    assert [e["code"] for e in result["errors"]] == ["ROOM_CONFLICT"]


@pytest.mark.boundary
def test_uppercase_period_conflicts_with_lowercase():
    state = make_state({"1150001": make_course(slots=[{"day": 1, "period": "a"}])})
    result = check_room_conflict(state, "R101", [{"day": 1, "period": "A"}])
    assert [e["code"] for e in result["errors"]] == ["ROOM_CONFLICT"]


def make_activity(activity_id="A001", room_id="R101", date="2026-11-24",
                  start_time="10:10", end_time="11:00", status="active"):
    # 2026-11-24 是星期二，10:10～11:00 為第 3 節
    return {
        "activity_id": activity_id, "name": "講座", "date": date,
        "start_time": start_time, "end_time": end_time, "expected_size": 10,
        "activity_type": "talk", "min_capacity": 0, "required_equipment": [],
        "room_id": room_id, "status": status,
    }


@pytest.mark.normal
def test_activity_in_same_room_and_period_reports_conflict():
    state = make_state(activities={"A001": make_activity()})
    result = check_room_conflict(state, "R101", [{"day": 2, "period": "3"}])
    assert result["ok"] is False
    assert result["errors"][0]["detail"] == {
        "day": 2, "period": "3", "with_kind": "activity",
        "with_id": "A001", "with_name": "講座",
    }


@pytest.mark.normal
def test_course_and_activity_conflicts_sorted_by_slot_then_id():
    state = make_state(
        {"1150001": make_course(slots=[{"day": 2, "period": "4"}])},
        {"A001": make_activity(start_time="10:10", end_time="12:00")},
    )
    result = check_room_conflict(
        state, "R101", [{"day": 2, "period": "3"}, {"day": 2, "period": "4"}])
    assert [(e["detail"]["period"], e["detail"]["with_id"])
            for e in result["errors"]] == [("3", "A001"), ("4", "1150001"), ("4", "A001")]


@pytest.mark.boundary
def test_activity_in_break_time_does_not_conflict():
    # 12:10～13:00 落在第 4、5 節之間，不佔節次
    state = make_state(activities={"A001": make_activity(start_time="12:10", end_time="13:00")})
    slots = [{"day": 2, "period": "4"}, {"day": 2, "period": "5"}]
    assert check_room_conflict(state, "R101", slots)["ok"] is True


@pytest.mark.boundary
def test_cancelled_activity_does_not_conflict():
    state = make_state(activities={"A001": make_activity(status="cancelled")})
    assert check_room_conflict(state, "R101", [{"day": 2, "period": "3"}])["ok"] is True


@pytest.mark.boundary
def test_activity_other_room_or_unassigned_does_not_conflict():
    state = make_state(activities={"A001": make_activity(room_id="R201"),
                                   "A002": make_activity("A002", room_id=None)})
    assert check_room_conflict(state, "R101", [{"day": 2, "period": "3"}])["ok"] is True


@pytest.mark.boundary
def test_ignore_id_skips_own_activity():
    state = make_state(activities={"A001": make_activity()})
    result = check_room_conflict(state, "R101", [{"day": 2, "period": "3"}], ignore_id="A001")
    assert result["ok"] is True


@pytest.mark.boundary
def test_include_activities_false_only_checks_courses():
    state = make_state(activities={"A001": make_activity()})
    result = check_room_conflict(state, "R101", [{"day": 2, "period": "3"}],
                                 include_activities=False)
    assert result["ok"] is True
