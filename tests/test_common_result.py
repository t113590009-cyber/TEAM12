import pytest
from src.common.result import make_ok, make_error, make_result
@pytest.mark.normal
def test_make_ok_returns_ok_true():
    result = make_ok({"x": 1})
    assert result["ok"] is True
    assert result["data"] == {"x": 1}
    assert result["errors"] == []


@pytest.mark.normal
def test_make_error_has_three_keys():
    error = make_error("NOT_FOUND", "課程不存在", {"course_id": "1150001"})
    assert error["code"] == "NOT_FOUND"
    assert error["message"] == "課程不存在"
    assert error["detail"] == {"course_id": "1150001"}


@pytest.mark.normal
def test_make_result_with_errors_is_not_ok():
    error = make_error("NOT_FOUND", "課程不存在")
    result = make_result(None, [error])
    assert result["ok"] is False
    assert result["errors"][0]["code"] == "NOT_FOUND"


@pytest.mark.boundary
def test_make_result_empty_errors_is_ok():
    result = make_result([], [])
    assert result["ok"] is True


@pytest.mark.boundary
def test_make_error_default_detail_is_empty_dict():
    error = make_error("NOT_FOUND", "課程不存在")
    assert error["detail"] == {}

@pytest.mark.error
def test_make_result_keeps_partial_data_on_failure():
    error = make_error("NOT_FOUND", "課程不存在")
    result = make_result({"partial": True}, [error])
    assert result["ok"] is False
    assert result["data"] == {"partial": True}
