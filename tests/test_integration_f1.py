
import pytest
from src.common.state import State
from src.f1_data import (
    add_room, add_course, add_student,
    cancel_course, delete_course,
    modify_course, query_courses
)


def make_course(course_id, period="3"):
    return {
        "course_id": course_id,
        "name": "微積分",
        "credits": 3,
        "category": "required",
        "teacher": "王老師",
        "capacity": 30,
        "room_id": "R101",
        "slots": [{"day": 2, "period": period}]
    }


@pytest.fixture
def state():
    s = State()

    result = add_room(s, {
        "room_id": "R101",
        "building": "一教",
        "capacity": 60,
        "equipment": []
    })

    assert result["ok"] is True
    return s


def codes(result):
    return [error["code"] for error in result["errors"]]


# IT01 - Create Room and Course
@pytest.mark.normal
def test_create_room_and_course(state):
    result = add_course(state, make_course("1150001"))
    assert result["ok"] is True
    assert result["errors"] == []

    result = query_courses(state, {})
    assert result["ok"] is True
    assert result["errors"] == []
    assert any(
        course["course_id"] == "1150001"
        for course in result["data"]
    )


# IT02 - Room Conflict
@pytest.mark.error
def test_room_conflict(state):
    assert add_course(
        state, make_course("1150001")
    )["ok"] is True

    result = add_course(state, make_course("1150002"))

    assert result["ok"] is False
    assert codes(result) == ["ROOM_CONFLICT"]

    assert result["errors"][0]["detail"] == {
        "day": 2,
        "period": "3",
        "with_kind": "course",
        "with_id": "1150001",
        "with_name": "微積分"
    }

    assert "1150002" not in state.courses


# IT03 - Cancel Course Releases Room
@pytest.mark.boundary
def test_cancel_releases_room(state):
    assert add_course(
        state, make_course("1150001")
    )["ok"] is True

    result = cancel_course(state, "1150001")
    assert result["ok"] is True
    assert result["errors"] == []

    result = add_course(state, make_course("1150002"))
    assert result["ok"] is True
    assert result["errors"] == []

    assert state.courses["1150001"]["status"] == "cancelled"


# IT04 - Course In Use Cannot Be Deleted
@pytest.mark.error
def test_delete_course_in_use(state):
    assert add_course(
        state, make_course("1150001")
    )["ok"] is True

    student = {
        "student_id": "115590001",
        "name": "陳小明",
        "department": "資工三甲",
        "credit_limit": 24
    }

    assert add_student(state, student)["ok"] is True
    state.enrollments.add(("115590001", "1150001"))

    result = delete_course(state, "1150001")

    assert result["ok"] is False
    assert codes(result) == ["COURSE_IN_USE"]

    assert result["errors"][0]["detail"] == {
        "course_id": "1150001",
        "enrolled": 1
    }

    assert "1150001" in state.courses


# IT05 - Modify Course Conflict
@pytest.mark.error
def test_modify_course_conflict(state):
    course1 = make_course("1150001", "3")
    course2 = make_course("1150002", "5")

    assert add_course(state, course1)["ok"] is True
    assert add_course(state, course2)["ok"] is True

    result = modify_course(
        state,
        "1150002",
        {"slots": [{"day": 2, "period": "3"}]}
    )

    assert result["ok"] is False
    assert codes(result) == ["ROOM_CONFLICT"]

    assert result["errors"][0]["detail"] == {
        "day": 2,
        "period": "3",
        "with_kind": "course",
        "with_id": "1150001",
        "with_name": "微積分"
    }

    assert state.courses["1150002"]["slots"] == [
        {"day": 2, "period": "5"}
    ]
