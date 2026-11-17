"""F4 校園活動與教室配置（負責：組員 D；協作 B、C）。

只依賴共用層（result、validators、periods、activity_time、check_room_conflict）與
F1 的 get_student_courses。所有函式直接修改傳入的 state 並回傳 {ok, data, errors}；
業務錯誤不拋例外。

衝突規則（資料格式書 2.4）：
- 活動 ↔ 課程：活動以 activity_periods 換算成 (day, period) 後比節次。
- 活動 ↔ 活動：同日期且時間區間重疊（time_ranges_overlap），不經節次換算。
- 已取消的課程與活動不構成衝突。
"""
import copy

from src.common.activity_time import activity_periods, is_valid_date
from src.common.check_room_conflict import check_room_conflict
from src.common.periods import period_index, slots_overlap, time_ranges_overlap
from src.common.result import make_error, make_ok, make_result
from src.common.validators import validate_activity
from src.f1_data import get_student_courses

QUERY_FIELDS = ("activity_id", "date", "activity_type", "room_id")


def _not_found(kind, key, value):
    return make_error("NOT_FOUND", "找不到資料", {"kind": kind, key: value})


def _is_active(item):
    return item.get("status", "active") == "active"


def _activity_slots(activity):
    """活動占用的節次，轉成 slot 清單；不佔任何節次的短時段回 []。"""
    return [{"day": day, "period": period} for day, period in activity_periods(activity)]


def _same_time(activity_a, activity_b):
    """活動對活動：同日期且時間區間重疊（頭尾相接不算）。"""
    return (activity_a["date"] == activity_b["date"]
            and time_ranges_overlap(activity_a["start_time"], activity_a["end_time"],
                                    activity_b["start_time"], activity_b["end_time"]))


def _activity_detail(other):
    """與其他活動衝突時的 detail：活動不一定佔節次，所以用日期與時間表示。"""
    return {"date": other["date"], "start_time": other["start_time"],
            "end_time": other["end_time"], "with_kind": "activity",
            "with_id": other["activity_id"], "with_name": other["name"]}


def get_activity_signups(state, activity_id):
    """Input: state、活動代號。Process: 由 activity_signups 推導報名學號。
    Output: 排序後的學號清單。Boundary: 無人報名或活動不存在回 []。"""
    return sorted(sid for sid, aid in state.activity_signups if aid == activity_id)


def activity_capacity(state, activity):
    """Input: state、活動 dict。
    Process: 報名容量 = min(預計人數, 教室容量)。
    Output: int。Boundary: 尚未配置教室（room_id 為 None）時為預計人數。"""
    room = state.rooms.get(activity.get("room_id"))
    if room is None:
        return activity["expected_size"]
    return min(activity["expected_size"], room["capacity"])


def _room_conflict_errors(state, activity):
    """教室衝突：課程用共用層 check_room_conflict 比節次，其他活動比同日期時間區間。"""
    room_id = activity.get("room_id")
    if room_id is None or not _is_active(activity):
        return []
    errors = check_room_conflict(state, room_id, _activity_slots(activity))["errors"]
    for other in sorted(state.activities.values(), key=lambda a: a["activity_id"]):
        if (other["activity_id"] != activity["activity_id"] and other.get("room_id") == room_id
                and _is_active(other) and _same_time(activity, other)):
            errors.append(make_error("ROOM_CONFLICT", "教室同時段已有課程或活動",
                                     _activity_detail(other)))
    return errors


def add_activity(state, activity_data):
    """Input: state、活動 dict。
    Process: 完整欄位驗證（共用層 validate_activity）→ 已配置教室時檢查教室衝突 → 存入標準化複本。
    Output: {ok, data=活動（複本）, errors}。
    Boundary: 重複／非法代號、日期不存在、時間超出 08:10～21:10 或起訖顛倒、預計人數 < 1、
    不存在的教室、教室同時段已有有效課程（比節次）或有效活動（比時間區間）。"""
    result = validate_activity(state, activity_data, is_new=True)
    if not result["ok"]:
        return result
    activity = result["data"]
    errors = _room_conflict_errors(state, activity)
    if errors:
        return make_result(None, errors)
    state.activities[activity["activity_id"]] = activity
    return make_ok(copy.deepcopy(activity))


def _modify_guard_errors(activity, activity_id, new_data):
    """代號不可改；狀態只能經 cancel_activity 改變。"""
    errors = []
    if new_data.get("activity_id", activity_id) != activity_id:
        errors.append(make_error("INVALID_FIELD", "活動代號不可修改", {"field": "activity_id"}))
    if new_data.get("status", activity["status"]) != activity["status"]:
        errors.append(make_error("INVALID_FIELD", "狀態請用 cancel_activity 變更",
                                 {"field": "status", "reason": "USE_CANCEL_ACTIVITY"}))
    return errors


