"""F4 活動與教室測試（正常、邊界、錯誤三類）。

fixture state：R101（容量 60、projector）、R102（容量 30、無設備）。
2026-10-15 為星期四；15:10～16:00 為第 7 節。
"""
import copy

import pytest

from src.f1_data import add_course, add_room, add_student, cancel_course
from src.f2_enrollment import check_enrollment
from src.f4_activity import (activity_capacity, add_activity, assign_room, cancel_activity,
                             cancel_signup, check_signup, find_suitable_rooms,
                             get_activity_signups, modify_activity, query_activities,
                             signup_activity)

THURSDAY = "2026-10-15"
NEXT_THURSDAY = "2026-10-22"


def activity_data(activity_id="A001", **overrides):
    data = {"activity_id": activity_id, "name": "程式設計讀書會", "date": THURSDAY,
            "start_time": "15:10", "end_time": "16:00", "expected_size": 20,
            "activity_type": "study"}
    data.update(overrides)
    return data


def put_activity(state, activity_id="A001", **overrides):
    result = add_activity(state, activity_data(activity_id, **overrides))
    assert result["ok"], result["errors"]
    return result["data"]


def put_student(state, student_id="115590001"):
    result = add_student(state, {"student_id": student_id, "name": "陳小明",
                                 "department": "資工三甲"})
    assert result["ok"], result["errors"]


def put_course(state, course_id="1150001", day=4, period="7", room_id="R101"):
    result = add_course(state, {"course_id": course_id, "name": "微積分", "credits": 3,
                                "category": "required", "teacher": "王大明", "capacity": 20,
                                "room_id": room_id, "slots": [{"day": day, "period": period}]})
    assert result["ok"], result["errors"]


def codes(result):
    return [e["code"] for e in result["errors"]]


# ---------- 新增與欄位驗證 ----------

@pytest.mark.normal
def test_add_activity_stores_normalized_defaults(state):
    result = add_activity(state, activity_data())
    assert result["ok"] is True
    assert state.activities["A001"] == {
        **activity_data(), "min_capacity": 0, "required_equipment": [],
        "room_id": None, "status": "active"}


@pytest.mark.normal
def test_add_activity_returns_copy_not_stored_object(state):
    result = add_activity(state, activity_data())
    result["data"]["name"] = "改掉"
    assert state.activities["A001"]["name"] == "程式設計讀書會"


@pytest.mark.boundary
def test_activity_may_span_whole_day_08_10_to_21_10(state):
    result = add_activity(state, activity_data(start_time="08:10", end_time="21:10"))
    assert result["ok"] is True


@pytest.mark.error
@pytest.mark.parametrize("activity_id", ["a001", "A01", "A0001", "R101", 1])
def test_invalid_activity_id_format(state, activity_id):
    result = add_activity(state, activity_data(activity_id))
    assert codes(result) == ["INVALID_ID_FORMAT"]


@pytest.mark.error
def test_duplicate_activity_id(state):
    put_activity(state)
    result = add_activity(state, activity_data(start_time="18:30", end_time="19:20"))
    assert codes(result) == ["DUPLICATE_ID"]


@pytest.mark.error
@pytest.mark.parametrize("date", ["2026-02-30", "2026/10/15", "20261015", None])
def test_invalid_date(state, date):
    result = add_activity(state, activity_data(date=date))
    assert codes(result) == ["INVALID_DATE"]


@pytest.mark.error
@pytest.mark.parametrize("start, end", [("08:00", "09:00"), ("20:30", "21:20"),
                                        ("16:00", "15:10"), ("15:10", "15:10")])
def test_time_out_of_range_or_reversed(state, start, end):
    result = add_activity(state, activity_data(start_time=start, end_time=end))
    assert codes(result) == ["INVALID_TIME"]
    assert result["errors"][0]["detail"] == {"start_time": start, "end_time": end}


@pytest.mark.error
def test_bad_time_format_reports_each_field(state):
    result = add_activity(state, activity_data(start_time="8:10", end_time="25:00"))
    assert codes(result) == ["INVALID_TIME", "INVALID_TIME"]
    assert [e["detail"]["field"] for e in result["errors"]] == ["start_time", "end_time"]


