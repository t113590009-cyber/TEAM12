"""F3 個人課表產生 - D 負責"""

from src.common.time_slot import period_index


def build_schedule(state, student_id):
    """產生學生每週課表
    輸入：state, student_id
    輸出：{"ok": bool, "data": {"grid": ..., "stats": ...}, "errors": [...]}
    TODO: 第 7 週實作
    """
    raise NotImplementedError


def find_free_blocks(state, student_id, scope, min_len):
    """找連續空堂
    TODO: 第 7 週實作
    """
    raise NotImplementedError
