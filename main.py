"""main.py：唯一入口，只負責選單、輸入與顯示，不放核心邏輯。

目前接上 F1～F4。F5（篩選）、F6（存檔與載入）合併進 main 後再補。
"""
from src.common.state import State
from src.f1_data import (
    add_course, modify_course, delete_course, cancel_course, query_courses,
    list_course_students, add_student, delete_student, add_room, delete_room,
)
from src.f2_enrollment import check_enrollment, enroll, drop
from src.f4_activity import (
    add_activity, modify_activity, cancel_activity, query_activities,
    assign_room, check_signup, signup_activity, cancel_signup,
)
# F3 統一檔名（D 負責）後，這一行改成 from src.f3_schedule import ...
from src.schedule import build_schedule, find_free_blocks

DAY_NAMES = ("一", "二", "三", "四", "五", "六", "日")
STAT_LABELS = (
    ("course_count", "課程數"),
    ("activity_count", "活動數"),
    ("free_slots", "全週未占用節數"),
    ("daily_periods", "每日節數"),
    ("weekly_credits", "每週學分"),
    ("free_periods", "空堂數"),
)
PERIOD_LABELS = "123456789abc"
CELL_WIDTH = 10

# 欄位清單：(欄位名稱, 提示文字, 型態)。型態：text、value、list、slots
COURSE_FIELDS = (
    ("course_id", "課號", "text"),
    ("name", "課名", "text"),
    ("credits", "學分", "value"),
    ("category", "必選修（required / elective）", "text"),
    ("teacher", "授課教師", "text"),
    ("capacity", "人數上限", "value"),
    ("room_id", "教室代號", "text"),
    ("slots", "上課時段（星期-節次，例：2-3,2-4,4-2）", "slots"),
)
STUDENT_FIELDS = (
    ("student_id", "學號", "text"),
    ("name", "姓名", "text"),
    ("department", "系級", "text"),
    ("credit_limit", "學分上限（可略過）", "value"),
)
ROOM_FIELDS = (
    ("room_id", "教室代號", "text"),
    ("building", "棟別", "text"),
    ("capacity", "容量", "value"),
    ("equipment", "設備（逗號分隔，可略過）", "list"),
)
ACTIVITY_FIELDS = (
    ("activity_id", "活動代號", "text"),
    ("name", "活動名稱", "text"),
    ("date", "日期（YYYY-MM-DD）", "text"),
    ("start_time", "開始時間（HH:MM）", "text"),
    ("end_time", "結束時間（HH:MM）", "text"),
    ("expected_size", "預計人數", "value"),
    ("activity_type", "活動類型（如 study、talk）", "text"),
    ("min_capacity", "最低容量（可略過）", "value"),
    ("required_equipment", "需要設備（逗號分隔，可略過）", "list"),
    ("room_id", "指定教室（可略過）", "text"),
)


# ---------- 輸入工具 ----------

def ask(prompt):
    """讀一行文字並去掉前後空白。"""
    return input(prompt).strip()


def parse_value(text):
    """能轉整數就轉整數，其次浮點數，否則保留字串，合不合法交給核心函式驗證。"""
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def parse_list(text):
    """逗號分隔字串轉清單，略過空白項。"""
    return [item.strip() for item in text.split(",") if item.strip()]


def parse_slots(text):
    """'2-3,2-4' 轉成 [{'day': 2, 'period': '3'}, ...]。"""
    slots = []
    for part in parse_list(text):
        day_text, _, period = part.partition("-")
        slots.append({"day": parse_value(day_text.strip()),
                      "period": period.strip()})
    return slots


def ask_fields(fields):
    """依欄位清單逐項詢問，空白視為略過，回傳字典。"""
    data = {}
    for key, label, kind in fields:
        text = ask(f"{label}：")
        if text == "":
            continue
        if kind == "value":
            data[key] = parse_value(text)
        elif kind == "list":
            data[key] = parse_list(text)
        elif kind == "slots":
            data[key] = parse_slots(text)
        else:
            data[key] = text
    return data


# ---------- 顯示工具 ----------

def print_errors(errors):
    """逐筆印出錯誤清單。"""
    for index, error in enumerate(errors, 1):
        print(f"  錯誤 {index}：{error['code']} - {error['message']}")
        if error["detail"]:
            print(f"      細節：{error['detail']}")


def show_result(result, ok_message, show_data=False):
    """依 ok 印出成功或失敗；show_data 為 True 時一併列出 data 內容。"""
    if result["ok"]:
        print(f"【成功】{ok_message}")
    else:
        print("【失敗】")
        print_errors(result["errors"])
    if show_data and isinstance(result["data"], dict):
        for key, value in result["data"].items():
            print(f"  {key}：{value}")