@pytest.mark.error
@pytest.mark.parametrize("size", [0, -1, True, 2.5, "20"])
def test_invalid_expected_size(state, size):
    result = add_activity(state, activity_data(expected_size=size))
    assert codes(result) == ["INVALID_CAPACITY"]


@pytest.mark.error
def test_unknown_room_reports_not_found(state):
    result = add_activity(state, activity_data(room_id="R999"))
    assert codes(result) == ["NOT_FOUND"]
    assert result["errors"][0]["detail"] == {"room_id": "R999"}


@pytest.mark.error
def test_validation_reports_all_errors_at_once(state):
    result = add_activity(state, activity_data(
        "X1", name=" ", date="2026-13-01", start_time="22:00", end_time="23:00",
        expected_size=0, min_capacity=-1, required_equipment=["Projector"]))
    assert sorted(codes(result)) == sorted([
        "INVALID_ID_FORMAT", "INVALID_FIELD", "INVALID_DATE", "INVALID_TIME",
        "INVALID_CAPACITY", "INVALID_CAPACITY", "INVALID_FIELD"])
    assert state.activities == {}


# ---------- 教室衝突（場地衝突） ----------

@pytest.mark.error
def test_room_conflict_with_course_compares_periods(state):
    put_course(state, day=4, period="7")
    result = add_activity(state, activity_data(room_id="R101", start_time="15:30",
                                               end_time="15:50"))
    assert codes(result) == ["ROOM_CONFLICT"]
    assert result["errors"][0]["detail"] == {
        "day": 4, "period": "7", "with_kind": "course",
        "with_id": "1150001", "with_name": "微積分"}


@pytest.mark.error
def test_room_conflict_with_activity_same_date(state):
    put_activity(state, room_id="R101")
    result = add_activity(state, activity_data("A002", room_id="R101",
                                               start_time="15:50", end_time="17:00"))
    assert codes(result) == ["ROOM_CONFLICT"]
    assert result["errors"][0]["detail"] == {
        "date": THURSDAY, "start_time": "15:10", "end_time": "16:00",
        "with_kind": "activity", "with_id": "A001", "with_name": "程式設計讀書會"}


@pytest.mark.error
def test_short_break_activity_conflicts_with_activity_not_course(state):
    """16:00～16:10 是下課時間，不佔任何節次：不與課程衝突，但仍與同日活動衝突。"""
    put_course(state, day=4, period="7")
    put_course(state, "1150002", day=4, period="8")
    put_activity(state, "A001", room_id="R102", start_time="15:50", end_time="16:05")
    short = activity_data("A002", start_time="16:00", end_time="16:10")
    assert add_activity(state, {**short, "room_id": "R101"})["ok"] is True
    result = add_activity(state, {**short, "activity_id": "A003", "room_id": "R102"})
    assert codes(result) == ["ROOM_CONFLICT"]
    assert result["errors"][0]["detail"]["with_id"] == "A001"


@pytest.mark.boundary
def test_same_weekday_different_date_no_conflict(state):
    put_activity(state, room_id="R101")
    result = add_activity(state, activity_data("A002", date=NEXT_THURSDAY, room_id="R101"))
    assert result["ok"] is True


@pytest.mark.boundary
def test_back_to_back_activities_in_same_room_no_conflict(state):
    put_activity(state, room_id="R101", start_time="13:10", end_time="14:00")
    result = add_activity(state, activity_data("A002", room_id="R101",
                                               start_time="14:00", end_time="15:00"))
    assert result["ok"] is True


@pytest.mark.boundary
def test_cancelled_course_does_not_block_room(state):
    put_course(state, day=4, period="7")
    cancel_course(state, "1150001")
    assert add_activity(state, activity_data(room_id="R101"))["ok"] is True


# ---------- 取消 ----------

@pytest.mark.normal
def test_cancel_keeps_record_and_releases_room(state):
    put_activity(state, room_id="R101")
    result = cancel_activity(state, "A001")
    assert result["ok"] is True
    assert state.activities["A001"]["status"] == "cancelled"
    assert add_activity(state, activity_data("A002", room_id="R101"))["ok"] is True


