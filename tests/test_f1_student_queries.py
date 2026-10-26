import pytest

from src.f1_data import (add_course, add_student, cancel_course, get_student_courses,
                         get_student_credits)


def make_course(**override):
    course = {"course_id": "1150001", "name": "微積分", "credits": 3, "category": "required",
              "teacher": "王大明", "capacity": 30, "room_id": "R101",
              "slots": [{"day": 2, "period": "3"}]}
    course.update(override)
    return course


def make_student(**override):
    student = {"student_id": "115590001", "name": "陳小明", "department": "資工三甲", "credit_limit": 24}
    student.update(override)
    return student


def setup_student_with_two_courses(state):
    add_student(state, make_student())
    add_course(state, make_course())
    add_course(state, make_course(course_id="1150002", credits=2, slots=[{"day": 3, "period": "1"}]))
    state.enrollments.update({("115590001", "1150002"), ("115590001", "1150001")})


@pytest.mark.normal
def test_get_student_courses_sorted(state):
    setup_student_with_two_courses(state)
    res = get_student_courses(state, "115590001")
    assert res["ok"] is True and res["data"] == ["1150001", "1150002"]


@pytest.mark.normal
def test_get_student_credits_sums_active_courses(state):
    setup_student_with_two_courses(state)
    res = get_student_credits(state, "115590001")
    assert res["ok"] is True and res["data"] == 5


@pytest.mark.boundary
def test_student_without_enrollments_returns_empty_and_zero(state):
    add_student(state, make_student())
    assert get_student_courses(state, "115590001")["data"] == []
    assert get_student_credits(state, "115590001")["data"] == 0


@pytest.mark.boundary
def test_other_students_enrollments_not_counted(state):
    setup_student_with_two_courses(state)
    add_student(state, make_student(student_id="115590002"))
    state.enrollments.add(("115590002", "1150001"))
    assert get_student_courses(state, "115590002")["data"] == ["1150001"]
    assert get_student_credits(state, "115590002")["data"] == 3


@pytest.mark.boundary
def test_cancelled_course_not_listed_or_counted(state):
    setup_student_with_two_courses(state)
    state.courses["1150002"]["status"] = "cancelled"
    assert get_student_courses(state, "115590001")["data"] == ["1150001"]
    assert get_student_credits(state, "115590001")["data"] == 3


@pytest.mark.boundary
def test_cancel_course_removes_it_from_student_courses(state):
    setup_student_with_two_courses(state)
    cancel_course(state, "1150001")
    assert get_student_courses(state, "115590001")["data"] == ["1150002"]
    assert get_student_credits(state, "115590001")["data"] == 2


@pytest.mark.error
def test_get_student_courses_student_not_found(state):
    res = get_student_courses(state, "115590009")
    assert res["ok"] is False and [e["code"] for e in res["errors"]] == ["NOT_FOUND"]
    assert res["errors"][0]["detail"]["student_id"] == "115590009"


@pytest.mark.error
def test_get_student_credits_student_not_found(state):
    res = get_student_credits(state, "115590009")
    assert res["ok"] is False and [e["code"] for e in res["errors"]] == ["NOT_FOUND"]
