def make_ok(data=None):
    """
    Input：data，成功時的結果，預設 None。
    Process：組成一個有三個鍵的字典。
    Output：ok 為 True、errors 為空清單的字典。
    Boundary：data 可以是 None、空字典、空清單，都原樣放進去。
    """
    return {"ok": True, "data": data,"errors":[]}


def make_error(code,message,detail=None):
    """
    Input：錯誤碼、中文說明、細節 dict（預設空 dict）。
    Process：組成一個字典。
    Output：有 code、message、detail 三個鍵的字典。
    Boundary：detail 沒給時改成空字典。
    """
    if detail is None:
        detail = {}
    return {"code": code, "message": message, "detail": detail}


def make_result(data,errors):
    """Input：data 結果或部分結果、errors 錯誤清單。
Process：errors 為空就 ok 是 True，否則是 False；errors 複製一份。
Output：有 ok、data、errors 三個鍵的字典。
Boundary：errors 是空清單時 ok 為 True；失敗時 data 可以保留部分結果。
    """
    errors_list = list(errors)
    return {"ok": len(errors) == 0, "data": data, "errors": errors_list}
