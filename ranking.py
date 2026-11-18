# recommendation/ranking.py

from typing import Any

import config
from scoring import calculate_post_score
from diversity import apply_diversity


def generate_reasons(
    score_breakdown: dict[str, float],
    is_followed: bool,
) -> list[str]:
    """Generate short, understandable explanations for a ranking."""

    reasons = []

    if is_followed:
        reasons.append("followed creator")

    if score_breakdown["topic"] > 0:
        reasons.append("topic match")

    if score_breakdown["freshness"] >= 0.5:
        reasons.append("recent post")

    if score_breakdown["engagement"] >= 0.10:
        reasons.append("good engagement")

    if score_breakdown["exploration"] > 0:
        reasons.append("exploration")

    if not reasons:
        reasons.append("general relevance")

    return reasons[:3]


def rank_posts(
    candidates: list[dict[str, Any]],
    user_features: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Score, sort, and apply diversity to candidate posts.

    This function does not fetch posts from a database.
    Candidates must be supplied by the backend.
    """
    if len(candidates) > config.MAX_CANDIDATES:
        raise ValueError(
            f"Maximum {config.MAX_CANDIDATES} candidates are allowed."
        )

    if not candidates:
        return []

    scored_posts = []

    for candidate in candidates:
        scored_post = calculate_post_score(
            post=candidate,
            user_features=user_features,
        )

        scored_posts.append(scored_post)

    # Highest score first.
    scored_posts.sort(
        key=lambda post: post["score"],
        reverse=True,
    )

    # Apply creator and topic diversity.
    diversified_posts = apply_diversity(scored_posts)

    # Add short explanations.
    candidate_lookup = {
        str(candidate["post_id"]): candidate
        for candidate in candidates
    }

    results = []

    for post in diversified_posts:
        original_candidate = candidate_lookup[
            str(post["post_id"])
        ]

        reasons = generate_reasons(
            score_breakdown=post["score_breakdown"],
            is_followed=bool(
                original_candidate.get("is_followed", False)
            ),
        )

        results.append({
            "post_id": post["post_id"],
            "score": post["score"],
            "reasons": reasons,
        })

    return results


def build_recommendation_response(
    candidates: list[dict[str, Any]],
    user_features: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the response payload for the recommendation endpoint.
    """
    ranked_posts = rank_posts(
        candidates=candidates,
        user_features=user_features,
    )

    return {
        "model": config.MODEL_NAME,
        "ranked_posts": ranked_posts,
        "total_candidates": len(candidates),
    }