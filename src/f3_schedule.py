from src.common.periods import is_valid_slot, slots_overlap

# 用來存所有學生課表，正式版本會改成讀寫JSON
_schedule_data = []


def add_schedule_item(student_id, course_id, weekday, period):
    """新增課表項目，檢查時段衝突"""
    if not student_id:
        return {"ok": False, "data": None, "errors": ["student_id is empty"]}

    if not is_valid_slot(period):
        return {"ok": False, "data": None, "errors": ["invalid period"]}

    # 檢查這個學生已經有的課，有沒有衝突
    student_items = [x for x in _schedule_data if x["student_id"] == student_id]
    new_item = {
        "student_id": student_id,
        "course_id": course_id,
        "weekday": weekday,
        "period": period
    }

    for item in student_items:
        if item["weekday"] == weekday and slots_overlap(item["period"], period):
            return {"ok": False, "data": None, "errors": ["time slot conflict"]}

    _schedule_data.append(new_item)
    return {"ok": True, "data": new_item, "errors": []}


def remove_schedule_item(student_id, course_id, weekday, period):
    """刪除指定課表項目"""
    target = None
    for item in _schedule_data:
        if (item["student_id"] == student_id
                and item["course_id"] == course_id
                and item["weekday"] == weekday
                and item["period"] == period):
            target = item
            break
    if target is None:
        return {"ok": False, "data": None, "errors": ["schedule item not found"]}

    _schedule_data.remove(target)
    return {"ok": True, "data": target, "errors": []}


def get_student_schedule(student_id):
    """取得單一學生全部課表"""
    result = [x for x in _schedule_data if x["student_id"] == student_id]
    return {"ok": True, "data": result, "errors": []}
