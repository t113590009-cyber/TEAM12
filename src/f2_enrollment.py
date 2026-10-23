from src.common.result import make_error, make_result


def _not_found(kind, key, value):
    return make_error("NOT_FOUND", "找不到資料", {"kind": kind, key: value})


def _precheck_errors(state, student_id, course_id):
    """前置檢查,依序為 NOT_FOUND、COURSE_CANCELLED、ALREADY_ENROLLED。

    Input: state、student_id、course_id
    Process: 依序檢查,第一組失敗就回傳,不再往下
    Output: 錯誤清單,全部通過回 []
    Boundary: 學生與課程都不存在時回兩筆 NOT_FOUND
    """
    errors = []
    if student_id not in state.students:
        errors.append(_not_found("student", "student_id", student_id))
    if course_id not in state.courses:
        errors.append(_not_found("course", "course_id", course_id))
    if errors:
        return errors
    if state.courses[course_id].get("status", "active") == "cancelled":
        return [make_error("COURSE_CANCELLED", "課程已取消",
                           {"course_id": course_id})]
    if (student_id, course_id) in state.enrollments:
        return [make_error("ALREADY_ENROLLED", "已選過此課程",
                           {"student_id": student_id, "course_id": course_id})]
    return []


def check_enrollment(state, student_id, course_id):
    """檢查學生是否可以加選課程。

    Input: state、student_id、course_id
    Process: 目前只做前置檢查,其餘五項檢查之後逐項加入
    Output: {ok, data, errors}
    Boundary: 前置檢查失敗時只回傳該錯誤,不再執行後面的檢查
    """
    return make_result(None, _precheck_errors(state, student_id, course_id))