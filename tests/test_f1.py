import pytest

from src.f1_data import (add_course, add_room, add_student, cancel_course, delete_course,
                         delete_room, delete_student, list_course_students, modify_course,
                         query_courses)
from tests.sample_data import build_sample_state, plant_room_conflict


def make_course(**override):
    course = {"course_id": "1150001", "name": "微積分", "credits": 3, "category": "required",
              "teacher": "王大明", "capacity": 30, "room_id": "R101",
              "slots": [{"day": 2, "period": "3"}, {"day": 2, "period": "4"}]}
    course.update(override)
    return course


def make_student(**override):
    student = {"student_id": "115590001", "name": "陳小明", "department": "資工三甲", "credit_limit": 24}
    student.update(override)
    return student


def codes(result):
    return [e["code"] for e in result["errors"]]


@pytest.mark.normal
def test_add_course_success(state):
    res = add_course(state, make_course())
    assert res["ok"] is True and res["errors"] == []
    assert state.courses["1150001"]["status"] == "active"


@pytest.mark.normal
def test_add_course_normalizes_slots_and_does_not_alias_input(state):
    src = make_course(slots=[{"day": 1, "period": 3}, {"day": 1, "period": "A"}])
    add_course(state, src)
    assert state.courses["1150001"]["slots"] == [{"day": 1, "period": "3"}, {"day": 1, "period": "a"}]
    src["name"] = "被改掉"
    assert state.courses["1150001"]["name"] == "微積分"


@pytest.mark.normal
def test_add_student_success_with_default_limit(state):
    data = make_student()
    del data["credit_limit"]
    res = add_student(state, data)
    assert res["ok"] is True and state.students["115590001"]["credit_limit"] == 24


@pytest.mark.normal
def test_add_room_success_with_default_equipment(state):
    res = add_room(state, {"room_id": "R201", "building": "三教", "capacity": 40})
    assert res["ok"] is True and state.rooms["R201"]["equipment"] == []


@pytest.mark.normal
def test_query_courses_by_teacher_and_sorted(state):
    add_course(state, make_course(course_id="1150002", teacher="張教授", slots=[{"day": 1, "period": "1"}]))
    add_course(state, make_course(course_id="1150001", teacher="張教授", slots=[{"day": 3, "period": "1"}]))
    add_course(state, make_course(course_id="1150003", teacher="李教授", slots=[{"day": 4, "period": "1"}]))
    res = query_courses(state, {"teacher": "張教授"})
    assert [c["course_id"] for c in res["data"]] == ["1150001", "1150002"]


@pytest.mark.normal
def test_query_courses_combined_and_conditions(state):
    add_course(state, make_course())
    add_course(state, make_course(course_id="1150002", category="elective", slots=[{"day": 2, "period": "5"}]))
    res = query_courses(state, {"day": 2, "category": "elective"})
    assert [c["course_id"] for c in res["data"]] == ["1150002"]


@pytest.mark.normal
def test_modify_course_success(state):
    add_course(state, make_course())
    res = modify_course(state, "1150001", {"name": "微積分（二）", "capacity": 40, "credits": 4.0})
    assert res["ok"] is True
    assert state.courses["1150001"]["name"] == "微積分（二）"
    assert state.courses["1150001"]["credits"] == 4 and isinstance(state.courses["1150001"]["credits"], int)


@pytest.mark.normal
def test_cancel_course_removes_enrollments_and_records_students(state):
    add_course(state, make_course())
    state.enrollments.update({("115590002", "1150001"), ("115590001", "1150001")})
    res = cancel_course(state, "1150001")
    assert res["ok"] is True
    assert res["data"]["removed_students"] == ["115590001", "115590002"]
    assert state.courses["1150001"]["status"] == "cancelled" and state.enrollments == set()


@pytest.mark.normal
def test_delete_course_after_cancel_succeeds(state):
    add_course(state, make_course())
    state.enrollments.add(("115590001", "1150001"))
    cancel_course(state, "1150001")
    assert delete_course(state, "1150001")["ok"] is True and "1150001" not in state.courses


