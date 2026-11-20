"""F6 資料儲存與載入（資料存取：組員 B）。

save_all / load_all 把 State 存成資料夾下的五個 JSON 檔，或從資料夾讀回。
載入時使用與 F1 相同的驗證函式（src/common/validators.py）；單筆錯誤只跳過該筆，
程式不中止。業務錯誤不拋例外，統一回傳 {ok, data, errors}（資料格式書第 7、9 章）。
"""
import json
import os

from src.common.result import make_error, make_result
from src.common.state import State
from src.common.validators import (validate_activity, validate_course,
                                   validate_room, validate_student)

FILE_VERSION = 1
ROOMS_FILE = "rooms.json"
COURSES_FILE = "courses.json"
STUDENTS_FILE = "students.json"
ACTIVITIES_FILE = "activities.json"
ENROLLMENTS_FILE = "enrollments.json"
ALL_FILES = (ROOMS_FILE, COURSES_FILE, STUDENTS_FILE, ACTIVITIES_FILE, ENROLLMENTS_FILE)


# ---------------------------------------------------------------- 存檔

def _sorted_records(mapping):
    """依代號排序後取出記錄清單。"""
    return [mapping[key] for key in sorted(mapping)]


def _build_payloads(state):
    """把 State 轉成 {檔名: 要寫出的 dict}；記錄依代號排序，選課與報名依 (學號, 代號) 排序。"""
    return {
        ROOMS_FILE: {"version": FILE_VERSION, "records": _sorted_records(state.rooms)},
        COURSES_FILE: {"version": FILE_VERSION, "records": _sorted_records(state.courses)},
        STUDENTS_FILE: {"version": FILE_VERSION, "records": _sorted_records(state.students)},
        ACTIVITIES_FILE: {"version": FILE_VERSION, "records": _sorted_records(state.activities)},
        ENROLLMENTS_FILE: {
            "version": FILE_VERSION,
            "course_enrollments": [{"student_id": sid, "course_id": cid}
                                   for sid, cid in sorted(state.enrollments)],
            "activity_signups": [{"student_id": sid, "activity_id": aid}
                                 for sid, aid in sorted(state.activity_signups)],
        },
    }


def _write_json(path, payload):
    """先寫暫存檔，成功後再取代正式檔，避免寫到一半造成損毀。"""
    temp_path = path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_path, path)
    except OSError:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def save_all(state, folder):
    """Input: state、資料夾路徑。
    Process: 資料夾不存在就建立；把 State 分成五個 JSON 檔寫出（UTF-8、ensure_ascii=False、
    indent=2、鍵順序固定、記錄依代號排序），每個檔先寫暫存檔再取代正式檔。
    Output: {ok, data={folder, files}, errors}。
    Boundary: 空資料集也能儲存；某檔寫入失敗（磁碟、權限）回 INVALID_FILE 且 reason 為
    WRITE_FAILED，其他檔照常寫；不修改 state。"""
    errors = []
    written = []
    payloads = _build_payloads(state)
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError as exc:
        return make_result(None, [make_error("INVALID_FILE", "無法建立資料夾",
                                             {"file": str(folder), "reason": "WRITE_FAILED",
                                              "os_error": str(exc)})])
    for name in ALL_FILES:
        try:
            _write_json(os.path.join(folder, name), payloads[name])
            written.append(name)
        except OSError as exc:
            errors.append(make_error("INVALID_FILE", "檔案寫入失敗",
                                     {"file": name, "reason": "WRITE_FAILED", "os_error": str(exc)}))
    return make_result({"folder": str(folder), "files": written}, errors)


# ---------------------------------------------------------------- 讀檔

def _bad_structure(name):
    """整檔結構不對（不是 dict、缺 records 等）。"""
    return make_error("INVALID_FILE", "檔案結構不正確，以空資料載入",
                      {"file": name, "reason": "BAD_STRUCTURE"})


def _read_json(folder, name):
    """讀一個 JSON 檔。回傳 (payload, error)；成功時 error 為 None。"""
    path = os.path.join(folder, name)
    if not os.path.isfile(path):
        return None, make_error("FILE_NOT_FOUND", "缺檔，以空資料載入", {"file": name})
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle), None
    except OSError:
        reason = "READ_FAILED"
    except (ValueError, RecursionError):  # JSONDecodeError、UnicodeDecodeError 都是 ValueError
        reason = "NOT_JSON"
    return None, make_error("INVALID_FILE", "檔案損毀，以空資料載入", {"file": name, "reason": reason})


def _record_errors(name, index, record, id_field, problems):
    """把驗證錯誤分成 INVALID_RECORD（欄位不合法）與 REFERENCE_MISSING（教室不存在）。"""
    others = [e for e in problems if e["code"] != "NOT_FOUND"]
    if others:
        return [make_error("INVALID_RECORD", "單筆資料不合法，已跳過",
                           {"file": name, "index": index, "errors": others})]
    return [make_error("REFERENCE_MISSING", "引用的代號不存在，已跳過",
                       {"file": name, "record_id": record.get(id_field),
                        "field": "room_id", "ref_id": e["detail"]["room_id"]})
            for e in problems]