CONFLICT_LABELS = {
    "STUDENT_CONFLICT": "已選課程",
    "ACTIVITY_CONFLICT": "已參加活動",
    "ROOM_CONFLICT": "教室被占用",
}


def print_enrollment_result(result):
    """依資料格式書 8.1 的格式印出加選檢查結果。"""
    data = result["data"]
    if not isinstance(data, dict) or "current_credits" not in data:
        show_result(result, "完成")
        return
    print(f"學生：{data['student_id']}")
    print(f"欲加選：{data['course_id']} {data['course_name']}")
    print(f"選課結果：{'成功' if result['ok'] else '失敗'}")
    for index, error in enumerate(result["errors"], 1):
        detail = error["detail"]
        if "day" in detail:
            print(f"衝突 {index}：星期{DAY_NAMES[detail['day'] - 1]}"
                  f"第 {detail['period']} 節")
            label = CONFLICT_LABELS.get(error["code"], error["message"])
            print(f" {label}：{detail.get('with_id')} {detail.get('with_name')}")
        else:
            print(f"衝突 {index}：{error['message']}")
            print(f" 細節：{detail}")
    print(f"目前學分：{data['current_credits']}")
    print(f"加選後學分：{data['new_credits']}")
    print(f"學分上限：{data['credit_limit']}")


def do_enrollment(state, function):
    """詢問學號與課號，呼叫檢查或加選函式，用規格格式顯示。"""
    student_id = ask("學號：")
    course_id = ask("課號：")
    print_enrollment_result(function(state, student_id, course_id))

CONFLICT_LABELS = {
    "STUDENT_CONFLICT": "已選課程",
    "ACTIVITY_CONFLICT": "已參加活動",
    "ROOM_CONFLICT": "教室被占用",
}


def print_enrollment_result(result):
    """依資料格式書 8.1 的格式印出加選檢查結果。"""
    data = result["data"]
    if not isinstance(data, dict) or "current_credits" not in data:
        show_result(result, "完成")
        return
    print(f"學生：{data['student_id']}")
    print(f"欲加選：{data['course_id']} {data['course_name']}")
    print(f"選課結果：{'成功' if result['ok'] else '失敗'}")
    for index, error in enumerate(result["errors"], 1):
        detail = error["detail"]
        if "day" in detail:
            print(f"衝堂 {index}：星期{DAY_NAMES[detail['day'] - 1]}"
                  f"第 {detail['period']} 節")
            label = CONFLICT_LABELS.get(error["code"], error["message"])
            print(f" {label}：{detail.get('with_id')} {detail.get('with_name')}")
        else:
            print(f"衝突 {index}：{error['message']}")
            print(f" 細節：{detail}")
    print(f"目前學分：{data['current_credits']}")
    print(f"加選後學分：{data['new_credits']}")
    print(f"學分上限：{data['credit_limit']}")


def do_enrollment(state, function):
    """詢問學號與課號，呼叫檢查或加選函式，用規格格式顯示。"""
    student_id = ask("學號：")
    course_id = ask("課號：")
    print_enrollment_result(function(state, student_id, course_id))

def format_slots(slots):
    """時段清單轉成『週二第3節、週二第4節』。"""
    return "、".join(f"週{DAY_NAMES[slot['day'] - 1]}第{slot['period']}節"
                     for slot in slots)


def print_courses(courses):
    """列出課程清單。"""
    if not courses:
        print("查無資料")
    for course in courses:
        print(f"{course['course_id']} {course['name']} {course['credits']}學分 "
              f"{course['category']} {course['teacher']} {course['room_id']} "
              f"{format_slots(course['slots'])} [{course.get('status', 'active')}]")


def cell_text(item):
    """格子裡的一個項目轉成文字；相容多種格式，活動前面加 *。"""
    if isinstance(item, dict):
        kind = item.get("kind") or item.get("type")
        prefix = "*" if kind == "activity" else ""
        return prefix + str(item.get("id", ""))
    return str(item)


def print_schedule(data):
    """印出 7 × 12 課表與統計，活動以 * 標示。"""
    header = "節次" + " " * (CELL_WIDTH - 4)
    header += "".join(f"週{name}" + " " * (CELL_WIDTH - 4) for name in DAY_NAMES)
    print(header)
    for index, label in enumerate(PERIOD_LABELS):
        row = label.ljust(CELL_WIDTH)
        for day_index in range(7):
            items = data["grid"][day_index][index] or []
            if isinstance(items, dict):
                items = [items]
            text = ",".join(cell_text(item) for item in items)
            row += (text or "-").ljust(CELL_WIDTH)
        print(row)
    labels = dict(STAT_LABELS)
    for key, value in data.get("stats", {}).items():
        print(f"{labels.get(key, key)}：{value}")