@pytest.mark.normal
def test_list_course_students_sorted(state):
    add_course(state, make_course())
    add_student(state, make_student(student_id="115590002", name="乙"))
    add_student(state, make_student())
    state.enrollments.update({("115590002", "1150001"), ("115590001", "1150001")})
    res = list_course_students(state, "1150001")
    assert [r["student_id"] for r in res["data"]] == ["115590001", "115590002"]


@pytest.mark.normal
def test_delete_student_removes_enrollments_and_signups(state):
    add_student(state, make_student())
    state.enrollments.add(("115590001", "1150001"))
    state.activity_signups.add(("115590001", "A001"))
    assert delete_student(state, "115590001")["ok"] is True
    assert state.enrollments == set() and state.activity_signups == set()


@pytest.mark.normal
def test_delete_room_unused_succeeds(state):
    assert delete_room(state, "R102")["ok"] is True and "R102" not in state.rooms


@pytest.mark.normal
def test_sample_data_meets_acceptance_counts(new_state):
    s = build_sample_state(new_state())
    assert len(s.rooms) == 5 and len(s.courses) == 20 and len(s.students) == 15
    assert any(c["status"] == "cancelled" for c in s.courses.values())
    assert any(len(c["slots"]) == 3 for c in s.courses.values())
    assert any(sl["period"] == "c" for c in s.courses.values() for sl in c["slots"])


@pytest.mark.boundary
def test_add_course_capacity_equals_room_capacity(state):
    assert add_course(state, make_course(capacity=60))["ok"] is True


@pytest.mark.boundary
def test_add_course_capacity_one_is_allowed(state):
    assert add_course(state, make_course(capacity=1))["ok"] is True


@pytest.mark.boundary
def test_add_course_float_credits_stored_as_int(state):
    add_course(state, make_course(credits=3.0))
    assert state.courses["1150001"]["credits"] == 3 and isinstance(state.courses["1150001"]["credits"], int)


@pytest.mark.boundary
@pytest.mark.parametrize("period", ["1", "9", "a", "b", "c", "C", 1, 9])
def test_add_course_accepts_boundary_periods(state, period):
    assert add_course(state, make_course(slots=[{"day": 7, "period": period}]))["ok"] is True


@pytest.mark.boundary
def test_add_course_day_one_and_seven_allowed(state):
    res = add_course(state, make_course(slots=[{"day": 1, "period": "1"}, {"day": 7, "period": "c"}]))
    assert res["ok"] is True


@pytest.mark.boundary
def test_modify_course_capacity_equal_to_enrolled_allowed(state):
    add_course(state, make_course())
    state.enrollments.update({("115590001", "1150001"), ("115590002", "1150001")})
    assert modify_course(state, "1150001", {"capacity": 2})["ok"] is True


@pytest.mark.boundary
def test_query_courses_no_match_returns_empty_list(state):
    res = query_courses(state, {"teacher": "沒有這個人"})
    assert res["ok"] is True and res["data"] == []


@pytest.mark.boundary
def test_query_courses_has_seats_excludes_full(state):
    add_course(state, make_course(capacity=1))
    state.enrollments.add(("115590001", "1150001"))
    assert query_courses(state, {"has_seats": True})["data"] == []


@pytest.mark.boundary
def test_query_courses_include_cancelled(state):
    add_course(state, make_course())
    cancel_course(state, "1150001")
    assert query_courses(state, {})["data"] == []
    assert len(query_courses(state, {}, include_cancelled=True)["data"]) == 1


@pytest.mark.boundary
def test_cancel_course_twice_is_success(state):
    add_course(state, make_course())
    cancel_course(state, "1150001")
    res = cancel_course(state, "1150001")
    assert res["ok"] is True and res["data"]["removed_students"] == []


@pytest.mark.boundary
def test_cancelled_course_does_not_block_room(state):
    add_course(state, make_course())
    cancel_course(state, "1150001")
    assert add_course(state, make_course(course_id="1150002"))["ok"] is True


