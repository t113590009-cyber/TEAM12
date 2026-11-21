from types import MappingProxyType

from src.common.periods import slots_overlap
from src.common.result import make_error, make_result
from src.common.validators import (DEFAULT_CREDIT_LIMIT, is_int_value,
                                   normalize_slot)
from src.f1_data import get_student_credits
from src.f2_enrollment import check_enrollment

REASON_BY_CODE = MappingProxyType({
    "ALREADY_ENROLLED": "ALREADY_ENROLLED",
    "COURSE_CANCELLED": "CANCELLED",
    "COURSE_FULL": "FULL",
    "STUDENT_CONFLICT": "CONFLICT_ENROLLED",
})

REQUIRED_REASONS = (
    ("CONFLICT_ENROLLED", "REQUIRED_ENROLLED_CONFLICT"),
    ("BLOCKED_SLOT", "REQUIRED_BLOCKED"),
    ("FULL", "REQUIRED_FULL"),
)


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


def _rank_key(row):
    """候選排序:希望課程優先,其次偏好星期,最後依課號。"""
    return (not row["wanted"], not row["preferred_day"], row["course_id"])


def _split_courses(state, student_id, criteria):
    """把全部課程分成候選清單與排除清單。

    Input: state、student_id、criteria
    Process: 逐門課做基本過濾;候選依希望課程、偏好星期、課號排序
    Output: (候選清單, 排除清單),排除清單依課號排序
    Boundary: 沒有課程時兩份都是空清單
    """
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
    candidates.sort(key=_rank_key)
    return candidates, excluded


def _contradiction(reason, **detail):
    """組出一筆 CONSTRAINT_CONTRADICTION 錯誤。"""
    return make_error("CONSTRAINT_CONTRADICTION", "條件互相矛盾",
                      {"reason": reason, **detail})


def _credit_value(criteria, field, default):
    """學分數值轉成整數(輸入驗證已確認為整數值,可能是 20.0)。"""
    return int(criteria.get(field, default))


def _effective_max(state, student_id, criteria):
    """學分上限:max_credits 與學生本身學分上限取較小者。"""
    limit = state.students[student_id].get("credit_limit", DEFAULT_CREDIT_LIMIT)
    return min(_credit_value(criteria, "max_credits", limit), limit)


def _pending_required(state, student_id, criteria):
    """必修中仍需加選的課號(存在、未取消、尚未選),依課號排序。"""
    pending = []
    for course_id in sorted(set(criteria.get("required_courses", []))):
        course = state.courses.get(course_id)
        if course is None or course.get("status", "active") == "cancelled":
            continue
        if (student_id, course_id) not in state.enrollments:
            pending.append(course_id)
    return pending


def _min_gt_max_errors(min_credits, max_credits):
    """學分下限大於上限。"""
    if min_credits > max_credits:
        return [_contradiction("MIN_GT_MAX", min_credits=min_credits,
                               max_credits=max_credits)]
    return []


def _required_conflict_errors(state, pending):
    """兩門必修互相衝堂,每一對只列一筆。"""
    errors = []
    for index, first in enumerate(pending):
        for second in pending[index + 1:]:
            slots_a = state.courses[first]["slots"]
            slots_b = state.courses[second]["slots"]
            if any(slots_overlap(a, b) for a in slots_a for b in slots_b):
                errors.append(_contradiction(
                    "REQUIRED_CONFLICT", course_id=first, with_id=second))
    return errors


def _required_reason_errors(state, student_id, pending, blocked):
    """必修課程本身的問題:與已選課程衝堂、落在不可上課時段、額滿。"""
    reasons = {course_id: _exclusion_reasons(
        state, student_id, course_id, blocked) for course_id in pending}
    errors = []
    for reason, code in REQUIRED_REASONS:
        for course_id in pending:
            if reason in reasons[course_id]:
                errors.append(_contradiction(code, course_id=course_id))
    return errors


def _required_over_max_errors(state, student_id, pending, max_credits):
    """已選學分加必修學分超過上限。"""
    current = get_student_credits(state, student_id)["data"]
    total = current + sum(state.courses[c]["credits"] for c in pending)
    if total > max_credits:
        return [_contradiction("REQUIRED_OVER_MAX", total_credits=total,
                               max_credits=max_credits)]
    return []


def _min_credit_unreachable_errors(state, student_id, candidates, min_credits, max_credits):
    """已選學分加候選課程學分總和低於學分下限（獨立錯誤碼 MIN_CREDIT_UNREACHABLE）。"""
    if min_credits > max_credits:
        return []
    current = get_student_credits(state, student_id)["data"]
    max_reachable = current + sum(c["credits"] for c in candidates)
    if max_reachable < min_credits:
        return [make_error("MIN_CREDIT_UNREACHABLE", "可選學分不足以達到學分下限",
                           {"min_credits": min_credits, "max_reachable": max_reachable})]
    return []


