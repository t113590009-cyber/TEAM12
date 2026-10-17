"""共用 fixture。State 定案後（A 負責）請改成 from src.common.state import State。"""
from dataclasses import dataclass, field

import pytest

from src.f1_data import add_room

try:
    from src.common.state import State
except ImportError:
    @dataclass
    class State:
        courses: dict = field(default_factory=dict)
        students: dict = field(default_factory=dict)
        rooms: dict = field(default_factory=dict)
        activities: dict = field(default_factory=dict)
        enrollments: set = field(default_factory=set)
        activity_signups: set = field(default_factory=set)


@pytest.fixture
def state():
    """含 R101（容量 60）與 R102（容量 30）的空 State。"""
    s = State()
    add_room(s, {"room_id": "R101", "building": "一教", "capacity": 60, "equipment": ["projector"]})
    add_room(s, {"room_id": "R102", "building": "二教", "capacity": 30})
    return s


@pytest.fixture
def new_state():
    """建立全空 State 的工廠。"""
    return State