@pytest.mark.boundary
def test_list_course_students_empty_returns_empty_list(state):
    add_course(state, make_course())
    res = list_course_students(state, "1150001")
    assert res["ok"] is True and res["data"] == []


@pytest.mark.boundary
def test_add_student_credit_limit_one_allowed(state):
    assert add_student(state, make_student(credit_limit=1))["ok"] is True


@pytest.mark.error
def test_add_course_duplicate_id(state):
    add_course(state, make_course())
    res = add_course(state, make_course(slots=[{"day": 5, "period": "1"}]))
    assert res["ok"] is False and codes(res) == ["DUPLICATE_ID"]
    assert res["errors"][0]["detail"] == {"field": "course_id", "value": "1150001"}


@pytest.mark.error
@pytest.mark.parametrize("bad_id", ["CS101", "115001", "11500012", 1150001, None, "1150001\n", "１１５０００１"])
def test_add_course_invalid_id_format(state, bad_id):
    res = add_course(state, make_course(course_id=bad_id))
    assert codes(res) == ["INVALID_ID_FORMAT"]


@pytest.mark.error
@pytest.mark.parametrize("credits", [0, -1, 2.5, True, False, "3", None])
def test_add_course_invalid_credits(state, credits):
    res = add_course(state, make_course(credits=credits))
    assert codes(res) == ["INVALID_CREDIT"]


@pytest.mark.error
@pytest.mark.parametrize("capacity", [0, -5, 1.5, True, "10", None])
def test_add_course_invalid_capacity(state, capacity):
    res = add_course(state, make_course(capacity=capacity))
    assert codes(res) == ["INVALID_CAPACITY"]


@pytest.mark.error
def test_add_course_exceeds_room_capacity(state):
    res = add_course(state, make_course(capacity=61))
    assert codes(res) == ["INVALID_CAPACITY"]
    assert res["errors"][0]["detail"] == {"capacity": 61, "room_capacity": 60}


@pytest.mark.error
def test_add_course_room_not_found(state):
    res = add_course(state, make_course(room_id="R999"))
    assert codes(res) == ["NOT_FOUND"] and res["errors"][0]["detail"] == {"room_id": "R999"}


@pytest.mark.error
@pytest.mark.parametrize("slot", [{"day": 8, "period": "1"}, {"day": 0, "period": "1"},
                                  {"day": 1, "period": "d"}, {"day": 1, "period": "0"},
                                  {"day": 1, "period": 10}, {"day": True, "period": "1"},
                                  {"day": 1}, "x", None])
def test_add_course_invalid_slot(state, slot):
    res = add_course(state, make_course(slots=[slot]))
    assert codes(res) == ["INVALID_PERIOD"]


@pytest.mark.error
@pytest.mark.parametrize("slots", [[], None, "abc"])
def test_add_course_empty_or_non_list_slots(state, slots):
    assert codes(add_course(state, make_course(slots=slots))) == ["INVALID_PERIOD"]


@pytest.mark.error
def test_add_course_duplicate_slot_in_same_course(state):
    res = add_course(state, make_course(slots=[{"day": 1, "period": "3"}, {"day": 1, "period": 3}]))
    assert codes(res) == ["INVALID_PERIOD"]


@pytest.mark.error
@pytest.mark.parametrize("field", ["name", "teacher"])
def test_add_course_missing_text_field(state, field):
    data = make_course()
    del data[field]
    res = add_course(state, data)
    assert codes(res) == ["INVALID_FIELD"] and res["errors"][0]["detail"] == {"field": field}


@pytest.mark.error
def test_add_course_invalid_category_and_status(state):
    res = add_course(state, make_course(category="zzz", status="gone"))
    assert codes(res) == ["INVALID_FIELD", "INVALID_FIELD"]


