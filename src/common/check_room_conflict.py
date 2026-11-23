from src.common.activity_time import activity_periods
from src.common.periods import is_valid_slot, period_index, slots_overlap
from src.common.result import make_error, make_result


def _sort_key(error):
    detail = error["detail"]
    return (detail["day"], period_index(detail["period"]), detail["with_id"])


def _split_slots(slots):
    """把時段分成合法時段與 INVALID_PERIOD 錯誤。"""
    valid, invalid = [], []
    for slot in slots:
        if is_valid_slot(slot):
            valid.append(slot)
        else:
            invalid.append(
                make_error("INVALID_PERIOD", "時段不合法", {"slot": slot})
            )
    return valid, invalid


def _is_active(item):
    return item.get("status", "active") != "cancelled"


def _occupants(state, room_id, ignore_id, include_activities):
    """同教室、有效、非 ignore_id 的課程與活動，回傳 (kind, 代號, 名稱, 占用時段) 清單。"""
    found = []
    for course in state.courses.values():
        if (course["room_id"] == room_id and course["course_id"] != ignore_id
                and _is_active(course)):
            found.append(("course", course["course_id"], course["name"], course["slots"]))
    if not include_activities:
        return found
    for activity in state.activities.values():
        if (activity.get("room_id") == room_id and activity["activity_id"] != ignore_id
                and _is_active(activity)):
            slots = [{"day": day, "period": period}
                     for day, period in activity_periods(activity)]
            found.append(("activity", activity["activity_id"], activity["name"], slots))
    return found


def check_room_conflict(state, room_id, slots, ignore_id=None, include_activities=True):
    """檢查教室在指定時段是否與其他有效課程或活動重疊。

    Input: state、room_id、slots(時段清單)、ignore_id(要排除的代號)、
           include_activities(是否比對活動，預設 True)
    Process: 先驗證時段;比對同教室、非取消、非 ignore_id 的課程時段，
             以及活動換算後的節次(activity_periods)
    Output: {ok, data, errors};ROOM_CONFLICT 依 (day, period_index, with_id) 排序,
            INVALID_PERIOD 排在最後
    Boundary: 空清單回 ok;非法時段回報但不影響其他時段檢查;
              不佔任何節次的短時段活動不會衝突;
              F4 比活動對活動要看日期，呼叫時傳 include_activities=False 自行比對
    """
    valid_slots, invalid_errors = _split_slots(slots)
    conflicts = []
    for kind, with_id, with_name, taken in _occupants(
            state, room_id, ignore_id, include_activities):
        for existing in taken:
            for new in valid_slots:
                if slots_overlap(existing, new):
                    conflicts.append(make_error(
                        "ROOM_CONFLICT", "教室同時段已有課程或活動",
                        {"day": new["day"], "period": new["period"],
                         "with_kind": kind, "with_id": with_id,
                         "with_name": with_name},
                    ))
    conflicts.sort(key=_sort_key)
    return make_result(None, conflicts + invalid_errors)
