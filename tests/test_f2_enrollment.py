import pytest

from src.f1_data import add_course, add_student
from src.f2_enrollment import check_enrollment
from src.f1_data import add_course, add_student, cancel_course


def put_student(state, student_id="115590001", credit_limit=24):
    result = add_student(state, {
        "student_id": student_id, "name": "陳小明",
        "department": "資工三甲", "credit_limit": credit_limit,
    })
    assert result["ok"], result["errors"]


def put_course(state, course_id="1150001", slots=None, room_id="R101",
               credits=3, capacity=50):
    result = add_course(state, {
        "course_id": course_id, "name": "微積分", "credits": credits,
        "category": "required", "teacher": "王大明", "capacity": capacity,
        "room_id": room_id,
        "slots": slots if slots is not None else [{"day": 2, "period": "3"}],
    })
    assert result["ok"], result["errors"]


@pytest.mark.error
def test_unknown_student_reports_not_found(state):
    put_course(state)
    result = check_enrollment(state, "115590099", "1150001")
    assert result["ok"] is False
    assert [e["code"] for e in result["errors"]] == ["NOT_FOUND"]
    assert result["errors"][0]["detail"] == {
        "kind": "student", "student_id": "115590099"}


@pytest.mark.error
def test_unknown_course_reports_not_found(state):
    put_student(state)
    result = check_enrollment(state, "115590001", "1159999")
    assert [e["code"] for e in result["errors"]] == ["NOT_FOUND"]
    assert result["errors"][0]["detail"] == {
        "kind": "course", "course_id": "1159999"}

@pytest.mark.error
def test_cancelled_course_reports_course_cancelled(state):
    put_student(state)
    put_course(state)
    cancel_course(state, "1150001")
    result = check_enrollment(state, "115590001", "1150001")
    assert result["ok"] is False
    assert [e["code"] for e in result["errors"]] == ["COURSE_CANCELLED"]
    assert result["errors"][0]["detail"] == {"course_id": "1150001"}


@pytest.mark.error
def test_already_enrolled_reports_already_enrolled(state):
    put_student(state)
    put_course(state)
    state.enrollments.add(("115590001", "1150001"))
    result = check_enrollment(state, "115590001", "1150001")
    assert result["ok"] is False
    assert [e["code"] for e in result["errors"]] == ["ALREADY_ENROLLED"]
    assert result["errors"][0]["detail"] == {
        "student_id": "115590001", "course_id": "1150001"}


@pytest.mark.error
def test_precheck_failure_returns_only_not_found(state):
    put_course(state)
    cancel_course(state, "1150001")
    result = check_enrollment(state, "115590099", "1150001")
    assert [e["code"] for e in result["errors"]] == ["NOT_FOUND"]