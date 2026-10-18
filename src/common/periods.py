def period_index(period):
    class_period=["1","2","3","4","5","6","7","8","9","a","b","c"]
    class_number=[1,2,3,4,5,6,7,8,9,10,11,12]
    if type(period) is int :
        if str(period) in class_period:
            return class_number[class_period.index(str(period))]
        else:
            return None
    elif type(period) is str:
        if period.lower() in class_period:
            return class_number[class_period.index(period.lower())]
        else:
            return None
    else:
        return None
    
def is_valid_slot(slot):
    if(type(slot) is not dict):
        return False
    elif(slot.get("day")==None or slot.get("period")==None):
        return False 
    elif((type(slot["day"]) is not int) or (1>slot["day"] or slot["day"]>7)):
        return False    
    elif(period_index(slot["period"])==None):
        return False
    else:
        return True
    
def slots_overlap(slot1,slot2):
    if(is_valid_slot(slot1) and is_valid_slot(slot2)):
        return(slot1["day"]==slot2["day"] and period_index(slot1["period"])==period_index(slot2["period"]))
    else:
        return False
 
def _time_to_minutes(time_str):
    digits = "0123456789"
    if type(time_str) is not str or len(time_str) != 5 or time_str[2] != ":":
        return None
    if not all(char in digits for char in time_str[0:2] + time_str[3:5]):
        return None
    hour, minute = int(time_str[0:2]), int(time_str[3:5])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour * 60 + minute


def time_ranges_overlap(start_a, end_a, start_b, end_b):
    times = [_time_to_minutes(value) for value in (start_a, end_a, start_b, end_b)]
    if None in times:
        return False
    start_a, end_a, start_b, end_b = times
    if start_a >= end_a or start_b >= end_b:
        return False
    return start_a < end_b and start_b < end_a
        