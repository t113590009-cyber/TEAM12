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

@pytest.mark.normal
def test_wanted_courses_listed_first(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    put_course(state, "1150002", [{"day": 3, "period": "3"}])
    put_course(state, "1150003", [{"day": 4, "period": "3"}])
    data = filter_courses(state, criteria(wanted_courses=["1150003"]))["data"]
    assert ids(data["candidates"]) == ["1150003", "1150001", "1150002"]
    assert data["candidates"][0]["wanted"] is True


@pytest.mark.normal
def test_preferred_day_courses_listed_before_others(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    put_course(state, "1150002", [{"day": 3, "period": "3"}])
    data = filter_courses(state, criteria(preferred_days=[3]))["data"]
    assert ids(data["candidates"]) == ["1150002", "1150001"]
    assert data["candidates"][0]["preferred_day"] is True
    assert data["candidates"][1]["preferred_day"] is False


@pytest.mark.normal
def test_wanted_before_preferred_before_course_id(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    put_course(state, "1150002", [{"day": 3, "period": "3"}])
    put_course(state, "1150003", [{"day": 4, "period": "3"}])
    data = filter_courses(
        state, criteria(wanted_courses=["1150003"], preferred_days=[3]))["data"]
    assert ids(data["candidates"]) == ["1150003", "1150002", "1150001"]


@pytest.mark.boundary
def test_preferred_day_needs_all_slots_on_preferred_days(state):
    put_student(state)
    put_course(state, "1150001",
               [{"day": 2, "period": "3"}, {"day": 3, "period": "3"}])
    put_course(state, "1150002", [{"day": 2, "period": "4"}])
    data = filter_courses(state, criteria(preferred_days=[2]))["data"]
    flags = {row["course_id"]: row["preferred_day"]
             for row in data["candidates"]}
    assert flags == {"1150001": False, "1150002": True}

@pytest.mark.error
def test_min_greater_than_max_reports_contradiction(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    result = filter_courses(state, criteria(min_credits=20, max_credits=15))
    assert result["ok"] is False
    assert [e["code"] for e in result["errors"]] == ["CONSTRAINT_CONTRADICTION"]
    assert result["errors"][0]["detail"] == {
        "reason": "MIN_GT_MAX", "min_credits": 20, "max_credits": 15}
    assert result["data"]["feasible"] is False
    assert ids(result["data"]["candidates"]) == ["1150001"]


@pytest.mark.error
def test_max_credits_is_limited_by_student_credit_limit(state):
    put_student(state, credit_limit=6)
    result = filter_courses(state, criteria(min_credits=8, max_credits=30))
    assert result["errors"][0]["detail"] == {
        "reason": "MIN_GT_MAX", "min_credits": 8, "max_credits": 6}


@pytest.mark.boundary
def test_min_equal_max_is_not_contradiction(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    result = filter_courses(state, criteria(min_credits=3, max_credits=3))
    assert result["ok"] is True
    assert result["data"]["feasible"] is True


@pytest.mark.error
def test_required_courses_conflict_with_each_other(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}], room_id="R101")
    put_course(state, "1150002", [{"day": 2, "period": "3"}], room_id="R102")
    result = filter_courses(
        state, criteria(required_courses=["1150002", "1150001"]))
    assert [e["detail"] for e in result["errors"]] == [
        {"reason": "REQUIRED_CONFLICT",
         "course_id": "1150001", "with_id": "1150002"}]


@pytest.mark.error
def test_required_conflicts_with_enrolled_course(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}], room_id="R101")
    put_course(state, "1150002", [{"day": 2, "period": "3"}], room_id="R102")
    enroll(state, "115590001", "1150001")
    result = filter_courses(state, criteria(required_courses=["1150002"]))
    assert [e["detail"] for e in result["errors"]] == [
        {"reason": "REQUIRED_ENROLLED_CONFLICT", "course_id": "1150002"}]


@pytest.mark.error
def test_required_course_in_blocked_slot(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    result = filter_courses(state, criteria(
        required_courses=["1150001"],
        blocked_slots=[{"day": 2, "period": "3"}]))
    assert [e["detail"] for e in result["errors"]] == [
        {"reason": "REQUIRED_BLOCKED", "course_id": "1150001"}]


@pytest.mark.error
def test_required_course_full(state):
    put_student(state)
    put_student(state, "115590002")
    put_course(state, "1150001", [{"day": 2, "period": "3"}], capacity=1)
    enroll(state, "115590002", "1150001")
    result = filter_courses(state, criteria(required_courses=["1150001"]))
    assert [e["detail"] for e in result["errors"]] == [
        {"reason": "REQUIRED_FULL", "course_id": "1150001"}]


@pytest.mark.error
def test_required_credits_over_max(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    put_course(state, "1150002", [{"day": 3, "period": "3"}])
    result = filter_courses(state, criteria(
        required_courses=["1150001", "1150002"], max_credits=5))
    assert [e["detail"] for e in result["errors"]] == [
        {"reason": "REQUIRED_OVER_MAX", "total_credits": 6, "max_credits": 5}]


@pytest.mark.boundary
def test_enrolled_required_course_is_not_a_contradiction(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}])
    enroll(state, "115590001", "1150001")
    result = filter_courses(state, criteria(required_courses=["1150001"]))
    assert result["ok"] is True
    assert result["data"]["feasible"] is True


@pytest.mark.error
def test_all_contradictions_listed_together_in_fixed_order(state):
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}], room_id="R101")
    put_course(state, "1150002", [{"day": 2, "period": "3"}], room_id="R102")
    result = filter_courses(state, criteria(
        required_courses=["1150001", "1150002"], min_credits=10,
        max_credits=5, blocked_slots=[{"day": 2, "period": "3"}]))
    assert [e["detail"]["reason"] for e in result["errors"]] == [
        "MIN_GT_MAX", "REQUIRED_CONFLICT", "REQUIRED_BLOCKED",
        "REQUIRED_BLOCKED", "REQUIRED_OVER_MAX"]

