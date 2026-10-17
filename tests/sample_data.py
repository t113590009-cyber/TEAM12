"""F1 測試資料：5 間教室、20 門課、15 名學生（供 C、D、E 重用）。

build_sample_state(state) 只經 F1 的 add_* 建立合法資料；
plant_room_conflict(state) 另外直接植入一筆教室衝堂（F1 會擋，所以只能直接寫 state）。
"""
from src.f1_data import add_course, add_room, add_student, cancel_course

ROOMS = [("R101", "一教", 20), ("R102", "一教", 40), ("R103", "二教", 60),
         ("R104", "二教", 80), ("R105", "二教", 100)]
PERIODS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c"]


def _course(i):
    """第 i 門課：教室、星期由 i % 5 決定，節次由 i // 5 決定，保證同教室不衝堂。"""
    room_id, _, room_cap = ROOMS[i % 5]
    return {"course_id": str(1150001 + i), "name": f"課程{i + 1}", "credits": 1 + i % 3,
            "category": "required" if i % 4 == 0 else "elective", "teacher": f"教師{i % 6}",
            "capacity": min(30, room_cap), "room_id": room_id,
            "slots": [{"day": 1 + i % 5, "period": PERIODS[i // 5]}]}


def build_sample_state(state):
    """建立 5 教室、20 課、15 學生，並加入：學生衝堂組、3 時段課、節次 c 課、額滿課、已取消課。"""
    for room_id, building, capacity in ROOMS:
        assert add_room(state, {"room_id": room_id, "building": building, "capacity": capacity,
                                "equipment": ["projector"] if capacity >= 60 else []})["ok"]
    courses = [_course(i) for i in range(20)]
    courses[6]["slots"] = list(courses[0]["slots"])
    courses[3]["slots"] += [{"day": 4, "period": "c"}, {"day": 5, "period": "9"}]
    courses[7]["capacity"] = 2
    for course in courses:
        assert add_course(state, course)["ok"], course
    for i in range(15):
        assert add_student(state, {"student_id": str(115590001 + i), "name": f"學生{i + 1}",
                                   "department": "資工三甲",
                                   "credit_limit": 9 if i == 0 else 24})["ok"]
    state.enrollments.update({("115590001", "1150001"), ("115590002", "1150008"),
                              ("115590003", "1150008"), ("115590004", "1150020")})
    assert cancel_course(state, "1150020")["ok"]
    return state


# AI實作：直接寫入 state 植入教室衝堂資料
def plant_room_conflict(state):
    """直接植入 1150099：與 1150001 同教室同時段（模擬資料不一致，供 F2 防線測試）。"""
    first = state.courses["1150001"]
    state.courses["1150099"] = {**first, "course_id": "1150099", "name": "植入衝堂",
                                "slots": list(first["slots"])}
    return state
