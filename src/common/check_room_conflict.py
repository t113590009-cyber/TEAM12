from src.common.periods import period_index
from src.common.result import make_error, make_result
from src.common.time_slot import is_valid_slot, slots_overlap

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


def check_room_conflict(state, room_id, slots, ignore_id=None):
    """檢查教室在指定時段是否與其他有效課程重疊。

    Input: state、room_id、slots(時段清單)、ignore_id(要排除的代號)
    Process: 先驗證時段;比對同教室、非取消、非 ignore_id 的課程時段
    Output: {ok, data, errors};ROOM_CONFLICT 依 (day, period_index) 排序,
            INVALID_PERIOD 排在最後
    Boundary: 空清單回 ok;非法時段回報但不影響其他時段檢查;
              目前只處理課程,活動衝突下一輪加
    """
    valid_slots, invalid_errors = _split_slots(slots)
    conflicts = []
    for course in state.courses.values():
        if course["room_id"] != room_id or course["course_id"] == ignore_id:
            continue
        if course.get("status", "active") == "cancelled":
            continue
        for existing in course["slots"]:
            for new in valid_slots:
                if slots_overlap(existing, new):
                    conflicts.append(make_error(
                        "ROOM_CONFLICT", "教室同時段已有課程或活動",
                        {"day": new["day"], "period": new["period"],
                         "with_kind": "course", "with_id": course["course_id"],
                         "with_name": course["name"]},
                    ))
    conflicts.sort(key=_sort_key)
    return make_result(None, conflicts + invalid_errors)