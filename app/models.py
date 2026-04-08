from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: int
    tg_id: Optional[int]
    full_name: Optional[str] = None
    phone: Optional[str] = None
    class_name: Optional[str] = None
    age: Optional[int] = None
    address: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @property
    def is_profile_complete(self) -> bool:
        return all([self.full_name, self.phone, self.class_name])


@dataclass
class Channel:
    id: int
    channel_id: int
    username: str
    created_at: Optional[datetime] = None


@dataclass
class Test:
    id: int
    code: str
    content: str
    answer_key: str
    question_count: int
    points_per_correct: float
    created_at: Optional[datetime] = None
    
    @property
    def max_score(self) -> float:
        return self.question_count * self.points_per_correct


@dataclass
class TestResult:
    id: int
    test_id: int
    user_id: int
    correct: int
    wrong: int
    score: float
    finished_at: Optional[datetime] = None