import pytest
from src.common.periods import period_index
from src.common.periods import is_valid_slot

@pytest.mark.boundary
@pytest.mark.parametrize("x,expected",[
    (1,1),
    ("c",12),
    ("C",12),
])
def test_period_index_boundary(x,expected):
    assert period_index(x)==expected
    
    
@pytest.mark.normal
@pytest.mark.parametrize("y,expected",[
    (2,2),
    (3,3),
    (4,4),
    (5,5),
    (6,6),
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


@pytest.mark.boundary	
@pytest.mark.parametrize("x1,x2,expected",[
    (5,"7",True),
    (5,"a",True),
    (5,"b",True),
])
def test_is_valid_slot_accepts_normal(x1,x2,expected):
    slot={"day":x1, "period": x2}
    assert is_valid_slot(slot)==expected


@pytest.mark.boundary
@pytest.mark.parametrize("x1,x2,expected",[
    (1,"1",True),
    (7,"1",True),
    (1,"c",True),
    (7,"c",True),
])
def test_is_valid_slot_accepts_boundary(x1,x2,expected):
    slot={"day":x1, "period": x2}
    assert is_valid_slot(slot)==expected


@pytest.mark.boundary
@pytest.mark.parametrize("x1,x2,expected",[
    (0,"d",False),
    (0,"0",False),
    (0,"10",False),
    (8,"d",False),
    (8,"0",False),
    (8,"10",False),
])
def test_is_valid_slot_rejects_boundary(x1,x2,expected):
    slot={"day":x1, "period": x2}
    assert is_valid_slot(slot)==expected
    


@pytest.mark.boundary
@pytest.mark.parametrize("x1,x2,expected",[
    (0,"True",False),
    (0,"False",False),
    (8,"2.0",False),
    (8,"None",False),
])
def test_is_valid_slot_rejects_boundary(x1,x2,expected):
    slot={"day":x1, "period": x2}
    assert is_valid_slot(slot)==expected


@pytest.mark.boundary
@pytest.mark.parametrize("x1,x2,expected",[
    (" ","True",False),
    (0," ",False),
    ("None","2.0",False),
    (" "," ",False),
])
def test_is_valid_slot_rejects_missing_field(x1,x2,expected):
    slot={"day":x1, "period": x2}
    assert is_valid_slot(slot)==expected

@pytest.mark.boundary
@pytest.mark.parametrize("x1,x2,expected",[
    ("acc","True",False),
    ("0"," ",False),
    ([{"day": 2, "period": "3"}],"2.0",False),
    (" "," ",False),
])
def test_is_valid_slot_rejects_non_dict(x1,x2,expected):
    slot={"day":x1, "period": x2}
    assert is_valid_slot(slot)==expected
    