def _load_entities(state, folder, name, validate_fn, id_field, store, errors):
    """載入 rooms／courses／students／activities 其中一個檔：逐筆驗證，合法才放入 store。"""
    payload, error = _read_json(folder, name)
    if error:
        errors.append(error)
        return
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        errors.append(_bad_structure(name))
        return
    for index, record in enumerate(records):
        result = validate_fn(state, record, is_new=True)
        if result["ok"]:
            store[result["data"][id_field]] = result["data"]
        else:
            errors.extend(_record_errors(name, index, record, id_field, result["errors"]))


def _pair_problems(state, entry, id_field, known, store):
    """檢查一筆選課／報名紀錄。回傳 (不合法錯誤清單, 不存在的引用 [(欄位, 代號)])。"""
    if not isinstance(entry, dict):
        return [make_error("INVALID_FIELD", "紀錄必須為 dict", {"field": "entry"})], []
    student_id, target_id = entry.get("student_id"), entry.get(id_field)
    bad = [make_error("INVALID_FIELD", "欄位缺漏或不合法", {"field": field})
           for field, value in (("student_id", student_id), (id_field, target_id))
           if not isinstance(value, str)]
    if bad:
        return bad, []
    refs = [(field, value) for field, value, table in
            (("student_id", student_id, state.students), (id_field, target_id, known))
            if value not in table]
    if refs:
        return [], refs
    if id_field == "course_id" and known[target_id].get("status", "active") == "cancelled":
        bad.append(make_error("COURSE_CANCELLED", "選課紀錄指向已取消課程", {"course_id": target_id}))
    if (student_id, target_id) in store:
        bad.append(make_error("DUPLICATE_ID", "選課或報名紀錄重複",
                              {"student_id": student_id, id_field: target_id}))
    return bad, []


def _load_pairs(state, entries, id_field, known, store, errors):
    """載入選課或報名清單；有問題的單筆跳過並記錄。"""
    for index, entry in enumerate(entries):
        bad, refs = _pair_problems(state, entry, id_field, known, store)
        if bad:
            errors.append(make_error("INVALID_RECORD", "單筆資料不合法，已跳過",
                                     {"file": ENROLLMENTS_FILE, "index": index, "errors": bad}))
        for field, ref_id in refs:
            record_id = f"{entry['student_id']}:{entry[id_field]}"
            errors.append(make_error("REFERENCE_MISSING", "引用的代號不存在，已跳過",
                                     {"file": ENROLLMENTS_FILE, "record_id": record_id,
                                      "field": field, "ref_id": ref_id}))
        if not bad and not refs:
            store.add((entry["student_id"], entry[id_field]))


def _load_enrollments(state, folder, errors):
    """載入 enrollments.json（選課與活動報名兩份清單，缺任一份視為整檔結構不對）。"""
    payload, error = _read_json(folder, ENROLLMENTS_FILE)
    if error:
        errors.append(error)
        return
    keys = ("course_enrollments", "activity_signups")
    if not isinstance(payload, dict) or not all(isinstance(payload.get(k), list) for k in keys):
        errors.append(_bad_structure(ENROLLMENTS_FILE))
        return
    _load_pairs(state, payload["course_enrollments"], "course_id",
                state.courses, state.enrollments, errors)
    _load_pairs(state, payload["activity_signups"], "activity_id",
                state.activities, state.activity_signups, errors)


def load_all(folder):
    """Input: 資料夾路徑。
    Process: 依序載入 rooms → courses → students → activities → enrollments（後者引用前者）；
    逐筆用 F1 的驗證函式檢查，只做欄位與引用驗證，不做衝堂、學分、人數上限檢查。
    Output: {ok, data=State, errors}；有任何錯誤時 ok=False，但 data 仍是可用的 State。
    Boundary: 檔案不存在（FILE_NOT_FOUND）或整檔損毀（INVALID_FILE）以空資料載入該檔、其他檔照常；
    單筆不合法（INVALID_RECORD，含重複代號、指向已取消課程、重複選課）、引用不存在
    （REFERENCE_MISSING）跳過該筆；資料夾不存在視為五個檔都缺；程式不中止。"""
    state = State()
    errors = []
    _load_entities(state, folder, ROOMS_FILE, validate_room, "room_id", state.rooms, errors)
    _load_entities(state, folder, COURSES_FILE, validate_course, "course_id", state.courses, errors)
    _load_entities(state, folder, STUDENTS_FILE, validate_student, "student_id", state.students, errors)
    _load_entities(state, folder, ACTIVITIES_FILE, validate_activity, "activity_id",
                   state.activities, errors)
    _load_enrollments(state, folder, errors)
    return make_result(state, errors)
