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
        
            