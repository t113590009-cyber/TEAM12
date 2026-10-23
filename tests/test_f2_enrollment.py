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
               credits=3, capacity=30):
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

@pytest.mark.error
def test_student_conflict_reports_each_overlapping_slot(state):
    put_student(state)
    both = [{"day": 2, "period": "3"}, {"day": 2, "period": "4"}]
    put_course(state, "1150001", slots=both, room_id="R101")
    put_course(state, "1150002", slots=both, room_id="R102", capacity=30)
    state.enrollments.add(("115590001", "1150001"))
    result = check_enrollment(state, "115590001", "1150002")
    assert result["ok"] is False
    assert [e["code"] for e in result["errors"]] == [
        "STUDENT_CONFLICT", "STUDENT_CONFLICT"]
    assert [(e["detail"]["day"], e["detail"]["period"])
            for e in result["errors"]] == [(2, "3"), (2, "4")]
    assert result["errors"][0]["detail"]["with_id"] == "1150001"


@pytest.mark.boundary
def test_different_day_no_student_conflict(state):
    put_student(state)
    put_course(state, "1150001", slots=[{"day": 2, "period": "3"}])
    put_course(state, "1150002", slots=[{"day": 3, "period": "3"}])
    state.enrollments.add(("115590001", "1150001"))
    result = check_enrollment(state, "115590001", "1150002")
    assert result["ok"] is True
    assert result["errors"] == []


@pytest.mark.boundary
def test_credits_exactly_at_limit_passes(state):
    put_student(state, credit_limit=6)
    put_course(state, "1150001", credits=3)
    put_course(state, "1150002", slots=[{"day": 3, "period": "3"}], credits=3)
    state.enrollments.add(("115590001", "1150001"))
    result = check_enrollment(state, "115590001", "1150002")
    assert result["ok"] is True
    assert result["data"]["current_credits"] == 3
    assert result["data"]["new_credits"] == 6
    assert result["data"]["credit_limit"] == 6


@pytest.mark.error
def test_credit_limit_exceeded_reports_detail(state):
    put_student(state, credit_limit=5)
    put_course(state, "1150001", credits=3)
    put_course(state, "1150002", slots=[{"day": 3, "period": "3"}], credits=3)
    state.enrollments.add(("115590001", "1150001"))
    result = check_enrollment(state, "115590001", "1150002")
    assert [e["code"] for e in result["errors"]] == ["CREDIT_LIMIT_EXCEEDED"]
    assert result["errors"][0]["detail"] == {
        "current": 3, "new": 6, "limit": 5}


@pytest.mark.error
def test_all_errors_listed_conflict_first_then_credit(state):
    put_student(state, credit_limit=5)
    put_course(state, "1150001", credits=3, room_id="R101")
    put_course(state, "1150002", credits=3, room_id="R102", capacity=30)
    state.enrollments.add(("115590001", "1150001"))
    result = check_enrollment(state, "115590001", "1150002")
    assert [e["code"] for e in result["errors"]] == [
        "STUDENT_CONFLICT", "CREDIT_LIMIT_EXCEEDED"]
    assert result["data"]["new_credits"] == 6