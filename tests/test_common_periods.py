import pytest
from src.common.periods import period_index


@pytest.mark.boundary
def test_period_index_digit_one():
    assert period_index("1") == 1
    
    
@pytest.mark.normal
def test_period_index_digit_two():
    assert period_index("2") == 2
    
    
@pytest.mark.normal
def test_period_index_digit_three():
    assert period_index("3") == 3
    
    
@pytest.mark.normal
def test_period_index_digit_four():
    assert period_index("4") == 4
    
    
@pytest.mark.normal
def test_period_index_digit_five():
    assert period_index("5") == 5
    
    
@pytest.mark.normal
def test_period_index_digit_six():
    assert period_index("6") == 6
    
    
@pytest.mark.normal
def test_period_index_digit_seven():
    assert period_index("7") == 7
    
    
@pytest.mark.normal
def test_period_index_digit_eight():
    assert period_index("8") == 8
    
    
@pytest.mark.normal
def test_period_index_digit_nine():
    assert period_index("9") == 9
    
    
@pytest.mark.normal
def test_period_index_letter_a():
    assert period_index("a") == 10
    
    
@pytest.mark.normal
def test_period_index_letter_b():
    assert period_index("b") == 11
    
    
@pytest.mark.boundary
def test_period_index_letter_c():
    assert period_index("c") == 12


@pytest.mark.error
def test_period_index_rejects_d():
    assert period_index("d") == None
    
    
@pytest.mark.error
def test_period_index_rejects_0():
    assert period_index("0") == None
    
    
@pytest.mark.error
def test_period_index_rejects_10():
    assert period_index("10") == None