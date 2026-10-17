import pytest
from src.common.state import State


@pytest.mark.normal
def test_new_state_is_empty():
    state = State()
    assert state.courses == {}
    assert state.students == {}
    assert state.rooms == {}
    assert state.activities == {}
    assert state.enrollments == set()
    assert state.activity_signups == set()


@pytest.mark.boundary
def test_two_states_do_not_share_data():
    first_state = State()
    first_state.courses["1150001"] = {}
    second_state = State()
    assert second_state.courses == {}


@pytest.mark.error
def test_unequal_states_compare_not_equal():
    other = State()
    other.rooms["R101"] = {}
    assert State() != other
    