def _below_signup_errors(state, activity):
    """修改後報名容量（預計人數或教室容量）低於現有報名人數：拒絕並列出學號。"""
    students = get_activity_signups(state, activity["activity_id"])
    capacity = activity_capacity(state, activity)
    if len(students) <= capacity:
        return []
    return [make_error("CAPACITY_BELOW_ENROLLED", "修改後活動容量低於現有報名人數",
                       {"enrolled": len(students), "new_capacity": capacity, "students": students})]


def _students_in_conflict(state, activity):
    """已報名此活動的學生中，與新時間的課程或其他活動衝突者（排序後學號）。"""
    if not _is_active(activity):
        return []
    return [sid for sid in get_activity_signups(state, activity["activity_id"])
            if _signup_conflict_errors(state, sid, activity)]


def modify_activity(state, activity_id, new_data):
    """Input: state、活動代號、要修改的欄位 dict。
    Process: 與原資料合併後重新完整驗證 → 容量不低於現有報名人數 → 教室衝突 →
    已報名學生衝突，全部通過才更新。
    Output: {ok, data=更新後活動（複本）, errors}。
    Boundary: 活動不存在、改代號、改 status、非法欄位、預計人數低於報名人數（列學號）、
    ROOM_CONFLICT、時間變更造成已報名學生衝突（STUDENT_CONFLICT，列學號）；失敗時 state 不變。"""
    activity = state.activities.get(activity_id)
    if activity is None:
        return make_result(None, [_not_found("activity", "activity_id", activity_id)])
    if not isinstance(new_data, dict):
        return make_result(None, [make_error("INVALID_FIELD", "資料必須為 dict", {"field": "new_data"})])
    errors = _modify_guard_errors(activity, activity_id, new_data)
    merged = {**activity, **new_data, "activity_id": activity_id}
    result = validate_activity(state, merged, is_new=False)
    errors += result["errors"]
    if result["ok"]:
        errors += _below_signup_errors(state, result["data"])
    if errors:
        return make_result(None, errors)
    updated = result["data"]
    errors = _room_conflict_errors(state, updated)
    bad = _students_in_conflict(state, updated)
    if bad:
        errors.append(make_error("STUDENT_CONFLICT", "修改時間造成已報名學生衝突",
                                 {"conflict_students": bad}))
    if errors:
        return make_result(None, errors)
    activity.update(updated)
    return make_ok(copy.deepcopy(activity))


def cancel_activity(state, activity_id):
    """Input: state、活動代號。
    Process: 保留活動資料、狀態改 cancelled，並移除所有報名紀錄以釋放時段。
    Output: {ok, data={activity_id, status, removed_students}, errors}。
    Boundary: 活動不存在回 NOT_FOUND；重複取消視為成功（removed_students 為 []）。"""
    activity = state.activities.get(activity_id)
    if activity is None:
        return make_result(None, [_not_found("activity", "activity_id", activity_id)])
    students = get_activity_signups(state, activity_id)
    state.activity_signups.difference_update({(sid, activity_id) for sid in students})
    activity["status"] = "cancelled"
    return make_ok({"activity_id": activity_id, "status": "cancelled", "removed_students": students})


def _query_filter_errors(filters):
    """查詢條件只接受 QUERY_FIELDS；值須為字串（room_id 可為 None 表示未配置）。"""
    errors = []
    for key, value in filters.items():
        if key not in QUERY_FIELDS:
            errors.append(make_error("INVALID_FIELD", "不支援的查詢條件", {"field": key}))
        elif key == "date" and not is_valid_date(value):
            errors.append(make_error("INVALID_DATE", "日期不合法", {"field": "date", "value": value}))
        elif not isinstance(value, str) and not (key == "room_id" and value is None):
            errors.append(make_error("INVALID_FIELD", "條件值不合法", {"field": key}))
    return errors