@pytest.mark.error
def test_min_credit_unreachable_reports_contradiction(state):
    """候選課程學分總和低於學分下限，回報 MIN_CREDIT_UNREACHABLE 且 feasible 為 False。"""
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}], credits=3)
    result = filter_courses(state, criteria(min_credits=5))
    assert result["ok"] is False
    assert [e["code"] for e in result["errors"]] == ["CONSTRAINT_CONTRADICTION"]
    assert result["errors"][0]["detail"] == {
        "reason": "MIN_CREDIT_UNREACHABLE", "min_credits": 5, "max_possible": 3}
    assert result["data"]["feasible"] is False
    # 仍保留候選清單供使用者參考
    assert ids(result["data"]["candidates"]) == ["1150001"]
@pytest.mark.error
def test_min_credit_unreachable_considers_enrolled_credits(state):
    """計算學分上限時需包含已選課程學分。"""
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}], credits=3)
    put_course(state, "1150002", [{"day": 3, "period": "3"}], credits=3)
    enroll(state, "115590001", "1150001")  # 已選 3 學分
    result = filter_courses(state, criteria(min_credits=8))  # 已選 3 + 候選 3 = 6 < 8
    assert [e["detail"] for e in result["errors"]] == [
        {"reason": "MIN_CREDIT_UNREACHABLE", "min_credits": 8, "max_possible": 6}]
    assert result["data"]["feasible"] is False
@pytest.mark.boundary
def test_min_credit_reachable_when_equal(state):
    """已選學分加候選課程學分剛好等於 min_credits 時為可行，不回報矛盾。"""
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}], credits=3)
    put_course(state, "1150002", [{"day": 3, "period": "3"}], credits=3)
    result = filter_courses(state, criteria(min_credits=6))  # 剛好等於 6
    assert result["ok"] is True
    assert result["errors"] == []
    assert result["data"]["feasible"] is True
@pytest.mark.error
def test_excluded_courses_do_not_count_towards_max_possible(state):
    """被排除的課程（例如衝堂、額滿）不應計入可能達到的學分上限。"""
    put_student(state)
    put_course(state, "1150001", [{"day": 2, "period": "3"}], credits=3)
    # 這裡加上 room_id="R102"，避免同教室衝堂
    put_course(state, "1150002", [{"day": 2, "period": "3"}], room_id="R102", credits=3)
    enroll(state, "115590001", "1150001")  # 已選 0001，0002 被排除（CONFLICT_ENROLLED）
    # 目前已選 3 學分，候選 0 學分，上限為 3
    result = filter_courses(state, criteria(min_credits=5))
    assert [e["detail"] for e in result["errors"]] == [
        {"reason": "MIN_CREDIT_UNREACHABLE", "min_credits": 5, "max_possible": 3}]
    assert result["data"]["feasible"] is False