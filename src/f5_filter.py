from types import MappingProxyType

from src.common.periods import slots_overlap
from src.common.result import make_error, make_result
from src.f2_enrollment import check_enrollment

REASON_BY_CODE = MappingProxyType({
    "ALREADY_ENROLLED": "ALREADY_ENROLLED",
    "COURSE_CANCELLED": "CANCELLED",
    "COURSE_FULL": "FULL",
    "STUDENT_CONFLICT": "CONFLICT_ENROLLED",
})


def _exclusion_reasons(state, student_id, course_id, blocked_slots):
    """一門課被排除的全部原因(依字母排序)。

    Input: state、student_id、course_id、blocked_slots(不可上課時段)
    Process: 呼叫 F2 check_enrollment 並轉成排除原因,另外檢查不可上課時段
    Output: 排序後的原因清單,沒有原因回 []
    Boundary: 學分、教室衝堂、活動衝突不當作排除原因
    """
    reasons = set()
    for error in check_enrollment(state, student_id, course_id)["errors"]:
        reason = REASON_BY_CODE.get(error["code"])
        if reason:
            reasons.add(reason)
    slots = state.courses[course_id]["slots"]
    if any(slots_overlap(s, b) for s in slots for b in blocked_slots):
        reasons.add("BLOCKED_SLOT")
    return sorted(reasons)


def _candidate_row(course, wanted, preferred_days):
    """候選課程的一列輸出。"""
    days = {slot["day"] for slot in course["slots"]}
    return {"course_id": course["course_id"], "name": course["name"],
            "credits": course["credits"], "wanted": wanted,
            "preferred_day": bool(preferred_days) and days <= preferred_days}


def _split_courses(state, student_id, criteria):
    """把全部課程分成候選清單與排除清單,各依課號排序。"""
    wanted = set(criteria.get("wanted_courses", []))
    blocked = criteria.get("blocked_slots", [])
    preferred = set(criteria.get("preferred_days", []))
    candidates, excluded = [], []
    for course_id in sorted(state.courses):
        reasons = _exclusion_reasons(state, student_id, course_id, blocked)
        if reasons:
            excluded.append({"course_id": course_id, "reasons": reasons})
        else:
            candidates.append(_candidate_row(
                state.courses[course_id], course_id in wanted, preferred))
    return candidates, excluded


def filter_courses(state, criteria):
    """依個人條件篩選候選課程。

    Input: state、criteria(學號、希望課程、必修、學分上下限、不可上課時段、偏好星期)
    Process: 學生存在才繼續;逐門課做基本過濾,分成候選與排除
    Output: {ok, data={student_id, candidates, excluded, feasible}, errors}
    Boundary: 學生不存在回 NOT_FOUND;矛盾與學分檢查之後逐項加入
    """
    student_id = criteria["student_id"]
    if student_id not in state.students:
        return make_result(None, [make_error(
            "NOT_FOUND", "找不到資料",
            {"kind": "student", "student_id": student_id})])
    candidates, excluded = _split_courses(state, student_id, criteria)
    data = {"student_id": student_id, "candidates": candidates,
            "excluded": excluded, "feasible": True}
    return make_result(data, [])