def query_activities(state, filters=None, include_cancelled=False):
    """Input: state、filters（activity_id／date／activity_type／room_id 任意組合）、include_cancelled。
    Process: 驗證條件 → AND 過濾 → 預設排除已取消 → 依 (日期, 開始時間, 代號) 排序。
    Output: {ok, data=活動清單（複本）, errors}。
    Boundary: filters 為 None 列出全部；查無結果回 ok=True、data=[]；未知條件或日期不合法回錯誤。"""
    filters = {} if filters is None else filters
    if not isinstance(filters, dict):
        return make_result(None, [make_error("INVALID_FIELD", "條件必須為 dict", {"field": "filters"})])
    errors = _query_filter_errors(filters)
    if errors:
        return make_result(None, errors)
    found = [a for a in state.activities.values()
             if (include_cancelled or _is_active(a))
             and all(a.get(key) == value for key, value in filters.items())]
    found.sort(key=lambda a: (a["date"], a["start_time"], a["activity_id"]))
    return make_ok(copy.deepcopy(found))


def _room_check(state, room, activity):
    """單間教室對活動的條件檢查，回傳 detail（unmet 為空代表合適）。"""
    unmet = []
    if room["capacity"] < max(activity["min_capacity"], activity["expected_size"]):
        unmet.append("capacity")
    missing = sorted(set(activity["required_equipment"]) - set(room["equipment"]))
    if missing:
        unmet.append("equipment")
    candidate = {**activity, "room_id": room["room_id"], "status": "active"}
    kinds = {e["detail"]["with_kind"] for e in _room_conflict_errors(state, candidate)}
    unmet += [f"{kind}_conflict" for kind in ("course", "activity") if kind in kinds]
    return {"room_id": room["room_id"], "capacity": room["capacity"],
            "unmet": unmet, "missing_equipment": missing}


def find_suitable_rooms(state, activity_id):
    """Input: state、活動代號。
    Process: 逐間檢查：容量 >= max(最低容量, 預計人數)、設備齊全、該時段無有效課程（比節次）、
    無其他有效活動（比時間區間）；合適者依 (容量, 代號) 由小到大排序。
    Output: {ok, data=[{room_id, building, capacity}], errors}。
    Boundary: 活動不存在回 NOT_FOUND；沒有合適教室回 NO_SUITABLE_ROOM，
    detail.rooms 逐間列出 unmet（capacity／equipment／course_conflict／activity_conflict）。"""
    activity = state.activities.get(activity_id)
    if activity is None:
        return make_result(None, [_not_found("activity", "activity_id", activity_id)])
    rooms = sorted(state.rooms.values(), key=lambda r: (r["capacity"], r["room_id"]))
    checks = [(room, _room_check(state, room, activity)) for room in rooms]
    suitable = [{"room_id": room["room_id"], "building": room["building"],
                 "capacity": room["capacity"]} for room, check in checks if not check["unmet"]]
    if suitable:
        return make_ok(suitable)
    rejected = sorted((check for _, check in checks), key=lambda c: c["room_id"])
    return make_result([], [make_error("NO_SUITABLE_ROOM", "沒有合適教室",
                                       {"activity_id": activity_id, "rooms": rejected})])


def assign_room(state, activity_id):
    """Input: state、活動代號。
    Process: 由 find_suitable_rooms 取容量最小的合適教室，寫入活動的 room_id。
    Output: {ok, data=更新後活動（複本）, errors}。
    Boundary: 活動不存在回 NOT_FOUND；已取消回 COURSE_CANCELLED（kind=activity）；
    無合適教室回 NO_SUITABLE_ROOM 且 state 不變；容量需要考量現有報名人數。"""
    activity = state.activities.get(activity_id)
    if activity is not None and not _is_active(activity):
        return make_result(None, [_cancelled_error(activity_id)])
    result = find_suitable_rooms(state, activity_id)
    if not result["ok"]:
        return result
    return modify_activity(state, activity_id, {"room_id": result["data"][0]["room_id"]})


def _cancelled_error(activity_id):
    """錯誤碼表沒有 ACTIVITY_CANCELLED，沿用 COURSE_CANCELLED 並以 kind 區分。"""
    return make_error("COURSE_CANCELLED", "活動已取消", {"kind": "activity", "activity_id": activity_id})


def _signup_precheck(state, student_id, activity_id):
    """前置檢查：NOT_FOUND（學生、活動皆檢查）→ 活動已取消 → 已報名。"""
    errors = []
    if student_id not in state.students:
        errors.append(_not_found("student", "student_id", student_id))
    if activity_id not in state.activities:
        errors.append(_not_found("activity", "activity_id", activity_id))
    if errors:
        return errors
    if not _is_active(state.activities[activity_id]):
        return [_cancelled_error(activity_id)]
    if (student_id, activity_id) in state.activity_signups:
        return [make_error("ALREADY_ENROLLED", "已報名此活動",
                           {"student_id": student_id, "activity_id": activity_id})]
    return []