@pytest.mark.boundary
def test_cancel_twice_is_success_and_removes_signups(state):
    put_activity(state)
    put_student(state)
    signup_activity(state, "115590001", "A001")
    first = cancel_activity(state, "A001")
    second = cancel_activity(state, "A001")
    assert first["data"]["removed_students"] == ["115590001"]
    assert second["ok"] is True and second["data"]["removed_students"] == []
    assert state.activity_signups == set()


@pytest.mark.error
def test_cancel_unknown_activity(state):
    result = cancel_activity(state, "A999")
    assert codes(result) == ["NOT_FOUND"]
    assert result["errors"][0]["detail"] == {"kind": "activity", "activity_id": "A999"}


# ---------- 修改 ----------

@pytest.mark.normal
def test_modify_time_and_size(state):
    put_activity(state)
    result = modify_activity(state, "A001", {"start_time": "18:30", "end_time": "20:00",
                                             "expected_size": 25})
    assert result["ok"] is True
    assert state.activities["A001"]["start_time"] == "18:30"
    assert state.activities["A001"]["expected_size"] == 25


@pytest.mark.error
def test_modify_revalidates_and_keeps_state_on_error(state):
    put_activity(state)
    before = copy.deepcopy(state.activities)
    result = modify_activity(state, "A001", {"end_time": "21:30"})
    assert codes(result) == ["INVALID_TIME"]
    assert state.activities == before


@pytest.mark.error
def test_modify_cannot_change_id_or_status(state):
    put_activity(state)
    result = modify_activity(state, "A001", {"activity_id": "A002", "status": "cancelled"})
    assert codes(result) == ["INVALID_FIELD", "INVALID_FIELD"]


@pytest.mark.boundary
def test_modify_expected_size_equal_to_signups_ok_below_fails(state):
    put_activity(state, expected_size=5)
    for i in range(2):
        put_student(state, f"11559000{i + 1}")
        assert signup_activity(state, f"11559000{i + 1}", "A001")["ok"]
    assert modify_activity(state, "A001", {"expected_size": 2})["ok"] is True
    result = modify_activity(state, "A001", {"expected_size": 1})
    assert codes(result) == ["CAPACITY_BELOW_ENROLLED"]
    assert result["errors"][0]["detail"] == {
        "enrolled": 2, "new_capacity": 1, "students": ["115590001", "115590002"]}


@pytest.mark.error
def test_modify_time_causing_signed_student_conflict(state):
    put_activity(state, start_time="18:30", end_time="19:20")
    put_student(state)
    put_course(state, day=4, period="7")
    state.enrollments.add(("115590001", "1150001"))
    signup_activity(state, "115590001", "A001")
    result = modify_activity(state, "A001", {"start_time": "15:10", "end_time": "16:00"})
    assert codes(result) == ["STUDENT_CONFLICT"]
    assert result["errors"][0]["detail"] == {"conflict_students": ["115590001"]}


@pytest.mark.error
def test_modify_room_into_conflict(state):
    put_course(state, day=4, period="7", room_id="R101")
    put_activity(state, room_id="R102")
    result = modify_activity(state, "A001", {"room_id": "R101"})
    assert codes(result) == ["ROOM_CONFLICT"]
    assert state.activities["A001"]["room_id"] == "R102"


# ---------- 查詢 ----------

@pytest.mark.normal
def test_query_by_date_sorted_and_excludes_cancelled(state):
    put_activity(state, "A003", start_time="18:30", end_time="19:20")
    put_activity(state, "A001", start_time="10:10", end_time="11:00")
    put_activity(state, "A002", date=NEXT_THURSDAY)
    put_activity(state, "A004", start_time="13:10", end_time="14:00")
    cancel_activity(state, "A004")
    result = query_activities(state, {"date": THURSDAY})
    assert [a["activity_id"] for a in result["data"]] == ["A001", "A003"]
    every = query_activities(state, include_cancelled=True)
    assert [a["activity_id"] for a in every["data"]] == ["A001", "A004", "A003", "A002"]


@pytest.mark.boundary
def test_query_unassigned_room_and_empty_result(state):
    put_activity(state, "A001")
    put_activity(state, "A002", room_id="R101", date=NEXT_THURSDAY)
    assert [a["activity_id"] for a in query_activities(state, {"room_id": None})["data"]] == ["A001"]
    assert query_activities(state, {"activity_type": "talk"}) == {"ok": True, "data": [], "errors": []}


