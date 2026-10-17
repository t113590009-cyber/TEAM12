import pytest
from src.common.periods import period_index


@pytest.mark.normal
def test_period_index_digit():
    assert period_index("1") == 1