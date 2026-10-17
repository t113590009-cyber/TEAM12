import pytest
from src.common.periods import period_index


@pytest.mark.boundary
@pytest.mark.parametrize("x,expected",[
    ("1",1),
    ("c",12),
    ("C",12),
])
def test_period_index_boundary(x,expected):
    assert period_index(x)==expected
    
    
@pytest.mark.normal
@pytest.mark.parametrize("y,expected",[
    ("2",2),
    ("3",3),
    ("4",4),
    ("5",5),
    ("6",6),
    ("7",7),
    ("8",8),
    ("9",9),
    ("a",10),
    ("b",11),
    ("A",10),
    ("B",11),
])
def test_period_index_digit_normal(y,expected):
    assert period_index(y)==expected
    

@pytest.mark.error
@pytest.mark.parametrize("z,expected",[
    ("d",None),
    ("0",None),
    ("True",None),
    ("False",None),
    ("3.0",None),
    (" ",None),
])
def test_period_index_rejects_(z,expected):
    assert period_index("z") == expected
