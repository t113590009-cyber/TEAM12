import json
import pytest
from src.common.state import State
from src.f6_storage import save_all, load_all


@pytest.mark.boundary
def test_save_load_empty_state(tmp_path):
    state = State()

    saved = save_all(state, tmp_path)
    assert saved["ok"] is True
    assert saved["errors"] == []

    loaded = load_all(tmp_path)
    assert loaded["ok"] is True
    assert loaded["errors"] == []

    new_state = loaded["data"]

    assert new_state.rooms == {}
    assert new_state.courses == {}
    assert new_state.students == {}
    assert new_state.activities == {}
    assert new_state.enrollments == set()
    assert new_state.activity_signups == set()


@pytest.mark.error
def test_load_corrupted_json(tmp_path):
    state = State()

    saved = save_all(state, tmp_path)
    assert saved["ok"] is True

    file = tmp_path / "courses.json"
    file.write_text("{invalid json", encoding="utf-8")

    result = load_all(tmp_path)

    assert result["ok"] is False

    assert [e["code"] for e in result["errors"]] == [
        "INVALID_FILE"
    ]

    assert result["errors"][0]["detail"] == {
        "file": "courses.json",
        "reason": "NOT_JSON"
    }



@pytest.mark.error
def test_load_missing_json_file(tmp_path):
    state = State()

    saved = save_all(state, tmp_path)
    assert saved["ok"] is True

    file = tmp_path / "students.json"
    file.unlink()

    result = load_all(tmp_path)

    assert result["ok"] is False
    assert len(result["errors"]) == 1

    assert result["errors"][0]["code"] == "FILE_NOT_FOUND"
    assert result["errors"][0]["detail"] == {
        "file": "students.json"
    }

    assert isinstance(result["data"], State)
    assert result["data"].students == {}



@pytest.mark.error
def test_load_invalid_record(tmp_path):
    state = State()

    saved = save_all(state, tmp_path)
    assert saved["ok"] is True

    file = tmp_path / "enrollments.json"

    data = json.loads(file.read_text(encoding="utf-8"))

    data["course_enrollments"].append({
        "student_id": 123,
        "course_id": "C1"
    })

    file.write_text(
        json.dumps(data),
        encoding="utf-8"
    )

    result = load_all(tmp_path)

    assert result["ok"] is False
    assert len(result["errors"]) == 1

    error = result["errors"][0]

    assert error["code"] == "INVALID_RECORD"
    assert error["detail"]["file"] == "enrollments.json"
    assert error["detail"]["index"] == 0

    assert error["detail"]["errors"][0]["code"] == "INVALID_FIELD"

    assert result["data"].enrollments == set()



@pytest.mark.error
def test_load_reference_missing(tmp_path):
    state = State()

    saved = save_all(state, tmp_path)
    assert saved["ok"] is True

    file = tmp_path / "enrollments.json"

    data = json.loads(file.read_text(encoding="utf-8"))

    data["course_enrollments"].append({
        "student_id": "S404",
        "course_id": "C404"
    })

    file.write_text(
        json.dumps(data),
        encoding="utf-8"
    )

    result = load_all(tmp_path)

    assert result["ok"] is False
    assert len(result["errors"]) == 2

    assert [e["code"] for e in result["errors"]] == [
        "REFERENCE_MISSING",
        "REFERENCE_MISSING"
    ]

    assert [e["detail"]["field"] for e in result["errors"]] == [
        "student_id",
        "course_id"
    ]

    assert [e["detail"]["ref_id"] for e in result["errors"]] == [
        "S404",
        "C404"
    ]

    assert result["data"].enrollments == set()
