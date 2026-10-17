"""共用層：欄位驗證函式（資料格式書第 3～5 章）。

F1 新增／修改與 F6 載入共用；只驗證、不修改 state，回傳 {ok, data, errors}，
成功時 data 為正規化後的新 dict（不是傳入物件）。一律跑完全部欄位再回傳。
"""
import re

from src.common.result import make_error, make_result

DEFAULT_CREDIT_LIMIT = 24
VALID_CATEGORIES = ("required", "elective")
VALID_STATUSES = ("active", "cancelled")
PERIOD_CHARS = "123456789abc"
COURSE_ID_RE = re.compile(r"[0-9]{7}")
STUDENT_ID_RE = re.compile(r"[0-9]{9}")
ROOM_ID_RE = re.compile(r"R[0-9]{3}")


def is_valid_id(value, pattern):
    """Input: 值、編譯後的正規表達式。Process: 必須是 str 且完整符合（不吃結尾換行、僅 ASCII 數字）。
    Output: bool。Boundary: int、None、'1150001\\n'、全形數字皆為 False。"""
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def is_int_value(value):
    """Input: 任意值。Process: 接受 int 與整數值 float（3.0），排除 bool。
    Output: bool。Boundary: True、2.5、'3'、None 為 False。"""
    if isinstance(value, bool):
        return False
    return isinstance(value, int) or (isinstance(value, float) and value.is_integer())


# AI實作：節次正規化（整數與大寫轉成標準字串）
def normalize_period(period):
    """Input: 節次（整數 1～9、字串 '1'～'9'、a/b/c 含大寫）。Process: 轉成標準字串。
    Output: 標準節次字串，非法回 None。Boundary: 'd'、'0'、10、True、'10' 皆為 None。"""
    if isinstance(period, bool):
        return None
    text = str(period) if isinstance(period, (int, str)) else None
    if text is None or len(text) != 1:
        return None
    text = text.lower()
    return text if text in PERIOD_CHARS else None


def normalize_slot(slot):
    """Input: 時段 dict。Process: 檢查 day 為 1～7 整數、period 合法，回傳標準化新 dict。
    Output: {"day", "period"} 或 None。Boundary: 非 dict、day 為 bool/8/0 皆為 None。"""
    if not isinstance(slot, dict):
        return None
    day = slot.get("day")
    period = normalize_period(slot.get("period"))
    if isinstance(day, bool) or not isinstance(day, int) or not 1 <= day <= 7 or period is None:
        return None
    return {"day": day, "period": period}


def _check_text(data, field, errors):
    """必填非空白字串；不合法加入 INVALID_FIELD。回傳去除前後空白的值或 None。"""
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(make_error("INVALID_FIELD", "欄位缺漏或不合法", {"field": field}))
        return None
    return value.strip()


def _check_positive_int(value, code, field, errors):
    """正整數檢查（學分、學分上限、人數）。回傳 int 或 None。"""
    if not is_int_value(value) or int(value) < 1:
        errors.append(make_error(code, "數值必須為正整數", {"field": field, "value": value}))
        return None
    return int(value)


def _check_id(data, field, pattern, existing, is_new, errors):
    """代號格式與（新增時）重複檢查。回傳代號或 None。"""
    value = data.get(field)
    if not is_valid_id(value, pattern):
        errors.append(make_error("INVALID_ID_FORMAT", "代號格式不符", {"field": field, "value": value}))
        return None
    if is_new and value in existing:
        errors.append(make_error("DUPLICATE_ID", "代號已存在", {"field": field, "value": value}))
        return None
    return value


def _check_status(data, errors):
    """status 預設 active，只能是 active 或 cancelled。"""
    status = data.get("status", "active")
    if status not in VALID_STATUSES:
        errors.append(make_error("INVALID_FIELD", "狀態不合法", {"field": "status", "value": status}))
        return None
    return status


def _check_slots(slots, errors):
    """至少 1 筆、每筆合法、同課程不得重複；每個問題各回報一筆。回傳標準化清單。"""
    if not isinstance(slots, list) or not slots:
        errors.append(make_error("INVALID_PERIOD", "上課時段不可為空", {"field": "slots"}))
        return None
    cleaned, seen = [], set()
    for slot in slots:
        norm = normalize_slot(slot)
        if norm is None:
            errors.append(make_error("INVALID_PERIOD", "星期或節次不合法", {"slot": slot}))
        elif (norm["day"], norm["period"]) in seen:
            errors.append(make_error("INVALID_PERIOD", "同一課程內時段重複", {"slot": norm}))
        else:
            seen.add((norm["day"], norm["period"]))
            cleaned.append(norm)
    return cleaned