@pytest.mark.error
def test_add_course_collects_all_errors_at_once(state):
    res = add_course(state, make_course(course_id="X", credits=True, capacity=0, room_id="R999",
                                        category="?", slots=[{"day": 8, "period": "d"}]))
    assert sorted(set(codes(res))) == ["INVALID_CAPACITY", "INVALID_CREDIT", "INVALID_FIELD",
                                       "INVALID_ID_FORMAT", "INVALID_PERIOD", "NOT_FOUND"]


@pytest.mark.error
def test_add_course_failure_does_not_change_state(state):
    add_course(state, make_course(credits=0))
    assert state.courses == {}


@pytest.mark.error
def test_add_course_non_dict(state):
    assert codes(add_course(state, None)) == ["INVALID_FIELD"]


@pytest.mark.error
def test_add_course_room_conflict(state):
    add_course(state, make_course())
    res = add_course(state, make_course(course_id="1150002", slots=[{"day": 2, "period": "4"}]))
    assert res["ok"] is False and codes(res) == ["ROOM_CONFLICT"]


@pytest.mark.error
def test_modify_course_not_found(state):
    res = modify_course(state, "1150009", {"name": "x"})
    assert codes(res) == ["NOT_FOUND"] and res["errors"][0]["detail"]["course_id"] == "1150009"


@pytest.mark.error
def test_modify_course_capacity_below_enrolled_lists_students(state):
    add_course(state, make_course(capacity=10))
    state.enrollments.update({("115590001", "1150001"), ("115590002", "1150001")})
    res = modify_course(state, "1150001", {"capacity": 1})
    assert codes(res) == ["CAPACITY_BELOW_ENROLLED"]
    assert res["errors"][0]["detail"] == {"enrolled": 2, "new_capacity": 1,
                                          "students": ["115590001", "115590002"]}
    assert state.courses["1150001"]["capacity"] == 10


@pytest.mark.error
@pytest.mark.parametrize("change,expected", [
    ({"room_id": "R999"}, "NOT_FOUND"), ({"credits": -5}, "INVALID_CREDIT"),
    ({"category": "zzz"}, "INVALID_FIELD"), ({"slots": [{"day": 9, "period": "z"}]}, "INVALID_PERIOD"),
    ({"capacity": 0}, "INVALID_CAPACITY"), ({"capacity": 99}, "INVALID_CAPACITY"),
    ({"course_id": "1150002"}, "INVALID_FIELD"), ({"status": "cancelled"}, "INVALID_FIELD"),
])
def test_modify_course_rejects_invalid_changes(state, change, expected):
    add_course(state, make_course())
    before = dict(state.courses["1150001"])
    res = modify_course(state, "1150001", change)
    assert res["ok"] is False and expected in codes(res)
    assert state.courses["1150001"] == before


@pytest.mark.error
def test_modify_course_cannot_bypass_cancel_enrollment_cleanup(state):
    add_course(state, make_course())
    state.enrollments.add(("115590001", "1150001"))
    modify_course(state, "1150001", {"status": "cancelled"})
    assert state.courses["1150001"]["status"] == "active" and ("115590001", "1150001") in state.enrollments


@pytest.mark.error
def test_modify_course_room_conflict(state):
    add_course(state, make_course())
    add_course(state, make_course(course_id="1150002", slots=[{"day": 5, "period": "1"}]))
    res = modify_course(state, "1150002", {"slots": [{"day": 2, "period": "3"}]})
    assert codes(res) == ["ROOM_CONFLICT"]


@pytest.mark.error
def test_modify_course_student_conflict_lists_students(state):
    add_course(state, make_course())
    add_course(state, make_course(course_id="1150002", room_id="R102", slots=[{"day": 5, "period": "1"}]))
    state.enrollments.update({("115590002", "1150002"), ("115590001", "1150002"),
                              ("115590001", "1150001")})
    res = modify_course(state, "1150002", {"slots": [{"day": 2, "period": "3"}]})
    assert codes(res) == ["STUDENT_CONFLICT"]
    assert res["errors"][0]["detail"] == {"conflict_students": ["115590001"]}


