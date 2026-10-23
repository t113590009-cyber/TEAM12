import pytest
from src.f2_enrollment import check_enrollment, drop, enroll


@pytest.mark.error
def test_both_student_and_course_not_found(state):
    result = check_enrollment(
        state, "115590099", "1159999"
    )

    assert result["ok"] is False

    assert [e["code"] for e in result["errors"]] == [
        "NOT_FOUND",
        "NOT_FOUND"
    ]

    assert [e["detail"] for e in result["errors"]] == [
        {"kind": "student", "student_id": "115590099"},
        {"kind": "course", "course_id": "1159999"}
    ]


from src.f2_enrollment import drop


@pytest.mark.error
def test_drop_both_student_and_course_not_found(state):
    before = set(state.enrollments)

    result = drop(state, "115590099", "1159999")

    assert result["ok"] is False

    assert [e["code"] for e in result["errors"]] == [
        "NOT_FOUND",
        "NOT_FOUND"
    ]

    assert [e["detail"] for e in result["errors"]] == [
        {"kind": "student", "student_id": "115590099"},
        {"kind": "course", "course_id": "1159999"}
    ]

    assert state.enrollments == before


from src.f1_data import add_student, add_course


@pytest.mark.normal
def test_check_enrollment_does_not_save_data(state):
    add_student(state, {
        "student_id": "115590001",
        "name": "陳小明",
        "department": "資工三甲",
        "credit_limit": 24
    })

    add_course(state, {
        "course_id": "1150001",
        "name": "微積分",
        "credits": 3,
        "category": "required",
        "teacher": "王大明",
        "capacity": 30,
        "room_id": "R101",
        "slots": [{"day": 2, "period": "3"}]
    })

    result = check_enrollment(
        state, "115590001", "1150001"
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert state.enrollments == set()


from src.common.validators import DEFAULT_CREDIT_LIMIT


@pytest.mark.boundary
def test_enrollment_uses_default_credit_limit(state):
    add_student(state, {
        "student_id": "115590001",
        "name": "陳小明",
        "department": "資工三甲",
        "credit_limit": 24
    })

    add_course(state, {
        "course_id": "1150001",
        "name": "微積分",
        "credits": 3,
        "category": "required",
        "teacher": "王大明",
        "capacity": 30,
        "room_id": "R101",
        "slots": [{"day": 2, "period": "3"}]
    })

    state.students["115590001"].pop("credit_limit", None)

    result = check_enrollment(
        state, "115590001", "1150001"
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["data"]["credit_limit"] == DEFAULT_CREDIT_LIMIT


@pytest.mark.boundary
def test_two_students_fill_course_capacity(state):
    for student_id in ["115590001", "115590002"]:
        result = add_student(state, {
            "student_id": student_id,
            "name": "陳小明",
            "department": "資工三甲",
            "credit_limit": 24
        })
        assert result["ok"] is True

    result = add_course(state, {
        "course_id": "1150001",
        "name": "微積分",
        "credits": 3,
        "category": "required",
        "teacher": "王大明",
        "capacity": 2,
        "room_id": "R101",
        "slots": [{"day": 2, "period": "3"}]
    })
    assert result["ok"] is True

    first = enroll(state, "115590001", "1150001")
    second = enroll(state, "115590002", "1150001")

    assert first["ok"] is True
    assert second["ok"] is True
    assert first["errors"] == []
    assert second["errors"] == []

    assert state.enrollments == {
        ("115590001", "1150001"),
        ("115590002", "1150001")
    }


from src.f1_data import cancel_course


@pytest.mark.error
def test_enroll_cancelled_course_keeps_state_unchanged(state):
    add_student(state, {
        "student_id": "115590001",
        "name": "陳小明",
        "department": "資工三甲",
        "credit_limit": 24
    })

    add_course(state, {
        "course_id": "1150001",
        "name": "微積分",
        "credits": 3,
        "category": "required",
        "teacher": "王大明",
        "capacity": 30,
        "room_id": "R101",
        "slots": [{"day": 2, "period": "3"}]
    })

    cancel_course(state, "1150001")

    before = set(state.enrollments)

    result = enroll(state, "115590001", "1150001")

    assert result["ok"] is False
    assert [e["code"] for e in result["errors"]] == [
        "COURSE_CANCELLED"
    ]
    assert result["errors"][0]["detail"] == {
        "course_id": "1150001"
    }
    assert state.enrollments == before