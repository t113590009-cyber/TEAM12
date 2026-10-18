"""F1 課程與學生資料管理（負責：組員 B）。

只依賴共用層（result、validators、check_room_conflict、time_slot.slots_overlap）。
所有函式直接修改傳入的 state 並回傳 {ok, data, errors}；業務錯誤不拋例外。
"""
import copy

from src.common.result import make_error, make_ok, make_result
from src.common.check_room_conflict import check_room_conflict
from src.common.periods import slots_overlap
from src.common.validators import (VALID_CATEGORIES, validate_course, validate_room,
                                   validate_student)


def _not_found(kind, key, value):
    return make_result(None, [make_error("NOT_FOUND", "找不到資料", {"kind": kind, key: value})])


def get_enrolled_students(state, course_id):
    """Input: state、課號。Process: 由 enrollments 推導修課學號。
    Output: 排序後的學號清單。Boundary: 無人修或課號不存在回 []。"""
    return sorted(sid for sid, cid in state.enrollments if cid == course_id)


# AI修改：新增與修改共用同一個教室衝堂檢查，已取消課程不檢查
def _room_conflict(state, course):
    """有效課程才檢查教室衝堂；回傳 check_room_conflict 的結果。"""
    if course["status"] != "active":
        return make_ok()
    return check_room_conflict(state, course["room_id"], course["slots"], ignore_id=course["course_id"])


def add_course(state, course_data):
    """Input: state、課程 dict。
    Process: 完整欄位驗證（跑完全部）→ 教室衝堂（共用層）→ 存入標準化複本。
    Output: {ok, data=課程, errors}。
    Boundary: 重複／非法代號、學分 0／2.5／True、人數 <1 或 > 教室容量、不存在的教室、
    星期 8／節次 d、同教室同時段（ROOM_CONFLICT）。"""
    result = validate_course(state, course_data, is_new=True)
    if not result["ok"]:
        return result
    course = result["data"]
    conflict = _room_conflict(state, course)
    if not conflict["ok"]:
        return conflict
    state.courses[course["course_id"]] = course
    return make_ok(course)


def _modify_guard_errors(course, course_id, new_data):
    """代號不可改；狀態只能經 cancel_course 改變。"""
    errors = []
    if new_data.get("course_id", course_id) != course_id:
        errors.append(make_error("INVALID_FIELD", "課程代號不可修改", {"field": "course_id"}))
    if new_data.get("status", course["status"]) != course["status"]:
        errors.append(make_error("INVALID_FIELD", "狀態請用 cancel_course 變更",
                                 {"field": "status", "reason": "USE_CANCEL_COURSE"}))
    return errors


def _capacity_errors(state, course_id, capacity):
    """人數上限低於現有人數：拒絕並列出學號。"""
    students = get_enrolled_students(state, course_id)
    if len(students) <= capacity:
        return []
    return [make_error("CAPACITY_BELOW_ENROLLED", "修改後人數上限低於現有人數",
                       {"enrolled": len(students), "new_capacity": capacity, "students": students})]


# AI實作：回傳衝堂學號清單（排序），需求規格要求拒絕時列出學號
def _students_in_conflict(state, course_id, slots):
    """已選此課的學生中，其他有效課程與新時段重疊者（排序後學號）。"""
    bad = []
    for sid in get_enrolled_students(state, course_id):
        others = [cid for s, cid in state.enrollments if s == sid and cid != course_id]
        for cid in others:
            other = state.courses.get(cid)
            if other and other["status"] == "active" and any(
                    slots_overlap(a, b) for a in slots for b in other["slots"]):
                bad.append(sid)
                break
    return sorted(bad)


