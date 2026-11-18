from pydantic import BaseModel
from typing import List


class CandidatePost(BaseModel):
    post_id: str
    creator_id: str
    topics: List[str]
    age_hours: float
    likes: int
    saves: int
    impressions: int
    is_followed: bool
    source: str


class RecommendationRequest(BaseModel):
    request_id: str
    user_id: str
    candidates: List[CandidatePost]