def _contradiction_errors(state, student_id, criteria, candidates):
    """六種條件矛盾與學分不足各自檢查,全部跑完再依固定順序回傳。"""
    max_credits = _effective_max(state, student_id, criteria)
    pending = _pending_required(state, student_id, criteria)
    blocked = criteria.get("blocked_slots", [])
    min_credits = _credit_value(criteria, "min_credits", 0)
    return (_min_gt_max_errors(min_credits, max_credits)
            + _required_conflict_errors(state, pending)
            + _required_reason_errors(state, student_id, pending, blocked)
            + _required_over_max_errors(
                state, student_id, pending, max_credits)
            + _min_credit_unreachable_errors(
                state, student_id, candidates, min_credits, max_credits))


def _student_errors(state, criteria):
    """學號:須為字串,且學生必須存在。"""
    student_id = criteria.get("student_id")
    if not isinstance(student_id, str):
        return [make_error("INVALID_FIELD", "欄位缺漏或不合法",
                           {"field": "student_id"})]
    if student_id not in state.students:
        return [make_error("NOT_FOUND", "找不到資料",
                           {"kind": "student", "student_id": student_id})]
    return []


def _is_credit_value(value):
    """學分數值:非 bool、整數值(接受 20.0)且不小於 0。"""
    return (not isinstance(value, bool) and is_int_value(value)
            and value >= 0)


def _credit_errors(criteria):
    """學分上下限必須是非負整數,規則與共用層一致。"""
    errors = []
    for field in ("min_credits", "max_credits"):
        if field in criteria and not _is_credit_value(criteria[field]):
            errors.append(make_error(
                "INVALID_CREDIT", "學分數值必須為非負整數",
                {"field": field, "value": criteria[field]}))
    return errors


def _list_field_error(field):
    """欄位必須為清單。"""
    return make_error("INVALID_FIELD", "欄位必須為清單", {"field": field})


def _day_errors(criteria):
    """preferred_days:須為清單,星期須是 1~7 的整數。"""
    if "preferred_days" not in criteria:
        return []
    days = criteria["preferred_days"]
    if not isinstance(days, list):
        return [_list_field_error("preferred_days")]
    return [make_error("INVALID_PERIOD", "星期不合法", {"day": day})
            for day in days
            if isinstance(day, bool) or not isinstance(day, int)
            or not 1 <= day <= 7]


def _blocked_slot_errors(criteria):
    """blocked_slots:須為清單,每個時段須合法。"""
    if "blocked_slots" not in criteria:
        return []
    slots = criteria["blocked_slots"]
    if not isinstance(slots, list):
        return [_list_field_error("blocked_slots")]
    return [make_error("INVALID_PERIOD", "星期或節次不合法", {"slot": slot})
            for slot in slots if normalize_slot(slot) is None]


def _course_id_errors(state, field, course_id):
    """單一課號:須為字串(先於查課號,避免 unhashable 當機)、須存在、必修不得已取消。"""
    if not isinstance(course_id, str):
        return [make_error("INVALID_FIELD", "課號必須為字串",
                           {"field": field, "value": course_id})]
    course = state.courses.get(course_id)
    if course is None:
        return [make_error("NOT_FOUND", "找不到資料",
                           {"kind": "course", "course_id": course_id})]
    if field == "required_courses" and course.get("status") == "cancelled":
        return [make_error("COURSE_CANCELLED", "必修課程已取消",
                           {"course_id": course_id})]
    return []


def _course_list_errors(state, criteria):
    """required_courses 與 wanted_courses:須為清單,逐一檢查課號。"""
    errors = []
    for field in ("required_courses", "wanted_courses"):
        if field not in criteria:
            continue
        if not isinstance(criteria[field], list):
            errors.append(_list_field_error(field))
            continue
        for course_id in criteria[field]:
            errors.extend(_course_id_errors(state, field, course_id))
    return errors


def _validate_criteria(state, criteria):
    """輸入驗證:全部檢查跑完一次回報。

    Input: state、criteria
    Process: criteria 須為 dict;依序檢查學號、學分上下限、偏好星期、
             不可上課時段、課號清單
    Output: 錯誤清單,通過回 []
    Boundary: criteria 不是 dict 直接回 INVALID_FIELD;課號不是字串回
              INVALID_FIELD,不會當機
    """
    if not isinstance(criteria, dict):
        return [make_error("INVALID_FIELD", "資料必須為 dict",
                           {"field": "criteria"})]
    return (_student_errors(state, criteria) + _credit_errors(criteria)
            + _day_errors(criteria) + _blocked_slot_errors(criteria)
            + _course_list_errors(state, criteria))


def filter_courses(state, criteria):
    """依個人條件篩選候選課程並檢查條件是否矛盾。

    Input: state、criteria(學號、希望課程、必修、學分上下限、不可上課時段、偏好星期)
    Process: 先做輸入驗證;通過才做基本過濾與條件檢查
    Output: {ok, data={student_id, candidates, excluded, feasible}, errors}
    Boundary: 輸入驗證失敗 data 為 None;有矛盾時 feasible 為 False 但 data 仍保留
    """
    errors = _validate_criteria(state, criteria)
    if errors:
        return make_result(None, errors)

    student_id = criteria["student_id"]
    candidates, excluded = _split_courses(state, student_id, criteria)
    contradictions = _contradiction_errors(state, student_id, criteria, candidates)
    data = {"student_id": student_id, "candidates": candidates,
            "excluded": excluded, "feasible": not contradictions}
    return make_result(data, contradictions)