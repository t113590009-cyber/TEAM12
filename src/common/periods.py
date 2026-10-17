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