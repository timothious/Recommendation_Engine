
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import config
from ranking import rank_posts


# --------------------------------------------------
# Application
# --------------------------------------------------

app = FastAPI(
    title="Halal SNS Recommendation Engine",
    description=(
        "A rule-based recommendation service that scores, "
        "ranks, and diversifies eligible candidate posts."
    ),
    version="1.0.0",
)


# --------------------------------------------------
# Request Schemas
# --------------------------------------------------

class CandidatePost(BaseModel):
    post_id: str
    creator_id: str

    topics: list[str] = Field(default_factory=list)

    age_hours: float = Field(ge=0)

    likes: int = Field(default=0, ge=0)
    saves: int = Field(default=0, ge=0)
    impressions: int = Field(default=0, ge=0)

    is_followed: bool = False

    source: str

    # Optional until penalty rules are finalized.
    penalty: float = Field(default=0.0, ge=0)


class UserFeatures(BaseModel):
    topic_weights: dict[str, float] = Field(
        default_factory=dict
    )

    recent_creator_engagement: dict[str, float] = Field(
        default_factory=dict
    )

    impressions_count: int = Field(default=0, ge=0)
    positive_actions_count: int = Field(default=0, ge=0)


class RecommendationRequest(BaseModel):
    user_id: str

    candidates: list[CandidatePost] = Field(
        min_length=1,
        max_length=200
    )

    user_features: UserFeatures = Field(
        default_factory=UserFeatures
    )

    context: Optional[dict] = None


# --------------------------------------------------
# Response Schemas
# --------------------------------------------------

class RankedPost(BaseModel):
    post_id: str
    score: float
    reasons: list[str]


class RecommendationResponse(BaseModel):
    model: str
    user_id: str
    ranked_posts: list[RankedPost]
    total_candidates: int


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "recommendation-engine"
    }


# --------------------------------------------------
# Recommendation Endpoint
# --------------------------------------------------

@app.post(
    "/recommendation",
    response_model=RecommendationResponse
)
def get_recommendations(
    request: RecommendationRequest
):
    try:
        # Convert Pydantic models into dictionaries.
        candidates = [
            candidate.model_dump()
            for candidate in request.candidates
        ]

        user_features = request.user_features.model_dump()

        # Ensure candidate IDs are unique.
        candidate_ids = [
            candidate["post_id"]
            for candidate in candidates
        ]

        if len(candidate_ids) != len(set(candidate_ids)):
            raise HTTPException(
                status_code=400,
                detail="Duplicate post IDs found in candidates."
            )

        # Rank and apply diversity.
        ranked_posts = rank_posts(
            candidates=candidates,
            user_features=user_features
        )

        # Return the ranked results.
        return {
            "model": getattr(config, "MODEL_NAME", "rules_v1"),
            "user_id": request.user_id,
            "ranked_posts": ranked_posts,
            "total_candidates": len(candidates)
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation processing failed: {str(error)}"
        )


# --------------------------------------------------
# Run Locally
# --------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