def modify_course(state, course_id, new_data):
    """Input: state、課號、要修改的欄位 dict。
    Process: 與原資料合併後做完整驗證 → 人數上限不低於現有人數 → 教室衝堂 →
    時段變更時檢查已選學生衝堂 → 全部通過才更新。
    Output: {ok, data=更新後課程, errors}。
    Boundary: 不存在的課程、改代號、改 status、非法欄位、人數上限 < 現有人數（列學號）、
    ROOM_CONFLICT、STUDENT_CONFLICT（列學號）。"""
    course = state.courses.get(course_id)
    if course is None:
        return _not_found("course", "course_id", course_id)
    if not isinstance(new_data, dict):
        return make_result(None, [make_error("INVALID_FIELD", "資料必須為 dict", {"field": "new_data"})])
    # AI修改：改成與原資料合併後走完整驗證，不再只檢查 capacity 與 slots
    errors = _modify_guard_errors(course, course_id, new_data)
    merged = {**course, **new_data, "course_id": course_id}
    result = validate_course(state, merged, is_new=False)
    errors += result["errors"]
    if "capacity" in new_data and result["ok"]:
        errors += _capacity_errors(state, course_id, result["data"]["capacity"])
    if errors:
        return make_result(None, errors)
    updated = result["data"]
    conflict = _room_conflict(state, updated)
    if not conflict["ok"]:
        return conflict
    bad = _students_in_conflict(state, course_id, updated["slots"]) if "slots" in new_data else []
    if bad:
        return make_result(None, [make_error("STUDENT_CONFLICT", "修改時段造成已選學生衝堂",
                                             {"conflict_students": bad})])
    course.update(updated)
    return make_ok(course)


# AI實作：查詢條件值驗證（day、category、has_seats）
def _query_filter_errors(filters):
    """驗證查詢條件值；不合法回 INVALID_FIELD 或 INVALID_PERIOD。"""
    errors = []
    day = filters.get("day")
    if "day" in filters and (isinstance(day, bool) or not isinstance(day, int) or not 1 <= day <= 7):
        errors.append(make_error("INVALID_PERIOD", "星期不合法", {"day": day}))
    if "category" in filters and filters["category"] not in VALID_CATEGORIES:
        errors.append(make_error("INVALID_FIELD", "必選修類別錯誤", {"field": "category"}))
    for key in ("course_id", "teacher"):
        if key in filters and not isinstance(filters[key], str):
            errors.append(make_error("INVALID_FIELD", "條件值不合法", {"field": key}))
    if "has_seats" in filters and not isinstance(filters["has_seats"], bool):
        errors.append(make_error("INVALID_FIELD", "條件值不合法", {"field": "has_seats"}))
    return errors


def _matches(state, course, filters):
    """單一課程是否符合全部條件（AND）。"""
    if "course_id" in filters and course["course_id"] != filters["course_id"]:
        return False
    if "teacher" in filters and course["teacher"] != filters["teacher"]:
        return False
    if "day" in filters and not any(s["day"] == filters["day"] for s in course["slots"]):
        return False
    if "category" in filters and course["category"] != filters["category"]:
        return False
    if filters.get("has_seats"):
        return course["capacity"] - len(get_enrolled_students(state, course["course_id"])) > 0
    return True


def query_courses(state, filters, include_cancelled=False):
    """Input: state、filters（course_id/teacher/day/category/has_seats 任意組合）、include_cancelled。
    Process: 驗證條件值 → AND 過濾 → 預設排除已取消 → 依課號排序。
    Output: {ok, data=課程清單（複本）, errors}。
    Boundary: 查無結果回 ok=True、data=[]；day=8、category 非法回錯誤。"""
    if not isinstance(filters, dict):
        return make_result(None, [make_error("INVALID_FIELD", "條件必須為 dict", {"field": "filters"})])
    errors = _query_filter_errors(filters)
    if errors:
        return make_result(None, errors)
    found = [c for c in state.courses.values()
             if (include_cancelled or c["status"] != "cancelled") and _matches(state, c, filters)]
    found.sort(key=lambda c: c["course_id"])
    return make_ok(copy.deepcopy(found))


def cancel_course(state, course_id):
    """Input: state、課號。Process: 退選所有學生並記錄學號，狀態改 cancelled。
    Output: {ok, data={course_id, status, removed_students}, errors}。
    Boundary: 課程不存在回 NOT_FOUND；重複取消視為成功（removed_students 為 [] ）。"""
    course = state.courses.get(course_id)
    if course is None:
        return _not_found("course", "course_id", course_id)
    students = get_enrolled_students(state, course_id)
    # AI修改：取消時記錄被退選學號並回傳，原本只改狀態
    state.enrollments.difference_update({(sid, course_id) for sid in students})
    course["status"] = "cancelled"
    return make_ok({"course_id": course_id, "status": "cancelled", "removed_students": students})


