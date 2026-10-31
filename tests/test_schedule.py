"""F3 個人課表與連續空堂測試。"""

from src.f1_data import add_course, add_student
from src.schedule import build_schedule, find_free_blocks


def _add_student(state, student_id="115590001"):
    result = add_student(state, {
        "student_id": student_id,
        "name": "測試學生",
        "department": "資工三甲",
    })
    assert result["ok"], result["errors"]


def _add_course(state, course_id="1150001", slots=None, status="active"):
    result = add_course(state, {
        "course_id": course_id,
        "name": "測試課程",
        "credits": 3,
        "category": "required",
        "teacher": "測試教師",
        "capacity": 30,
        "room_id": "R101",
        "slots": slots or [{"day": 1, "period": "1"}],
        "status": status,
    })
    assert result["ok"], result["errors"]


def test_build_schedule_unknown_student_returns_not_found(state):
    result = build_schedule(state, "115590099")
    assert result["ok"] is False
    assert result["data"] is None
    assert result["errors"][0]["code"] == "NOT_FOUND"


def test_build_schedule_creates_week_grid_and_places_enrolled_course(state):
    _add_student(state)
    _add_course(state, slots=[{"day": 1, "period": "1"},
                              {"day": 3, "period": "a"}])
    state.enrollments.add(("115590001", "1150001"))

    result = build_schedule(state, "115590001")

    assert result["ok"] is True
    assert len(result["data"]["grid"]) == 7
    assert all(len(row) == 12 for row in result["data"]["grid"])
    assert result["data"]["grid"][0][0] == {"type": "course", "id": "1150001"}
    assert result["data"]["grid"][2][9] == {"type": "course", "id": "1150001"}
    assert result["data"]["stats"] == {
        "course_count": 1, "activity_count": 0, "free_slots": 82
    }


def test_build_schedule_ignores_cancelled_course(state):
    _add_student(state)
    _add_course(state, status="cancelled")
    state.enrollments.add(("115590001", "1150001"))

    result = build_schedule(state, "115590001")

    assert result["ok"] is True
    assert result["data"]["stats"]["course_count"] == 0
    assert result["data"]["grid"][0][0] is None


def test_find_free_blocks_finds_contiguous_periods_in_scope(state):
    _add_student(state)
    _add_course(state, slots=[{"day": 1, "period": "1"},
                              {"day": 1, "period": "2"}])
    state.enrollments.add(("115590001", "1150001"))

    result = find_free_blocks(
        state, "115590001",
        {"day": 1, "start_period": "1", "end_period": "4"}, min_len=2
    )

    assert result["ok"] is True
    assert result["data"] == [{
        "day": 1, "start_period": "3", "end_period": "4", "length": 2
    }]


def test_find_free_blocks_rejects_invalid_min_len(state):
    _add_student(state)
    result = find_free_blocks(state, "115590001", min_len=0)
    assert result["ok"] is False
    assert result["errors"][0]["code"] == "INVALID_FIELD"


def test_find_free_blocks_unknown_student_returns_not_found(state):
    result = find_free_blocks(state, "115590099")
    assert result["ok"] is False
    assert result["errors"][0]["code"] == "NOT_FOUND"