def _check_course_room(state, data, capacity, errors):
    """教室須存在（NOT_FOUND）；人數上限不得大於教室容量（INVALID_CAPACITY）。"""
    room_id = data.get("room_id")
    if not isinstance(room_id, str):
        errors.append(make_error("INVALID_FIELD", "欄位缺漏或不合法", {"field": "room_id"}))
        return None
    room = state.rooms.get(room_id)
    if room is None:
        errors.append(make_error("NOT_FOUND", "指定的教室不存在", {"room_id": room_id}))
        return None
    if capacity is not None and capacity > room["capacity"]:
        errors.append(make_error("INVALID_CAPACITY", "課程人數上限大於教室容量",
                                 {"capacity": capacity, "room_capacity": room["capacity"]}))
    return room_id


# AI修改：驗證從 add_course 拆到共用層，F6 載入可共用
def validate_course(state, data, is_new=True):
    """Input: state、課程 dict、is_new（新增才檢查重複代號）。
    Process: 跑完全部欄位驗證，不修改 state。
    Output: {ok, data=標準化新 dict, errors}；失敗時 data 為 None。
    Boundary: 非 dict、缺欄位、學分 0／2.5／True／'3'、人數 <1、人數 > 教室容量、
    不存在的教室、節次 d、星期 8、時段重複、代號非字串。"""
    if not isinstance(data, dict):
        return make_result(None, [make_error("INVALID_FIELD", "資料必須為 dict", {"field": "course"})])
    errors = []
    course_id = _check_id(data, "course_id", COURSE_ID_RE, state.courses, is_new, errors)
    name = _check_text(data, "name", errors)
    teacher = _check_text(data, "teacher", errors)
    credits = _check_positive_int(data.get("credits"), "INVALID_CREDIT", "credits", errors)
    capacity = _check_positive_int(data.get("capacity"), "INVALID_CAPACITY", "capacity", errors)
    room_id = _check_course_room(state, data, capacity, errors)
    category = data.get("category")
    if category not in VALID_CATEGORIES:
        errors.append(make_error("INVALID_FIELD", "必選修類別錯誤", {"field": "category", "value": category}))
    slots = _check_slots(data.get("slots"), errors)
    status = _check_status(data, errors)
    if errors:
        return make_result(None, errors)
    cleaned = {"course_id": course_id, "name": name, "credits": credits, "category": category,
               "teacher": teacher, "capacity": capacity, "room_id": room_id,
               "slots": slots, "status": status}
    return make_result(cleaned, [])


def validate_student(state, data, is_new=True):
    """Input: state、學生 dict、is_new。Process: 驗證學號、姓名、系級、學分上限（預設 24）。
    Output: {ok, data=標準化新 dict, errors}；失敗 data 為 None。
    Boundary: 學號非 9 位數字或非字串、姓名／系級空白、學分上限 0／2.5／True。"""
    if not isinstance(data, dict):
        return make_result(None, [make_error("INVALID_FIELD", "資料必須為 dict", {"field": "student"})])
    errors = []
    student_id = _check_id(data, "student_id", STUDENT_ID_RE, state.students, is_new, errors)
    name = _check_text(data, "name", errors)
    department = _check_text(data, "department", errors)
    limit = _check_positive_int(data.get("credit_limit", DEFAULT_CREDIT_LIMIT),
                                "INVALID_CREDIT", "credit_limit", errors)
    if errors:
        return make_result(None, errors)
    return make_result({"student_id": student_id, "name": name,
                        "department": department, "credit_limit": limit}, [])


# AI實作：設備清單檢查（小寫、不重複）
def _check_equipment(equipment, errors):
    """設備清單：元素為非空小寫字串且不重複。"""
    ok = isinstance(equipment, list) and all(
        isinstance(item, str) and item and item == item.lower() and item.strip() == item
        for item in equipment) and len(set(equipment)) == len(equipment)
    if not ok:
        errors.append(make_error("INVALID_FIELD", "設備清單不合法", {"field": "equipment"}))
        return None
    return list(equipment)


def validate_room(state, data, is_new=True):
    """Input: state、教室 dict、is_new。Process: 驗證代號 Rxxx、棟別、容量、設備（預設 []）。
    Output: {ok, data=標準化新 dict, errors}；失敗 data 為 None。
    Boundary: 代號非 R+3 位數字、容量 0、棟別空白、設備大寫／重複／非字串。"""
    if not isinstance(data, dict):
        return make_result(None, [make_error("INVALID_FIELD", "資料必須為 dict", {"field": "room"})])
    errors = []
    room_id = _check_id(data, "room_id", ROOM_ID_RE, state.rooms, is_new, errors)
    building = _check_text(data, "building", errors)
    capacity = _check_positive_int(data.get("capacity"), "INVALID_CAPACITY", "capacity", errors)
    equipment = _check_equipment(data.get("equipment", []), errors)
    if errors:
        return make_result(None, errors)
    return make_result({"room_id": room_id, "building": building,
                        "capacity": capacity, "equipment": equipment}, [])
