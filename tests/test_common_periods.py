import pytest
from src.common.periods import period_index
from src.common.periods import is_valid_slot
from src.common.periods import slots_overlap
from src.common.periods import _time_to_minutes
from src.common.periods import time_ranges_overlap

## period_index的測試
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

## is_valid_slot的測試資料
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
    (0,True,False),
    (0,False,False),
    (8,"2.0",False),
    (8,None,False),
])
def test_is_valid_slot_rejects_boundary(x1,x2,expected):
    slot={"day":x1, "period": x2}
    assert is_valid_slot(slot)==expected


@pytest.mark.boundary
@pytest.mark.parametrize("x1,x2,expected",[
    (" ",True,False),
    (0," ",False),
    ("None","2.0",False),
    (" "," ",False),
])
def test_is_valid_slot_rejects_missing_field(x1,x2,expected):
    slot={"day":x1, "period": x2}
    assert is_valid_slot(slot)==expected

@pytest.mark.boundary
@pytest.mark.parametrize("x1,x2,expected",[
    ("acc",True,False),
    ("0"," ",False),
    ([{"day": 2, "period": "3"}],"2.0",False),
    (" "," ",False),
])
def test_is_valid_slot_rejects_non_dict(x1,x2,expected):
    slot={"day":x1, "period": x2}
    assert is_valid_slot(slot)==expected

##slot_overlap測試資料
@pytest.mark.normal
@pytest.mark.parametrize("x1,x2,x3,x4,expected",[
   (2,"3",2,"3",True),
   (5,"7",5,"7",True),
   (1,"a",1,"a",True),
])
def test_slots_overlap_same_slot(x1,x2,x3,x4,expected):
    slot1={"day":x1, "period": x2}
    slot2={"day":x3, "period": x4}
    assert slots_overlap(slot1,slot2)==expected

@pytest.mark.normal
@pytest.mark.parametrize("x1,x2,x3,x4,expected",[
   (2,"3",3,"3",False),
   (1,"5",7,"5",False),
])
def test_slots_overlap_different_day(x1,x2,x3,x4,expected):
    slot1={"day":x1, "period": x2}
    slot2={"day":x3, "period": x4}
    assert slots_overlap(slot1,slot2)==expected


@pytest.mark.normal
@pytest.mark.parametrize("x1,x2,x3,x4,expected",[
   (2,"3",2,"5",False),
   (4,"1",4,"c",False),
])
def test_slots_overlap_different_period(x1,x2,x3,x4,expected):
    slot1={"day":x1, "period": x2}
    slot2={"day":x3, "period": x4}
    assert slots_overlap(slot1,slot2)==expected
    

@pytest.mark.boundary
@pytest.mark.parametrize("x1,x2,x3,x4,expected",[
   (2,"3",2,"4",False),
   (2,"4",2,"5",False),
   (2,"9",2,"a",False),
])
def test_slots_overlap_adjacent_periods(x1,x2,x3,x4,expected):
    slot1={"day":x1, "period": x2}
    slot2={"day":x3, "period": x4}
    assert slots_overlap(slot1,slot2)==expected


@pytest.mark.boundary
@pytest.mark.parametrize("x1,x2,x3,x4,expected",[
   (1,"1",1,"1",True),
   (7,"c",7,"c",True),
])
def test_slots_overlap_day_edges(x1,x2,x3,x4,expected):
    slot1={"day":x1, "period": x2}
    slot2={"day":x3, "period": x4}
    assert slots_overlap(slot1,slot2)==expected
    

@pytest.mark.error
@pytest.mark.parametrize("x1,x2,x3,x4,expected",[
    (8,"3",8,"3",False),
   (0,"3",0,"3",False),
   (2,"d",2,"d",False),
   (True,"9",True,"a",False),
])
def test_slots_overlap_rejects_invalid_slot(x1,x2,x3,x4,expected):
    slot1={"day":x1, "period": x2}
    slot2={"day":x3, "period": x4}
    assert slots_overlap(slot1,slot2)==expected


@pytest.mark.normal
@pytest.mark.parametrize("x1,expected",[
   ("10:30",630),
   ("12:00",720),
   ("08:10",490),
   ("21:10",1270),
])
def test_time_to_minutes_overlap_normal(x1,expected):
    assert _time_to_minutes(x1)==expected


@pytest.mark.boundary
@pytest.mark.parametrize("x1,expected",[
   ("00:00",0),
   ("00:01",1),
   ("23:59",1439),
])
def test_time_to_minutes_boundary(x1,expected):
    assert _time_to_minutes(x1)==expected


@pytest.mark.error
@pytest.mark.parametrize("x1,expected",[
   ("9:30",None),
   ("10:30 ",None),
   ("1a:30",None),
   (["10:30"],None),
   (" ",None),
])
def test_time_to_minutes_error(x1,expected):
    assert _time_to_minutes(x1)==expected

@pytest.mark.normal
@pytest.mark.parametrize("a_start,a_end,b_start,b_end,expected", [
    ("10:00", "11:00", "10:30", "11:30", True),
    ("10:00", "11:00", "12:00", "13:00", False),
    ("14:10", "15:00", "14:30", "16:00", True),
    ("08:10", "09:00", "15:10", "16:00", False),
])
def test_time_ranges_overlap_normal(a_start, a_end, b_start, b_end, expected):
    assert time_ranges_overlap(a_start, a_end, b_start, b_end) is expected
    assert time_ranges_overlap(b_start, b_end, a_start, a_end) is expected


@pytest.mark.boundary
@pytest.mark.parametrize("a_start,a_end,b_start,b_end,expected", [
    ("10:00", "11:00", "11:00", "12:00", False),   
    ("10:00", "11:00", "10:00", "11:00", True),   
    ("10:00", "11:00", "11:01", "12:00", False),  
    ("10:00", "11:00", "10:00", "10:30", True),    
    ("10:00", "11:00", "10:30", "11:00", True),  
    ("00:00", "12:00", "12:00", "23:59", False),  
    ("00:00", "23:59", "23:00", "23:59", True),  
    ("08:10", "09:00", "09:00", "09:10", False),   
])
def test_time_ranges_overlap_boundary(a_start, a_end, b_start, b_end, expected):
    assert time_ranges_overlap(a_start, a_end, b_start, b_end) is expected
    assert time_ranges_overlap(b_start, b_end, a_start, a_end) is expected


BAD_VALUES = ["9:30", "24:00", "10:60", "ab:cd", "", None, 1030]


@pytest.mark.error
@pytest.mark.parametrize("bad_value", BAD_VALUES)
@pytest.mark.parametrize("position", [0, 1, 2, 3])
def test_time_ranges_overlap_rejects_bad_value(position, bad_value):
  
    args = ["10:00", "11:00", "10:30", "11:30"]
    args[position] = bad_value
    assert time_ranges_overlap(*args) is False
    assert time_ranges_overlap(args[2], args[3], args[0], args[1]) is False


@pytest.mark.error
@pytest.mark.parametrize("a_start,a_end,b_start,b_end", [
    ("11:00", "10:00", "10:30", "11:30"),   # A 起訖顛倒
    ("10:00", "11:00", "11:30", "10:30"),   # B 起訖顛倒
    ("10:00", "10:00", "10:30", "11:30"),   # A 起訖相同
    ("10:00", "11:00", "10:30", "10:30"),   # B 起訖相同
])
def test_time_ranges_overlap_rejects_bad_range(a_start, a_end, b_start, b_end):
    assert time_ranges_overlap(a_start, a_end, b_start, b_end) is False
    assert time_ranges_overlap(b_start, b_end, a_start, a_end) is False