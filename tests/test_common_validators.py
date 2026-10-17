import pytest

from src.common.validators import (is_int_value, is_valid_id, normalize_period, normalize_slot,
                                   COURSE_ID_RE)


@pytest.mark.normal
@pytest.mark.parametrize("raw,expected", [(1, "1"), (9, "9"), ("a", "a"), ("C", "c"), ("5", "5")])
def test_normalize_period_valid(raw, expected):
    assert normalize_period(raw) == expected


@pytest.mark.boundary
@pytest.mark.parametrize("raw", [0, 10, "d", "0", "10", "", True, None, 1.0, "ab"])
def test_normalize_period_invalid(raw):
    assert normalize_period(raw) is None


@pytest.mark.boundary
@pytest.mark.parametrize("value,expected", [(3, True), (3.0, True), (2.5, False), (True, False), ("3", False), (None, False)])
def test_is_int_value(value, expected):
    assert is_int_value(value) is expected


@pytest.mark.error
@pytest.mark.parametrize("value", [1150001, None, "1150001\n", "１１５０００１", "abc"])
def test_is_valid_id_rejects(value):
    assert is_valid_id(value, COURSE_ID_RE) is False


@pytest.mark.error
@pytest.mark.parametrize("slot", [None, "x", {"day": 8, "period": "1"}, {"day": True, "period": "1"}, {"day": 1}])
def test_normalize_slot_invalid(slot):
    assert normalize_slot(slot) is None
