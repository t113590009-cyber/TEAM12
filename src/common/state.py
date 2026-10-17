from dataclasses import dataclass, field

@dataclass
class State:
    """系統所有會變的資料，由 main 建立並傳入各函式。
    
    Input:沒有必填參數，欄位預設為空。
    Process:dataclass 自動產生建立與比較的功能。
    Output:State 物件。
    Boundary:只存原始資料，修課人數和學分由函式推導，不存在這裡。
    """
    courses: dict[str, dict] = field(default_factory=dict)
    students: dict[str, dict] = field(default_factory=dict)
    rooms: dict[str, dict] = field(default_factory=dict)
    activities: dict[str, dict] = field(default_factory=dict)
    enrollments: set[tuple[str, str]] = field(default_factory=set)
    activity_signups: set[tuple[str, str]] = field(default_factory=set)
