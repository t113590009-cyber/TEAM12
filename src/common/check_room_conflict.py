from src.common.result import make_error, make_result
from src.common.time_slot import slots_overlap


def check_room_conflict(state, room_id, slots, ignore_id=None):
    """檢查教室在指定時段是否與其他有效課程重疊。

    Input: state、room_id、slots(時段清單)、ignore_id(要排除的代號)
    Process: 比對同教室、非取消、非 ignore_id 的課程時段
    Output: {ok, data, errors},每個衝突一筆 ROOM_CONFLICT
    Boundary: 目前只處理課程;活動與非法輸入下一輪加
    """
    errors = []
    for course in state.courses.values():
        if course["room_id"] != room_id or course["course_id"] == ignore_id:
            continue
        if course.get("status", "active") == "cancelled":
            continue
        for existing in course["slots"]:
            for new in slots:
                if slots_overlap(existing, new):
                    errors.append(make_error(
                        "ROOM_CONFLICT", "教室同時段已有課程或活動",
                        {"day": new["day"], "period": new["period"],
                         "with_kind": "course", "with_id": course["course_id"],
                         "with_name": course["name"]},
                    ))
    return make_result(None, errors)