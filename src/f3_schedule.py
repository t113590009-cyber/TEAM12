"""F3 個人課表產生與連續空堂查詢。"""

from src.common.activity_time import activity_periods
from src.common.periods import period_index
from src.common.result import make_error, make_result
from src.f1_data import get_student_courses


def _not_found(student_id):
    return make_error("NOT_FOUND", "找不到學生", {
        "kind": "student", "student_id": student_id
    })


def _put(grid, day, period, item, errors):
    """將一個時段放入矩陣；重複占用時保留原項目並記錄錯誤。"""
    index = period_index(period)
    if type(day) is not int or not 1 <= day <= 7 or index is None:
        errors.append(make_error("INVALID_PERIOD", "課表時段不合法", {
            "day": day, "period": period, "id": item["id"]
        }))
        return
    cell = grid[day - 1][index - 1]
    if cell is not None:
        errors.append(make_error("SCHEDULE_CONFLICT", "學生課表時段重複", {
            "day": day, "period": str(period), "with_id": cell["id"],
            "id": item["id"]
        }))
        return
    grid[day - 1][index - 1] = item


def build_schedule(state, student_id):
    """建立學生一週 7 天、每天 12 節的課表。

    課程只取已選且有效的課；活動只取已報名且未取消的活動。
    回傳 {ok, data={grid, stats}, errors}。
    """
    if student_id not in state.students:
        return make_result(None, [_not_found(student_id)])

    grid = [[None for _ in range(12)] for _ in range(7)]
    errors = []
    course_ids = get_student_courses(state, student_id)["data"]

    for course_id in course_ids:
        course = state.courses[course_id]
        for slot in course.get("slots", []):
            _put(grid, slot.get("day"), slot.get("period"),
                 {"type": "course", "id": course_id}, errors)

    activity_count = 0
    for sid, activity_id in sorted(state.activity_signups):
        if sid != student_id:
            continue
        activity = state.activities.get(activity_id)
        if activity is None or activity.get("status", "active") == "cancelled":
            continue
        periods = activity_periods(activity)
        if not periods:
            errors.append(make_error("INVALID_ACTIVITY_TIME", "活動日期或時間不合法", {
                "activity_id": activity_id
            }))
            continue
        activity_count += 1
        for day, period in periods:
            _put(grid, day, period,
                 {"type": "activity", "id": activity_id}, errors)

    stats = {
        "course_count": len(course_ids),
        "activity_count": activity_count,
        "free_slots": sum(cell is None for row in grid for cell in row),
    }
    return make_result({"grid": grid, "stats": stats}, errors)


def _scope_days(scope):
    """解析搜尋日範圍；scope 可省略或用 day / start_day、end_day。"""
    if scope is None:
        return 1, 7
    if not isinstance(scope, dict):
        return None
    start = scope.get("day", scope.get("start_day", 1))
    end = scope.get("day", scope.get("end_day", 7))
    if (type(start) is not int or type(end) is not int
            or not 1 <= start <= end <= 7):
        return None
    return start, end


def _scope_periods(scope):
    """解析每日搜尋節次範圍；預設搜尋全天 12 節。"""
    start = scope.get("start_period", "1") if isinstance(scope, dict) else "1"
    end = scope.get("end_period", "c") if isinstance(scope, dict) else "c"
    first, last = period_index(start), period_index(end)
    if first is None or last is None or first > last:
        return None
    return first, last


def find_free_blocks(state, student_id, scope=None, min_len=1):
    """找出指定日／節次範圍內至少 min_len 節的連續空堂。

    scope 可為 None、{"day": 2}、{"start_day": 1, "end_day": 5}，
    並可加上 start_period / end_period 限定每日搜尋範圍。
    data 為區段清單，每筆含 day、start_period、end_period、length。
    """
    if student_id not in state.students:
        return make_result(None, [_not_found(student_id)])
    if type(min_len) is not int or min_len < 1:
        return make_result(None, [make_error("INVALID_FIELD", "min_len 必須是正整數", {
            "field": "min_len", "value": min_len
        })])
    days = _scope_days(scope)
    periods = _scope_periods(scope)
    if days is None:
        return make_result(None, [make_error("INVALID_PERIOD", "搜尋星期範圍不合法", {
            "field": "scope"
        })])
    if periods is None:
        return make_result(None, [make_error("INVALID_PERIOD", "搜尋節次範圍不合法", {
            "field": "scope"
        })])

    schedule = build_schedule(state, student_id)
    if not schedule["ok"]:
        return schedule
    grid = schedule["data"]["grid"]
    start_day, end_day = days
    first_period, last_period = periods
    blocks = []
    for day in range(start_day, end_day + 1):
        run_start = None
        for period_number in range(first_period, last_period + 2):
            is_free = (period_number <= last_period
                       and grid[day - 1][period_number - 1] is None)
            if is_free and run_start is None:
                run_start = period_number
            elif not is_free and run_start is not None:
                length = period_number - run_start
                if length >= min_len:
                    blocks.append({
                        "day": day,
                        "start_period": str(run_start) if run_start <= 9 else "abc"[run_start - 10],
                        "end_period": str(period_number - 1) if period_number - 1 <= 9 else "abc"[period_number - 11],
                        "length": length,
                    })
                run_start = None
    return make_result(blocks, [])
