from src.common.result import make_error, make_result


def _not_found(kind, key, value):
    return make_error("NOT_FOUND", "找不到資料", {"kind": kind, key: value})


def check_enrollment(state, student_id, course_id):
    """檢查學生是否可以加選課程。

    Input: state、student_id、course_id
    Process: 目前只做前置檢查(學生、課程是否存在),其餘檢查之後逐項加入
    Output: {ok, data, errors}
    Boundary: 前置檢查失敗時只回傳該錯誤,不再執行後面的檢查
    """
    errors = []
    if student_id not in state.students:
        errors.append(_not_found("student", "student_id", student_id))
    if course_id not in state.courses:
        errors.append(_not_found("course", "course_id", course_id))
    return make_result(None, errors)