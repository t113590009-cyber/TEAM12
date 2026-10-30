from types import MappingProxyType

# 節次字串 -> 索引（資料格式書 2.1），唯讀
PERIOD_TABLE = MappingProxyType({
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "a": 10, "b": 11, "c": 12,
})
_DIGITS = "0123456789"


def period_index(period):
    """節次 -> 索引 1～12。

    Input: period，整數 1～9 或字串 "1"～"9"、"a"～"c"（大小寫皆可）。
    Process: 整數轉字串、字串轉小寫後查 PERIOD_TABLE。
    Output: 索引 1～12。
    Boundary: 非法值（0、10、"d"、None、bool、float 等）回傳 None。
    """
    if type(period) is int:  # 用 type 比對以排除 bool
        key = str(period)
    elif type(period) is str:
        key = period.lower()
    else:
        return None
    return PERIOD_TABLE.get(key)


def is_valid_slot(slot):
    """檢查時段是否合法。

    Input: slot，形如 {"day": 2, "period": "3"}。
    Process: 檢查型態、day 是否為 1～7 的整數、period 是否合法。
    Output: True / False。
    Boundary: 非 dict、缺鍵、day 為 bool 或字串皆回傳 False。
    """
    if type(slot) is not dict:
        return False
    day = slot.get("day")
    if type(day) is not int:  # 排除 bool
        return False
    if not 1 <= day <= 7:
        return False
    return period_index(slot.get("period")) is not None


def slots_overlap(slot_a, slot_b):
    """兩時段是否同星期同節次。

    Input: slot_a、slot_b，皆為 slot。
    Process: 兩者都合法時，比對 day 與節次索引。
    Output: True / False。
    Boundary: 任一方非法回傳 False（待與組員確認是否要自行擋非法輸入）。
    """
    if not (is_valid_slot(slot_a) and is_valid_slot(slot_b)):
        return False
    return (slot_a["day"] == slot_b["day"]
            and period_index(slot_a["period"]) == period_index(slot_b["period"]))


def _time_to_minutes(time_str):
    """HH:MM 轉為當日分鐘數；格式或數值不合法回傳 None。"""
    if type(time_str) is not str or len(time_str) != 5 or time_str[2] != ":":
        return None
    if not all(char in _DIGITS for char in time_str[:2] + time_str[3:]):
        return None
    hour, minute = int(time_str[:2]), int(time_str[3:])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour * 60 + minute


def time_ranges_overlap(start_a, end_a, start_b, end_b):
    """兩個 HH:MM 區間是否重疊。

    Input: start_a、end_a、start_b、end_b，皆為 "HH:MM"。
    Process: 轉成分鐘後判斷 start_a < end_b 且 start_b < end_a。
    Output: True / False。
    Boundary: 頭尾相接不算重疊；格式不合或起訖不是 start < end 回傳 False。
    """
    times = [_time_to_minutes(v) for v in (start_a, end_a, start_b, end_b)]
    if None in times:
        return False
    start_a, end_a, start_b, end_b = times
    if start_a >= end_a or start_b >= end_b:
        return False
    return start_a < end_b and start_b < end_a