@pytest.mark.error
@pytest.mark.parametrize("filters,expected", [
    ({"day": 8}, "INVALID_PERIOD"), ({"day": True}, "INVALID_PERIOD"),
    ({"category": "x"}, "INVALID_FIELD"), ({"has_seats": "yes"}, "INVALID_FIELD"),
    ({"teacher": 5}, "INVALID_FIELD"),
])
def test_query_courses_invalid_filter(state, filters, expected):
    assert codes(query_courses(state, filters)) == [expected]


@pytest.mark.error
def test_cancel_course_not_found(state):
    res = cancel_course(state, "1150009")
    assert codes(res) == ["NOT_FOUND"]


@pytest.mark.error
def test_delete_course_in_use(state):
    add_course(state, make_course())
    state.enrollments.add(("115590001", "1150001"))
    res = delete_course(state, "1150001")
    assert codes(res) == ["COURSE_IN_USE"] and "1150001" in state.courses


@pytest.mark.error
def test_delete_course_not_found(state):
    assert codes(delete_course(state, "1150009")) == ["NOT_FOUND"]


@pytest.mark.error
def test_list_course_students_not_found(state):
    assert codes(list_course_students(state, "1150009")) == ["NOT_FOUND"]


@pytest.mark.error
def test_add_student_duplicate_id(state):
    add_student(state, make_student())
    assert codes(add_student(state, make_student())) == ["DUPLICATE_ID"]


@pytest.mark.error
def test_add_student_collects_all_errors(state):
    res = add_student(state, make_student(student_id="12", name=" ", department=None, credit_limit=0))
    assert sorted(codes(res)) == ["INVALID_CREDIT", "INVALID_FIELD", "INVALID_FIELD", "INVALID_ID_FORMAT"]


@pytest.mark.error
@pytest.mark.parametrize("limit", [0, -1, 2.5, True, "24"])
def test_add_student_invalid_credit_limit(state, limit):
    assert codes(add_student(state, make_student(credit_limit=limit))) == ["INVALID_CREDIT"]


@pytest.mark.error
def test_delete_student_not_found(state):
    assert codes(delete_student(state, "115590009")) == ["NOT_FOUND"]


@pytest.mark.error
def test_add_room_invalid_and_duplicate(state):
    assert codes(add_room(state, {"room_id": "R101", "building": "x", "capacity": 5})) == ["DUPLICATE_ID"]
    res = add_room(state, {"room_id": "101", "building": " ", "capacity": 0})
    assert sorted(codes(res)) == ["INVALID_CAPACITY", "INVALID_FIELD", "INVALID_ID_FORMAT"]


@pytest.mark.error
@pytest.mark.parametrize("equipment", [["Projector"], ["a", "a"], [3], "projector", [""]])
def test_add_room_invalid_equipment(state, equipment):
    res = add_room(state, {"room_id": "R201", "building": "x", "capacity": 5, "equipment": equipment})
    assert codes(res) == ["INVALID_FIELD"]


@pytest.mark.error
def test_delete_room_in_use_by_course_lists_ids(state):
    add_course(state, make_course())
    res = delete_room(state, "R101")
    assert codes(res) == ["ROOM_IN_USE"] and res["errors"][0]["detail"]["courses"] == ["1150001"]


@pytest.mark.error
def test_delete_room_in_use_by_activity(state):
    state.activities["A001"] = {"activity_id": "A001", "room_id": "R102", "status": "active"}
    assert codes(delete_room(state, "R102")) == ["ROOM_IN_USE"]


@pytest.mark.error
def test_delete_room_not_found(state):
    assert codes(delete_room(state, "R999")) == ["NOT_FOUND"]


@pytest.mark.error
def test_sample_data_planted_room_conflict_is_blocked_by_f1(new_state):
    s = plant_room_conflict(build_sample_state(new_state()))
    clash = dict(s.courses["1150099"], course_id="1150098")
    assert codes(add_course(s, clash)) == ["ROOM_CONFLICT"]