@pytest.mark.error
def test_query_rejects_unknown_filter_and_bad_date(state):
    result = query_activities(state, {"teacher": "王大明", "date": "2026-02-30"})
    assert codes(result) == ["INVALID_FIELD", "INVALID_DATE"]


# ---------- 教室篩選與配置 ----------

def add_rooms(state):
    """補兩間：R103（容量 25、projector）、R104（容量 100、projector + computer）。"""
    add_room(state, {"room_id": "R103", "building": "三教", "capacity": 25, "equipment": ["projector"]})
    add_room(state, {"room_id": "R104", "building": "三教", "capacity": 100,
                     "equipment": ["computer", "projector"]})


@pytest.mark.normal
def test_find_rooms_filters_equipment_and_sorts_by_capacity(state):
    add_rooms(state)
    put_activity(state, expected_size=20, required_equipment=["projector"])
    result = find_suitable_rooms(state, "A001")
    assert [r["room_id"] for r in result["data"]] == ["R103", "R101", "R104"]


@pytest.mark.boundary
def test_find_rooms_uses_max_of_min_capacity_and_expected_size(state):
    add_rooms(state)
    put_activity(state, expected_size=10, min_capacity=30)
    result = find_suitable_rooms(state, "A001")
    assert [r["room_id"] for r in result["data"]] == ["R102", "R101", "R104"]


@pytest.mark.normal
def test_find_rooms_skips_rooms_used_by_course_or_activity(state):
    add_rooms(state)
    put_course(state, day=4, period="7", room_id="R103")
    put_activity(state, "A002", room_id="R102", start_time="15:30", end_time="16:30")
    put_activity(state, "A001")
    result = find_suitable_rooms(state, "A001")
    assert [r["room_id"] for r in result["data"]] == ["R101", "R104"]


@pytest.mark.error
def test_no_suitable_room_lists_unmet_conditions(state):
    put_course(state, day=4, period="7", room_id="R101")
    put_activity(state, expected_size=40, required_equipment=["projector"])
    result = find_suitable_rooms(state, "A001")
    assert codes(result) == ["NO_SUITABLE_ROOM"]
    assert result["data"] == []
    assert result["errors"][0]["detail"] == {"activity_id": "A001", "rooms": [
        {"room_id": "R101", "capacity": 60, "unmet": ["course_conflict"], "missing_equipment": []},
        {"room_id": "R102", "capacity": 30, "unmet": ["capacity", "equipment"],
         "missing_equipment": ["projector"]}]}


@pytest.mark.normal
def test_assign_room_picks_smallest_suitable(state):
    add_rooms(state)
    put_activity(state, expected_size=20)
    result = assign_room(state, "A001")
    assert result["ok"] is True
    assert state.activities["A001"]["room_id"] == "R103"


@pytest.mark.error
def test_assign_room_on_cancelled_or_missing_activity(state):
    put_activity(state)
    cancel_activity(state, "A001")
    assert codes(assign_room(state, "A001")) == ["COURSE_CANCELLED"]
    assert codes(assign_room(state, "A999")) == ["NOT_FOUND"]


# ---------- 報名 ----------

@pytest.mark.normal
def test_multiple_students_sign_up(state):
    put_activity(state, room_id="R101")
    for i in range(3):
        put_student(state, f"11559000{i + 1}")
        result = signup_activity(state, f"11559000{i + 1}", "A001")
        assert result["ok"] is True
        assert result["data"]["enrolled"] == i + 1
    assert get_activity_signups(state, "A001") == ["115590001", "115590002", "115590003"]


@pytest.mark.boundary
def test_activity_full_by_expected_size_last_seat_ok(state):
    put_activity(state, expected_size=2)
    for sid in ("115590001", "115590002", "115590003"):
        put_student(state, sid)
    assert signup_activity(state, "115590001", "A001")["ok"]
    assert signup_activity(state, "115590002", "A001")["ok"]
    result = signup_activity(state, "115590003", "A001")
    assert codes(result) == ["ACTIVITY_FULL"]
    assert result["errors"][0]["detail"] == {"enrolled": 2, "capacity": 2}


