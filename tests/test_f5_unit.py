import pytest

from src.f1_data import add_course, add_student, cancel_course
from src.f2_enrollment import enroll
from src.f5_filter import filter_courses


def put_student(state, student_id="115590001", credit_limit=24):
    result = add_student(state, {
        "student_id": student_id, "name": "陳小明",
        "department": "資工三甲", "credit_limit": credit_limit,
    })
    assert result["ok"], result["errors"]


def put_course(state, course_id, slots, room_id="R101", credits=3, capacity=30):
    result = add_course(state, {
        "course_id": course_id, "name": "課" + course_id, "credits": credits,
        "category": "elective", "teacher": "王大明", "capacity": capacity,
        "room_id": room_id, "slots": slots,
    })
    assert result["ok"], result["errors"]


def criteria(**changes):
    base = {"student_id": "115590001", "wanted_courses": [],
            "required_courses": [], "min_credits": 0, "max_credits": 24,
            "blocked_slots": [], "preferred_days": []}
    base.update(changes)
    return base


def ids(rows):
    return [row["course_id"] for row in rows]


@pytest.mark.error
def test_unknown_student_reports_not_found(state):
    result = filter_courses(state, criteria(student_id="115590099"))
    assert result["ok"] is False
    assert [e["code"] for e in result["errors"]] == ["NOT_FOUND"]
    assert result["errors"][0]["detail"] == {
        "kind": "student", "student_id": "115590099"}


@pytest.mark.normal
def test_all_courses_are_candidates_sorted_by_id(state):
    put_student(state)
    put_course(state, "1150002", [{"day": 3, "period": "3"}])
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    result = filter_courses(state, criteria())
    data = result["data"]
    assert result["ok"] is True
    assert ids(data["candidates"]) == ["1150001", "1150002"]
    assert data["candidates"][0] == {
        "course_id": "1150001", "name": "課1150001", "credits": 3,
        "wanted": False, "preferred_day": False}
    assert data["excluded"] == []
    assert data["feasible"] is True


@pytest.mark.error
def test_already_enrolled_course_excluded(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    put_course(state, "1150002", [{"day": 3, "period": "3"}])
    enroll(state, "115590001", "1150001")
    data = filter_courses(state, criteria())["data"]
    assert ids(data["candidates"]) == ["1150002"]
    assert data["excluded"] == [
        {"course_id": "1150001", "reasons": ["ALREADY_ENROLLED"]}]


@pytest.mark.error
def test_cancelled_course_excluded(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    cancel_course(state, "1150001")
    data = filter_courses(state, criteria())["data"]
    assert data["excluded"] == [
        {"course_id": "1150001", "reasons": ["CANCELLED"]}]


@pytest.mark.error
def test_conflict_with_enrolled_course_excluded(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}], room_id="R101")
    put_course(state, "1150002", [{"day": 2, "period": "3"}], room_id="R102")
    enroll(state, "115590001", "1150001")
    data = filter_courses(state, criteria())["data"]
    assert data["excluded"] == [
    {"course_id": "1150001", "reasons": ["ALREADY_ENROLLED"]},
    {"course_id": "1150002", "reasons": ["CONFLICT_ENROLLED"]}]

@pytest.mark.error
def test_full_course_excluded(state):
    put_student(state)
    put_student(state, "115590002")
    put_course(state, "1150001", [{"day": 2, "period": "3"}], capacity=1)
    enroll(state, "115590002", "1150001")
    data = filter_courses(state, criteria())["data"]
    assert data["excluded"] == [{"course_id": "1150001", "reasons": ["FULL"]}]


@pytest.mark.error
def test_blocked_slot_course_excluded(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    data = filter_courses(
        state, criteria(blocked_slots=[{"day": 2, "period": "3"}]))["data"]
    assert data["excluded"] == [
        {"course_id": "1150001", "reasons": ["BLOCKED_SLOT"]}]


@pytest.mark.boundary
def test_blocked_slot_on_other_day_keeps_candidate(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    data = filter_courses(
        state, criteria(blocked_slots=[{"day": 3, "period": "3"}]))["data"]
    assert ids(data["candidates"]) == ["1150001"]


@pytest.mark.boundary
def test_multiple_reasons_listed_in_alphabetical_order(state):
    put_student(state)
    put_student(state, "115590002")
    put_course(state, "1150001", [{"day": 2, "period": "3"}], capacity=1)
    enroll(state, "115590002", "1150001")
    data = filter_courses(
        state, criteria(blocked_slots=[{"day": 2, "period": "3"}]))["data"]
    assert data["excluded"] == [
        {"course_id": "1150001", "reasons": ["BLOCKED_SLOT", "FULL"]}]