# ---------- 通用處理（建立、修改、依代號操作） ----------

def do_create(state, function, fields, label):
    """詢問欄位後呼叫新增函式。"""
    result = function(state, ask_fields(fields))
    show_result(result, f"{label}成功")


def do_modify(state, function, id_label, fields, label):
    """詢問代號與要修改的欄位（Enter 略過）後呼叫修改函式。"""
    item_id = ask(f"{id_label}：")
    print("只填要修改的欄位，不改的直接按 Enter。")
    new_data = ask_fields(fields)
    if not new_data:
        print("沒有要修改的欄位")
        return
    show_result(function(state, item_id, new_data), f"{label}成功")


def do_by_one_id(state, function, id_label, label, show_data=False):
    """詢問一個代號後呼叫函式。"""
    item_id = ask(f"{id_label}：")
    show_result(function(state, item_id), f"{label}成功", show_data)


def do_by_two_ids(state, function, first_label, second_label, label,
                  show_data=True):
    """詢問兩個代號（如學號與課號）後呼叫函式。"""
    first = ask(f"{first_label}：")
    second = ask(f"{second_label}：")
    show_result(function(state, first, second), f"{label}成功", show_data)


# ---------- 個別功能 ----------

def do_query_courses(state):
    """依條件查詢課程，條件可略過。"""
    filters = {}
    for key, label in (("course_id", "課號"), ("teacher", "教師"),
                       ("day", "星期（1～7）"), ("category", "必選修")):
        text = ask(f"{label}（可略過）：")
        if text:
            filters[key] = parse_value(text) if key == "day" else text
    if ask("只看還有名額的課程？（y/N）：").lower() == "y":
        filters["has_seats"] = True
    include_cancelled = ask("包含已取消課程？（y/N）：").lower() == "y"
    result = query_courses(state, filters, include_cancelled)
    if result["ok"]:
        print_courses(result["data"])
    else:
        print_errors(result["errors"])


def do_list_students(state):
    """列出指定課程的修課學生。"""
    result = list_course_students(state, ask("課號："))
    if not result["ok"]:
        print_errors(result["errors"])
        return
    for student in result["data"]:
        print(f"{student['student_id']} {student['name']} {student['department']}")
    print(f"共 {len(result['data'])} 人")


def do_schedule(state):
    """顯示個人課表。"""
    result = build_schedule(state, ask("學號："))
    if result["ok"]:
        print_schedule(result["data"])
    else:
        print_errors(result["errors"])


def do_free_blocks(state):
    """查詢連續空閒時段。"""
    student_id = ask("學號：")
    scope = {}
    days_text = ask("星期（逗號分隔，Enter 表示 1～7）：")
    if days_text:
        scope["days"] = [parse_value(item) for item in parse_list(days_text)]
    from_period = ask("起始節次（Enter 表示從 1）：")
    if from_period:
        scope["from_period"] = from_period
    to_period = ask("結束節次（Enter 表示到 c）：")
    if to_period:
        scope["to_period"] = to_period
    min_text = ask("最少連續節數（Enter 表示 1）：")
    min_len = parse_value(min_text) if min_text else 1
    result = find_free_blocks(state, student_id, scope, min_len)
    if not result["ok"]:
        print_errors(result["errors"])
        return
    if not result["data"]:
        print("沒有符合的空閒區段")
    for block in result["data"]:
        print(f"週{DAY_NAMES[block['day'] - 1]} 第{block['start_period']}～"
              f"{block['end_period']}節（{block['length']} 節）")


def do_query_activities(state):
    """列出所有活動（含已取消）。"""
    result = query_activities(state, None, True)
    if not result["ok"]:
        print_errors(result["errors"])
        return
    if not result["data"]:
        print("查無資料")
    for act in result["data"]:
        print(f"{act['activity_id']} {act['name']} {act['date']} "
              f"{act['start_time']}-{act['end_time']} 教室：{act.get('room_id')} "
              f"[{act.get('status', 'active')}]")