def _course_conflict_errors(state, student_id, activity):
    """活動對學生已選課程：比節次，每個衝突節次、每門課各一筆。"""
    errors = []
    for course_id in get_student_courses(state, student_id)["data"] or []:
        course = state.courses[course_id]
        for slot in _activity_slots(activity):
            if any(slots_overlap(slot, existing) for existing in course["slots"]):
                errors.append(make_error("ACTIVITY_CONFLICT", "與已選課程衝突",
                                         {"day": slot["day"], "period": slot["period"],
                                          "with_kind": "course", "with_id": course_id,
                                          "with_name": course["name"]}))
    return errors


def _other_activity_errors(state, student_id, activity):
    """活動對學生已報名的其他有效活動：同日期比時間區間。"""
    errors = []
    for sid, aid in sorted(state.activity_signups):
        other = state.activities.get(aid)
        if (sid == student_id and aid != activity["activity_id"] and other is not None
                and _is_active(other) and _same_time(activity, other)):
            errors.append(make_error("ACTIVITY_CONFLICT", "與已報名活動衝突", _activity_detail(other)))
    return errors


def _conflict_sort_key(error):
    """課程衝突依 (day, period_index) 排前面，活動衝突依 (日期, 開始時間) 排後面。"""
    detail = error["detail"]
    if detail["with_kind"] == "course":
        return (0, detail["day"], period_index(detail["period"]), "", detail["with_id"])
    return (1, 0, 0, detail["date"] + detail["start_time"], detail["with_id"])


def _signup_conflict_errors(state, student_id, activity):
    """學生報名此活動會產生的全部衝突（課程 + 其他活動），已排序。"""
    errors = (_course_conflict_errors(state, student_id, activity)
              + _other_activity_errors(state, student_id, activity))
    return sorted(errors, key=_conflict_sort_key)


def check_signup(state, student_id, activity_id):
    """Input: state、學號、活動代號。
    Process: 前置檢查通過後，跑完課程衝突、活動衝突、報名額滿三項再回傳（只檢查，不修改 state）。
    Output: {ok, data={student_id, activity_id, activity_name, enrolled, capacity}, errors}。
    Boundary: 前置檢查失敗只回該錯誤；容量 = min(預計人數, 教室容量)；剩 1 名額通過；
    不佔節次的短時段不與課程衝突。"""
    pre_errors = _signup_precheck(state, student_id, activity_id)
    if pre_errors:
        return make_result(None, pre_errors)
    activity = state.activities[activity_id]
    enrolled = len(get_activity_signups(state, activity_id))
    capacity = activity_capacity(state, activity)
    errors = _signup_conflict_errors(state, student_id, activity)
    if enrolled >= capacity:
        errors.append(make_error("ACTIVITY_FULL", "活動報名已額滿",
                                 {"enrolled": enrolled, "capacity": capacity}))
    data = {"student_id": student_id, "activity_id": activity_id,
            "activity_name": activity["name"], "enrolled": enrolled, "capacity": capacity}
    return make_result(data, errors)


def signup_activity(state, student_id, activity_id):
    """Input: state、學號、活動代號。
    Process: check_signup 全部通過才加入 activity_signups。
    Output: 與 check_signup 相同；成功時 data.enrolled 為報名後人數。
    Boundary: 失敗時 state 完全不變。"""
    result = check_signup(state, student_id, activity_id)
    if result["ok"]:
        state.activity_signups.add((student_id, activity_id))
        result["data"]["enrolled"] += 1
    return result


def cancel_signup(state, student_id, activity_id):
    """Input: state、學號、活動代號。
    Process: 確認學生與活動存在且有報名紀錄才移除。
    Output: {ok, data={student_id, activity_id, enrolled}, errors}；enrolled 為取消後人數。
    Boundary: 學生與活動都不存在回兩筆 NOT_FOUND；沒報名回 NOT_ENROLLED；失敗時 state 不變。"""
    errors = []
    if student_id not in state.students:
        errors.append(_not_found("student", "student_id", student_id))
    if activity_id not in state.activities:
        errors.append(_not_found("activity", "activity_id", activity_id))
    if errors:
        return make_result(None, errors)
    if (student_id, activity_id) not in state.activity_signups:
        return make_result(None, [make_error("NOT_ENROLLED", "沒有報名紀錄",
                                             {"student_id": student_id, "activity_id": activity_id})])
    state.activity_signups.discard((student_id, activity_id))
    return make_ok({"student_id": student_id, "activity_id": activity_id,
                    "enrolled": len(get_activity_signups(state, activity_id))})
