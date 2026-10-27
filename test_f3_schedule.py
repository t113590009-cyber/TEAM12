from src.f3_schedule import add_schedule_item, remove_schedule_item, get_student_schedule

def test_add_schedule_success():
    """正常新增課表"""
    res = add_schedule_item("S001", "C001", 1, "1")
    assert res["ok"] is True
    assert len(res["errors"]) == 0

def test_add_schedule_conflict():
    """同星期同時段衝突，新增失敗"""
    add_schedule_item("S002", "C002", 2, "2")
    res = add_schedule_item("S002", "C003", 2, "2")
    assert res["ok"] is False
    assert "time slot conflict" in res["errors"]

def test_add_invalid_period():
    """節次不合法"""
    res = add_schedule_item("S003", "C004", 3, "d")
    assert res["ok"] is False
    assert "invalid period" in res["errors"]

def test_remove_item_success():
    """刪除存在的項目"""
    add_schedule_item("S004", "C005", 4, "3")
    res = remove_schedule_item("S004", "C005", 4, "3")
    assert res["ok"] is True

def test_remove_item_not_found():
    """刪不存在的項目"""
    res = remove_schedule_item("S999", "C999", 5, "5")
    assert res["ok"] is False
    assert "schedule item not found" in res["errors"]

def test_get_student_schedule():
    """查詢學生課表"""
    add_schedule_item("S005", "C006", 1, "4")
    res = get_student_schedule("S005")
    assert res["ok"] is True
    assert len(res["data"]) >= 1
