# recommendation/scoring.py

from typing import Any

import config


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """Keep a numeric value within a specified range."""
    return max(minimum, min(value, maximum))


def calculate_topic_score(
    post_topics: list[str],
    user_topic_weights: dict[str, float],
) -> float:
    """
    Calculate how relevant a post's topics are to the user.

    A post with no topics receives a score of 0.
    The total score cannot exceed 1.
    """
    if not post_topics:
        return 0.0

    total = sum(
        max(0.0, float(user_topic_weights.get(topic, 0.0)))
        for topic in post_topics
    )

    return clamp(total)


def calculate_relationship_score(
    is_followed: bool,
    creator_id: str,
    recent_creator_engagement: dict[str, float],
) -> float:
    """
    Followed creators receive 1.0.

    Other creators receive half of their recent engagement
    score with the user.
    """
    if is_followed:
        return 1.0

    engagement = float(
        recent_creator_engagement.get(str(creator_id), 0.0)
    )

    return clamp(0.5 * engagement)


def calculate_freshness_score(
    age_hours: float,
    is_followed: bool,
) -> float:
    """
    Calculate freshness using exponential decay.

    Followed creators use a 72-hour half-life.
    Other posts use a 24-hour half-life.
    """
    age_hours = max(0.0, float(age_hours))

    if is_followed:
        half_life = config.FOLLOWED_FRESHNESS_HALF_LIFE_HOURS
    else:
        half_life = config.DEFAULT_FRESHNESS_HALF_LIFE_HOURS

    return 0.5 ** (age_hours / half_life)


def calculate_engagement_score(
    likes: int,
    saves: int,
    impressions: int,
) -> float:
    """
    Calculate smoothed engagement quality.

    Formula:
        (likes + 2 * saves + k * prior) / (impressions + k)

    The result is clamped to [0, 1].
    """
    likes = max(0, int(likes))
    saves = max(0, int(saves))
    impressions = max(0, int(impressions))

    k = config.ENGAGEMENT_SMOOTHING_K
    prior = config.ENGAGEMENT_PRIOR

    numerator = (
        likes
        + config.SAVE_WEIGHT * saves
        + k * prior
    )

    denominator = impressions + k

    if denominator == 0:
        return 0.0

    return clamp(numerator / denominator)


def calculate_exploration_score(source: str) -> float:
    """Give exploration-source posts an exploration score of 1."""
    return (
        1.0
        if source == config.EXPLORATION_SOURCE
        else 0.0
    )


def calculate_post_score(
    post: dict[str, Any],
    user_features: dict[str, Any],
) -> dict[str, Any]:
    """
    Calculate the final recommendation score for one post.

    Expected post fields:
        post_id, creator_id, topics, age_hours,
        likes, saves, impressions, is_followed, source

    Expected user_features:
        topic_weights
        recent_creator_engagement
    """
    topic_weights = user_features.get("topic_weights", {})
    creator_engagement = user_features.get(
        "recent_creator_engagement", {}
    )

    topic_score = calculate_topic_score(
        post_topics=post.get("topics", []),
        user_topic_weights=topic_weights,
    )

    relationship_score = calculate_relationship_score(
        is_followed=bool(post.get("is_followed", False)),
        creator_id=str(post.get("creator_id", "")),
        recent_creator_engagement=creator_engagement,
    )

    freshness_score = calculate_freshness_score(
        age_hours=post.get("age_hours", 0),
        is_followed=bool(post.get("is_followed", False)),
    )

    engagement_score = calculate_engagement_score(
        likes=post.get("likes", 0),
        saves=post.get("saves", 0),
        impressions=post.get("impressions", 0),
    )

    exploration_score = calculate_exploration_score(
        source=post.get("source", "")
    )

    # Penalty values are not finalized in the plan.
    # A caller may supply a precomputed penalty from 0 to 1.
    penalty = clamp(
        float(post.get("penalty", config.DEFAULT_PENALTY))
    )

    final_score = (
        config.TOPIC_WEIGHT * topic_score
        + config.RELATIONSHIP_WEIGHT * relationship_score
        + config.FRESHNESS_WEIGHT * freshness_score
        + config.ENGAGEMENT_WEIGHT * engagement_score
        + config.EXPLORATION_WEIGHT * exploration_score
        - penalty
    )

    final_score = max(0.0, final_score)

    return {
        "post_id": post["post_id"],
        "creator_id": post.get("creator_id"),
        "topics": post.get("topics", []),
        "score": round(final_score, 6),
        "score_breakdown": {
            "topic": round(topic_score, 6),
            "relationship": round(relationship_score, 6),
            "freshness": round(freshness_score, 6),
            "engagement": round(engagement_score, 6),
            "exploration": round(exploration_score, 6),
            "penalty": round(penalty, 6),
        },
    }