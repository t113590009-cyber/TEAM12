import copy
import pytest

from src.f1_data import add_course, add_student
from src.f2_enrollment import check_enrollment, drop, enroll
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

def plant_course(state, source_id, new_id, name="物理"):
    """直接植入一門與來源課程同教室同時段的課(繞過 F1 的檢查)。"""
    course = copy.deepcopy(state.courses[source_id])
    course["course_id"] = new_id
    course["name"] = name
    state.courses[new_id] = course


@pytest.mark.error
def test_room_conflict_reports_conflicting_course(state):
    put_student(state)
    put_course(state, "1150001")
    plant_course(state, "1150001", "1150002")
    result = check_enrollment(state, "115590001", "1150002")
    assert [e["code"] for e in result["errors"]] == ["ROOM_CONFLICT"]
    assert result["errors"][0]["detail"] == {
        "day": 2, "period": "3", "with_kind": "course",
        "with_id": "1150001", "with_name": "微積分"}


@pytest.mark.boundary
def test_room_conflict_ignores_cancelled_course(state):
    put_student(state)
    put_course(state, "1150001")
    plant_course(state, "1150001", "1150002")
    cancel_course(state, "1150001")
    result = check_enrollment(state, "115590001", "1150002")
    assert result["ok"] is True


@pytest.mark.error
def test_room_and_student_conflict_same_slot_sorted_by_code(state):
    put_student(state)
    put_course(state, "1150001")
    plant_course(state, "1150001", "1150002")
    state.enrollments.add(("115590001", "1150001"))
    result = check_enrollment(state, "115590001", "1150002")
    assert [e["code"] for e in result["errors"]] == [
        "ROOM_CONFLICT", "STUDENT_CONFLICT"]


@pytest.mark.error
def test_course_full_reports_detail(state):
    put_student(state)
    put_student(state, "115590002")
    put_course(state, "1150001", capacity=1)
    state.enrollments.add(("115590002", "1150001"))
    result = check_enrollment(state, "115590001", "1150001")
    assert [e["code"] for e in result["errors"]] == ["COURSE_FULL"]
    assert result["errors"][0]["detail"] == {"enrolled": 1, "capacity": 1}


@pytest.mark.boundary
def test_one_seat_left_passes(state):
    put_student(state)
    put_student(state, "115590002")
    put_course(state, "1150001", capacity=2)
    state.enrollments.add(("115590002", "1150001"))
    result = check_enrollment(state, "115590001", "1150001")
    assert result["ok"] is True


@pytest.mark.error
def test_credit_error_listed_before_full_error(state):
    put_student(state, credit_limit=5)
    put_student(state, "115590002")
    put_course(state, "1150001", credits=3)
    put_course(state, "1150002", slots=[{"day": 3, "period": "3"}],
               credits=3, capacity=1)
    state.enrollments.add(("115590001", "1150001"))
    state.enrollments.add(("115590002", "1150002"))
    result = check_enrollment(state, "115590001", "1150002")
    assert [e["code"] for e in result["errors"]] == [
        "CREDIT_LIMIT_EXCEEDED", "COURSE_FULL"]
    
def plant_activity(state, student_id, activity_id="A001", date="2026-10-20",
                   start="10:30", end="10:50", status="active",
                   name="程式設計讀書會"):
    """直接植入一個活動並讓學生報名(F4 還沒做,繞過活動管理)。"""
    state.activities[activity_id] = {
        "activity_id": activity_id, "name": name, "date": date,
        "start_time": start, "end_time": end, "expected_size": 10,
        "activity_type": "study", "min_capacity": 0,
        "required_equipment": [], "room_id": None, "status": status}
    state.activity_signups.add((student_id, activity_id))


@pytest.mark.error
def test_activity_conflict_reports_overlapping_period(state):
    put_student(state)
    put_course(state, "1150001", slots=[{"day": 2, "period": "3"}])
    plant_activity(state, "115590001")
    result = check_enrollment(state, "115590001", "1150001")
    assert [e["code"] for e in result["errors"]] == ["ACTIVITY_CONFLICT"]
    assert result["errors"][0]["detail"] == {
        "day": 2, "period": "3", "with_id": "A001",
        "with_name": "程式設計讀書會"}


@pytest.mark.boundary
def test_activity_on_different_weekday_no_conflict(state):
    put_student(state)
    put_course(state, "1150001", slots=[{"day": 2, "period": "3"}])
    plant_activity(state, "115590001", date="2026-10-21")
    result = check_enrollment(state, "115590001", "1150001")
    assert result["ok"] is True


