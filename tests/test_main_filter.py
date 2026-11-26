from main import do_filter
from src.f1_data import add_course, add_student


def test_do_filter_prints_candidates(state, monkeypatch, capsys):
    add_student(state, {"student_id": "115590001", "name": "陳小明",
                        "department": "資工三甲"})
    add_course(state, {
        "course_id": "1150001", "name": "微積分", "credits": 3,
        "category": "elective", "teacher": "王大明", "capacity": 30,
        "room_id": "R101", "slots": [{"day": 2, "period": "3"}]})
    answers = iter(["115590001", "", "", "", "", "", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    do_filter(state)
    out = capsys.readouterr().out
    assert "1150001 微積分" in out
    assert "條件可行" in out