from src.common.check_room_conflict import check_room_conflict
from src.common.periods import period_index, slots_overlap
from src.common.result import make_error, make_result
from src.common.validators import DEFAULT_CREDIT_LIMIT
from src.f1_data import get_enrolled_students

NO_SLOT_ORDER = ("CREDIT_LIMIT_EXCEEDED", "COURSE_FULL")


def _not_found(kind, key, value):
    return make_error("NOT_FOUND", "找不到資料", {"kind": kind, key: value})


def _precheck_errors(state, student_id, course_id):
    """前置檢查,依序為 NOT_FOUND、COURSE_CANCELLED、ALREADY_ENROLLED。

    Input: state、student_id、course_id
    Process: 依序檢查,第一組失敗就回傳,不再往下
    Output: 錯誤清單,全部通過回 []
    Boundary: 學生與課程都不存在時回兩筆 NOT_FOUND
    """
    errors = []
    if student_id not in state.students:
        errors.append(_not_found("student", "student_id", student_id))
    if course_id not in state.courses:
        errors.append(_not_found("course", "course_id", course_id))
    if errors:
        return errors
    if state.courses[course_id].get("status", "active") == "cancelled":
        return [make_error("COURSE_CANCELLED", "課程已取消",
                           {"course_id": course_id})]
    if (student_id, course_id) in state.enrollments:
        return [make_error("ALREADY_ENROLLED", "已選過此課程",
                           {"student_id": student_id, "course_id": course_id})]
    return []


def _student_courses(state, student_id):
    """暫時版:由 enrollments 推導學生已選的有效課程,F1 提供後替換。"""
    return [state.courses[cid] for sid, cid in sorted(state.enrollments)
            if sid == student_id and cid in state.courses
            and state.courses[cid].get("status", "active") != "cancelled"]


def _current_credits(state, student_id):
    """暫時版:已選有效課程的學分加總(活動不計),F1 提供後替換。"""
    return sum(c["credits"] for c in _student_courses(state, student_id))


def _student_conflict_errors(state, student_id, course_id):
    """學生衝堂:每個衝突時段、每門衝突課程各一筆。"""
    new_course = state.courses[course_id]
    errors = []
    for existing in _student_courses(state, student_id):
        for old_slot in existing["slots"]:
            for new_slot in new_course["slots"]:
                if slots_overlap(old_slot, new_slot):
                    errors.append(make_error(
                        "STUDENT_CONFLICT", "與已選課程衝堂",
                        {"day": new_slot["day"], "period": new_slot["period"],
                         "with_id": existing["course_id"],
                         "with_name": existing["name"]}))
    return errors


def _room_conflict_errors(state, course_id):
    """教室衝堂:呼叫共用層 check_room_conflict,排除課程自己。"""
    course = state.courses[course_id]
    result = check_room_conflict(
        state, course["room_id"], course["slots"], ignore_id=course_id)
    return result["errors"]


def _credit_limit_errors(current, new, limit):
    """學分上限:加選後學分大於上限才算超過(剛好等於上限通過)。"""
    if new > limit:
        return [make_error("CREDIT_LIMIT_EXCEEDED", "加選後學分超過上限",
                           {"current": current, "new": new, "limit": limit})]
    return []


def _course_full_errors(state, course_id):
    """人數上限:目前修課人數已達上限就拒絕(剩 1 名額通過)。"""
    enrolled = len(get_enrolled_students(state, course_id))
    capacity = state.courses[course_id]["capacity"]
    if enrolled >= capacity:
        return [make_error("COURSE_FULL", "課程人數已達上限",
                           {"enrolled": enrolled, "capacity": capacity})]
    return []


def _sort_key(error):
    """有時段的錯誤依 (day, period_index, code) 排前面,沒有時段的排後面。"""
    detail = error["detail"]
    if "day" in detail:
        return (0, detail["day"], period_index(detail["period"]),
                error["code"], detail["with_id"])
    code = error["code"]
    rank = (NO_SLOT_ORDER.index(code) if code in NO_SLOT_ORDER
            else len(NO_SLOT_ORDER))
    return (1, rank, 0, code, "")


def check_enrollment(state, student_id, course_id):
    """檢查學生是否可以加選課程。

    Input: state、student_id、course_id
    Process: 前置檢查,通過後執行學生衝堂、教室衝堂、學分上限、人數上限,
             全部跑完再排序回傳
    Output: {ok, data, errors};data 含課程名稱、目前學分、加選後學分、學分上限
    Boundary: 前置檢查失敗只回傳該錯誤;學分剛好等於上限通過;剩 1 名額通過
    """
    pre_errors = _precheck_errors(state, student_id, course_id)
    if pre_errors:
        return make_result(None, pre_errors)
    course = state.courses[course_id]
    current = _current_credits(state, student_id)
    new = current + course["credits"]
    limit = state.students[student_id].get(
        "credit_limit", DEFAULT_CREDIT_LIMIT)
    errors = (_student_conflict_errors(state, student_id, course_id)
              + _room_conflict_errors(state, course_id)
              + _credit_limit_errors(current, new, limit)
              + _course_full_errors(state, course_id))
    errors.sort(key=_sort_key)
    data = {"student_id": student_id, "course_id": course_id,
            "course_name": course["name"], "current_credits": current,
            "new_credits": new, "credit_limit": limit}
    return make_result(data, errors)