@pytest.mark.boundary
def test_cancelled_activity_no_conflict(state):
    put_student(state)
    put_course(state, "1150001", slots=[{"day": 2, "period": "3"}])
    plant_activity(state, "115590001", status="cancelled")
    result = check_enrollment(state, "115590001", "1150001")
    assert result["ok"] is True


@pytest.mark.boundary
def test_short_activity_between_periods_no_conflict(state):
    put_student(state)
    put_course(state, "1150001", slots=[{"day": 2, "period": "5"}])
    plant_activity(state, "115590001", start="12:10", end="12:50")
    result = check_enrollment(state, "115590001", "1150001")
    assert result["ok"] is True


@pytest.mark.boundary
def test_other_students_activity_not_counted(state):
    put_student(state)
    put_student(state, "115590002")
    put_course(state, "1150001", slots=[{"day": 2, "period": "3"}])
    plant_activity(state, "115590002")
    result = check_enrollment(state, "115590001", "1150001")
    assert result["ok"] is True

@pytest.mark.normal
def test_enroll_success_adds_enrollment(state):
    put_student(state)
    put_course(state, "1150001")
    result = enroll(state, "115590001", "1150001")
    assert result["ok"] is True
    assert ("115590001", "1150001") in state.enrollments
    assert result["data"]["current_credits"] == 0
    assert result["data"]["new_credits"] == 3


@pytest.mark.error
def test_enroll_failure_keeps_state_unchanged(state):
    put_student(state)
    put_course(state, "1150001", room_id="R101")
    put_course(state, "1150002", room_id="R102", capacity=30)
    state.enrollments.add(("115590001", "1150001"))
    before = set(state.enrollments)
    result = enroll(state, "115590001", "1150002")
    assert [e["code"] for e in result["errors"]] == ["STUDENT_CONFLICT"]
    assert state.enrollments == before


@pytest.mark.error
def test_enroll_unknown_student_not_found_state_unchanged(state):
    put_course(state)
    result = enroll(state, "115590099", "1150001")
    assert [e["code"] for e in result["errors"]] == ["NOT_FOUND"]
    assert state.enrollments == set()


@pytest.mark.boundary
def test_enroll_last_seat_then_next_student_full(state):
    put_student(state)
    put_student(state, "115590002")
    put_course(state, "1150001", capacity=1)
    assert enroll(state, "115590001", "1150001")["ok"] is True
    result = enroll(state, "115590002", "1150001")
    assert [e["code"] for e in result["errors"]] == ["COURSE_FULL"]
    assert state.enrollments == {("115590001", "1150001")}


@pytest.mark.normal
def test_drop_success_removes_enrollment_and_reports_credits(state):
    put_student(state)
    put_course(state, "1150001")
    put_course(state, "1150002", slots=[{"day": 3, "period": "3"}])
    state.enrollments.update({("115590001", "1150001"),
                              ("115590001", "1150002")})
    result = drop(state, "115590001", "1150002")
    assert result["ok"] is True
    assert state.enrollments == {("115590001", "1150001")}
    assert result["data"]["current_credits"] == 3


@pytest.mark.error
def test_drop_not_enrolled_reports_not_enrolled(state):
    put_student(state)
    put_course(state)
    result = drop(state, "115590001", "1150001")
    assert [e["code"] for e in result["errors"]] == ["NOT_ENROLLED"]
    assert result["errors"][0]["detail"] == {
        "student_id": "115590001", "course_id": "1150001"}


@pytest.mark.error
def test_drop_unknown_course_reports_not_found(state):
    put_student(state)
    result = drop(state, "115590001", "1159999")
    assert [e["code"] for e in result["errors"]] == ["NOT_FOUND"]
    assert result["errors"][0]["detail"] == {
        "kind": "course", "course_id": "1159999"}


@pytest.mark.error
def test_drop_unknown_student_reports_not_found(state):
    put_course(state)
    result = drop(state, "115590099", "1150001")
    assert [e["code"] for e in result["errors"]] == ["NOT_FOUND"]
    assert result["errors"][0]["detail"] == {
        "kind": "student", "student_id": "115590099"}


@pytest.mark.normal
def test_enroll_drop_then_enroll_again(state):
    put_student(state)
    put_course(state)
    assert enroll(state, "115590001", "1150001")["ok"] is True
    assert drop(state, "115590001", "1150001")["ok"] is True
    assert state.enrollments == set()
    assert enroll(state, "115590001", "1150001")["ok"] is True