@pytest.mark.boundary
def test_capacity_limited_by_room(state):
    """教室額滿：預計 40 人，但 R102 只容納 30 人，報名容量為 30。"""
    activity = put_activity(state, expected_size=40, room_id="R102")
    assert activity_capacity(state, activity) == 30
    state.activity_signups.update({(f"1155900{i:02d}", "A001") for i in range(30)})
    put_student(state, "115590099")
    result = check_signup(state, "115590099", "A001")
    assert codes(result) == ["ACTIVITY_FULL"]
    assert result["errors"][0]["detail"] == {"enrolled": 30, "capacity": 30}


@pytest.mark.error
def test_signup_conflicts_with_enrolled_course(state):
    put_course(state, day=4, period="7")
    put_student(state)
    state.enrollments.add(("115590001", "1150001"))
    put_activity(state)
    result = signup_activity(state, "115590001", "A001")
    assert codes(result) == ["ACTIVITY_CONFLICT"]
    assert result["errors"][0]["detail"] == {
        "day": 4, "period": "7", "with_kind": "course",
        "with_id": "1150001", "with_name": "微積分"}
    assert state.activity_signups == set()


@pytest.mark.error
def test_signup_conflicts_with_other_activity_and_full_reports_all(state):
    put_student(state)
    put_student(state, "115590002")
    put_activity(state, "A001")
    put_activity(state, "A002", start_time="15:50", end_time="16:05", expected_size=1)
    signup_activity(state, "115590001", "A001")
    signup_activity(state, "115590002", "A002")
    result = check_signup(state, "115590001", "A002")
    assert codes(result) == ["ACTIVITY_CONFLICT", "ACTIVITY_FULL"]
    assert result["errors"][0]["detail"]["with_id"] == "A001"


@pytest.mark.boundary
def test_same_weekday_different_date_signup_no_conflict(state):
    put_student(state)
    put_activity(state, "A001")
    put_activity(state, "A002", date=NEXT_THURSDAY)
    assert signup_activity(state, "115590001", "A001")["ok"]
    assert signup_activity(state, "115590001", "A002")["ok"]


@pytest.mark.boundary
def test_short_break_activity_does_not_conflict_with_course(state):
    put_course(state, day=4, period="7")
    put_course(state, "1150002", day=4, period="8")
    put_student(state)
    state.enrollments.update({("115590001", "1150001"), ("115590001", "1150002")})
    put_activity(state, start_time="16:00", end_time="16:10")
    assert signup_activity(state, "115590001", "A001")["ok"] is True


@pytest.mark.error
def test_signup_prechecks(state):
    put_student(state)
    put_activity(state)
    assert codes(signup_activity(state, "115590099", "A999")) == ["NOT_FOUND", "NOT_FOUND"]
    assert signup_activity(state, "115590001", "A001")["ok"]
    assert codes(signup_activity(state, "115590001", "A001")) == ["ALREADY_ENROLLED"]
    cancel_activity(state, "A001")
    result = signup_activity(state, "115590001", "A001")
    assert codes(result) == ["COURSE_CANCELLED"]
    assert result["errors"][0]["detail"] == {"kind": "activity", "activity_id": "A001"}


@pytest.mark.normal
def test_cancel_signup(state):
    put_student(state)
    put_activity(state)
    signup_activity(state, "115590001", "A001")
    result = cancel_signup(state, "115590001", "A001")
    assert result["ok"] is True and result["data"]["enrolled"] == 0
    assert codes(cancel_signup(state, "115590001", "A001")) == ["NOT_ENROLLED"]


@pytest.mark.normal
def test_signed_activity_blocks_f2_enrollment(state):
    """F4 報名後，F2 加選同節次課程應回 ACTIVITY_CONFLICT（F2、F4 整合）。"""
    put_student(state)
    put_activity(state)
    signup_activity(state, "115590001", "A001")
    put_course(state, day=4, period="7", room_id="R102")
    result = check_enrollment(state, "115590001", "1150001")
    assert codes(result) == ["ACTIVITY_CONFLICT"]
