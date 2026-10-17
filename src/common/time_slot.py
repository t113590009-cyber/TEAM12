"""時段與節次共用函式 - F1~F5、F7 共用"""

PERIOD_TABLE = {
    "1":  (1,  "08:10", "09:00"),
    "2":  (2,  "09:10", "10:00"),
    "3":  (3,  "10:10", "11:00"),
    "4":  (4,  "11:10", "12:00"),
    "5":  (5,  "13:10", "14:00"),
    "6":  (6,  "14:10", "15:00"),
    "7":  (7,  "15:10", "16:00"),
    "8":  (8,  "16:10", "17:00"),
    "9":  (9,  "17:10", "18:00"),
    "a":  (10, "18:30", "19:20"),
    "b":  (11, "19:20", "20:10"),
    "c":  (12, "20:20", "21:10"),
}


def period_index(period):
    """節次字串 → 索引 1~12；非法回傳 None"""
    if period in PERIOD_TABLE:
        return PERIOD_TABLE[period][0]
    return None


def period_time_range(period):
    """節次字串 → (start, end) 字串，例：("10:10","11:00")；非法回傳 None"""
    if period in PERIOD_TABLE:
        _, start, end = PERIOD_TABLE[period]
        return (start, end)
    return None


def is_valid_slot(slot):
    """檢查 slot = {"day":1~7, "period":"1"~"c"} 是否合法"""
    if not isinstance(slot, dict):
        return False
    day = slot.get("day")
    period = slot.get("period")
    if not isinstance(day, int) or isinstance(day, bool):
        return False
    if not (1 <= day <= 7):
        return False
    if period_index(period) is None:
        return False
    return True


def slots_overlap(slot_a, slot_b):
    """兩個 slot 是否同時段（同 day 同 period）"""
    return (slot_a.get("day") == slot_b.get("day")
            and slot_a.get("period") == slot_b.get("period"))