def delete_course(state, course_id):
    """Input: state、課號。Process: 無人選修才刪除。
    Output: {ok, data={deleted_id}, errors}。
    Boundary: 不存在回 NOT_FOUND；有人選修回 COURSE_IN_USE（取消後即可刪除）。"""
    if course_id not in state.courses:
        return _not_found("course", "course_id", course_id)
    students = get_enrolled_students(state, course_id)
    if students:
        return make_result(None, [make_error("COURSE_IN_USE", "課程仍有人選，不可刪除",
                                             {"course_id": course_id, "enrolled": len(students)})])
    del state.courses[course_id]
    return make_ok({"deleted_id": course_id})


def list_course_students(state, course_id):
    """Input: state、課號。Process: 由選課紀錄推導修課學生。
    Output: {ok, data=[{student_id, name, department}]（依學號排序）, errors}。
    Boundary: 課程不存在回 NOT_FOUND；無人修回 ok=True、data=[]。"""
    if course_id not in state.courses:
        return _not_found("course", "course_id", course_id)
    rows = []
    for sid in get_enrolled_students(state, course_id):
        student = state.students.get(sid)
        if student:
            rows.append({"student_id": sid, "name": student["name"], "department": student["department"]})
    return make_ok(rows)


def add_student(state, student_data):
    """Input: state、學生 dict。Process: 完整驗證後存入標準化複本（學分上限預設 24）。
    Output: {ok, data=學生, errors}。
    Boundary: 重複／非法學號、姓名或系級空白、學分上限 0／2.5／True。"""
    result = validate_student(state, student_data, is_new=True)
    if not result["ok"]:
        return result
    state.students[result["data"]["student_id"]] = result["data"]
    return make_ok(result["data"])


def delete_student(state, student_id):
    """Input: state、學號。Process: 刪除學生並一併移除其選課與活動報名。
    Output: {ok, data={deleted_id}, errors}。Boundary: 學生不存在回 NOT_FOUND。"""
    if student_id not in state.students:
        return _not_found("student", "student_id", student_id)
    # AI修改：用 difference_update 原地移除，不重新指派 state.enrollments
    state.enrollments.difference_update({e for e in state.enrollments if e[0] == student_id})
    state.activity_signups.difference_update({a for a in state.activity_signups if a[0] == student_id})
    del state.students[student_id]
    return make_ok({"deleted_id": student_id})


def add_room(state, room_data):
    """Input: state、教室 dict。Process: 完整驗證後存入標準化複本（設備預設 []）。
    Output: {ok, data=教室, errors}。
    Boundary: 重複／非法代號、容量 <1、棟別空白、設備大寫或重複。"""
    result = validate_room(state, room_data, is_new=True)
    if not result["ok"]:
        return result
    state.rooms[result["data"]["room_id"]] = result["data"]
    return make_ok(result["data"])


def delete_room(state, room_id):
    """Input: state、教室代號。
    Process: 任何課程（含已取消，避免載入時 REFERENCE_MISSING）或活動仍引用就拒絕。
    Output: {ok, data={deleted_id}, errors}。
    Boundary: 不存在回 NOT_FOUND；使用中回 ROOM_IN_USE（detail 列出課號與活動代號）。"""
    if room_id not in state.rooms:
        return _not_found("room", "room_id", room_id)
    # AI修改：已取消課程也算引用，避免存檔載入時出現找不到教室的資料
    courses = sorted(c["course_id"] for c in state.courses.values() if c["room_id"] == room_id)
    activities = sorted(a["activity_id"] for a in state.activities.values() if a.get("room_id") == room_id)
    if courses or activities:
        return make_result(None, [make_error("ROOM_IN_USE", "教室仍被課程或活動使用，不可刪除",
                                             {"room_id": room_id, "courses": courses,
                                              "activities": activities})])
    del state.rooms[room_id]
    return make_ok({"deleted_id": room_id})