def load_demo_data(state):
    """暫時用：以 F1 函式放入幾筆示範資料（F6 合併後移除）。"""
    rooms = [
        {"room_id": "R101", "building": "一教", "capacity": 60,
         "equipment": ["computer", "projector"]},
        {"room_id": "R201", "building": "二教", "capacity": 30},
    ]
    courses = [
        {"course_id": "1150001", "name": "微積分", "credits": 3,
         "category": "required", "teacher": "王大明", "capacity": 50,
         "room_id": "R101",
         "slots": [{"day": 2, "period": "3"}, {"day": 2, "period": "4"}]},
        {"course_id": "1150002", "name": "Python 程式設計", "credits": 3,
         "category": "elective", "teacher": "李小華", "capacity": 30,
         "room_id": "R201",
         "slots": [{"day": 2, "period": "3"}]},
        {"course_id": "1150003", "name": "資料結構", "credits": 3,
         "category": "required", "teacher": "陳老師", "capacity": 30,
         "room_id": "R201",
         "slots": [{"day": 3, "period": "1"}, {"day": 3, "period": "2"}]},
    ]
    students = [
        {"student_id": "115590001", "name": "陳小明", "department": "資工三甲"},
        {"student_id": "115590002", "name": "林小美", "department": "資工三甲",
         "credit_limit": 6},
    ]
    for function, records in ((add_room, rooms), (add_course, courses),
                              (add_student, students)):
        for record in records:
            result = function(state, record)
            if not result["ok"]:
                print_errors(result["errors"])
    print("示範資料已載入（若有錯誤，代表該筆已存在或資料不合法）")


# ---------- 選單 ----------

def run_menu(title, items, state, back_label="返回"):
    """顯示選單並重複執行，直到選 0。items 為 (名稱, 處理函式) 清單。"""
    while True:
        print(f"\n=== {title} ===")
        for number, (label, _) in enumerate(items, 1):
            print(f"{number} {label}")
        print(f"0 {back_label}")
        choice = ask("請選擇：")
        if choice == "0":
            return
        if choice.isdigit() and 1 <= int(choice) <= len(items):
            items[int(choice) - 1][1](state)
        else:
            print("無效的選項")


def build_menus():
    """建立各層選單內容，回傳頂層選單項目。"""
    course_items = [
        ("新增課程", lambda s: do_create(s, add_course, COURSE_FIELDS, "新增課程")),
        ("修改課程", lambda s: do_modify(s, modify_course, "課號",
                                       COURSE_FIELDS[1:], "修改課程")),
        ("取消課程", lambda s: do_by_one_id(s, cancel_course, "課號",
                                          "取消課程", True)),
        ("刪除課程", lambda s: do_by_one_id(s, delete_course, "課號", "刪除課程")),
        ("查詢課程", do_query_courses),
        ("查詢修課名單", do_list_students),
    ]
    people_items = [
        ("新增學生", lambda s: do_create(s, add_student, STUDENT_FIELDS, "新增學生")),
        ("刪除學生", lambda s: do_by_one_id(s, delete_student, "學號", "刪除學生")),
        ("新增教室", lambda s: do_create(s, add_room, ROOM_FIELDS, "新增教室")),
        ("刪除教室", lambda s: do_by_one_id(s, delete_room, "教室代號", "刪除教室")),
    ]
    enroll_items = [
        ("檢查能否加選（不加選）", lambda s: do_enrollment(s, check_enrollment)),
        ("加選課程", lambda s: do_enrollment(s, enroll)),
        ("退選課程", lambda s: do_by_two_ids(s, drop, "學號", "課號", "退選")),
    ]
    schedule_items = [
        ("查看個人課表", do_schedule),
        ("查詢空閒時段", do_free_blocks),
    ]
    activity_items = [
        ("建立活動", lambda s: do_create(s, add_activity, ACTIVITY_FIELDS,
                                       "建立活動")),
        ("配置教室", lambda s: do_by_one_id(s, assign_room, "活動代號",
                                          "配置教室", True)),
        ("修改活動", lambda s: do_modify(s, modify_activity, "活動代號",
                                       ACTIVITY_FIELDS[1:], "修改活動")),
        ("取消活動", lambda s: do_by_one_id(s, cancel_activity, "活動代號",
                                          "取消活動")),
        ("查詢活動", do_query_activities),
        ("檢查能否報名（不報名）", lambda s: do_by_two_ids(
            s, check_signup, "學號", "活動代號", "檢查")),
        ("報名活動", lambda s: do_by_two_ids(
            s, signup_activity, "學號", "活動代號", "報名")),
        ("取消報名", lambda s: do_by_two_ids(
            s, cancel_signup, "學號", "活動代號", "取消報名")),
    ]
    return [
        ("課程管理", lambda s: run_menu("課程管理", course_items, s)),
        ("學生與教室", lambda s: run_menu("學生與教室", people_items, s)),
        ("選課", lambda s: run_menu("選課", enroll_items, s)),
        ("課表", lambda s: run_menu("課表", schedule_items, s)),
        ("活動", lambda s: run_menu("活動", activity_items, s)),
        ("載入示範資料（暫時）", load_demo_data),
    ]


def main():
    """建立 State，進入主選單。"""
    state = State()
    try:
        run_menu("選課與課表規劃系統", build_menus(), state, "離開")
    except (KeyboardInterrupt, EOFError):
        print("\n已中斷")
    print("再見")


if __name__ == "__main__":
    main()
