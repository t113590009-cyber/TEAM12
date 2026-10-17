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