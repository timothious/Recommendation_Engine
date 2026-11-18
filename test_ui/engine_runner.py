"""Helpers for the recommendation engine test UI."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import config
import diversity
import ranking
import scoring


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

DEFAULT_OVERRIDES = {
    "TOPIC_WEIGHT": config.TOPIC_WEIGHT,
    "RELATIONSHIP_WEIGHT": config.RELATIONSHIP_WEIGHT,
    "FRESHNESS_WEIGHT": config.FRESHNESS_WEIGHT,
    "ENGAGEMENT_WEIGHT": config.ENGAGEMENT_WEIGHT,
    "EXPLORATION_WEIGHT": config.EXPLORATION_WEIGHT,
    "DEFAULT_FRESHNESS_HALF_LIFE_HOURS": config.DEFAULT_FRESHNESS_HALF_LIFE_HOURS,
    "FOLLOWED_FRESHNESS_HALF_LIFE_HOURS": config.FOLLOWED_FRESHNESS_HALF_LIFE_HOURS,
    "ENGAGEMENT_SMOOTHING_K": config.ENGAGEMENT_SMOOTHING_K,
    "ENGAGEMENT_PRIOR": config.ENGAGEMENT_PRIOR,
    "SAVE_WEIGHT": config.SAVE_WEIGHT,
    "MAX_CONSECUTIVE_SAME_CREATOR": config.MAX_CONSECUTIVE_SAME_CREATOR,
    "MAX_CONSECUTIVE_SAME_TOPIC": config.MAX_CONSECUTIVE_SAME_TOPIC,
    "EXPLORATION_SOURCE": config.EXPLORATION_SOURCE,
}


def list_scenario_files() -> list[Path]:
    """Return all JSON scenario files in the data folder."""
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.glob("*.json"))


def load_scenario(path: Path) -> dict[str, Any]:
    """Load one candidate scenario JSON file."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@contextmanager
def apply_config(overrides: dict[str, Any]) -> Iterator[None]:
    """Temporarily patch config values used by scoring and diversity."""
    previous = {key: getattr(config, key) for key in overrides}
    try:
        for key, value in overrides.items():
            setattr(config, key, value)
        yield
    finally:
        for key, value in previous.items():
            setattr(config, key, value)


def score_all(
    candidates: list[dict[str, Any]],
    user_features: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        scoring.calculate_post_score(post=candidate, user_features=user_features)
        for candidate in candidates
    ]


def run_pipeline(
    candidates: list[dict[str, Any]],
    user_features: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """
    Run the full ranking pipeline and return intermediate stages
    so the UI can show how each step works.
    """
    with apply_config(overrides):
        scored = score_all(candidates, user_features)
        sorted_posts = sorted(scored, key=lambda post: post["score"], reverse=True)
        diversified = diversity.apply_diversity(sorted_posts)

        candidate_lookup = {
            str(candidate["post_id"]): candidate for candidate in candidates
        }

        ranked = []
        for post in diversified:
            original = candidate_lookup[str(post["post_id"])]
            reasons = ranking.generate_reasons(
                score_breakdown=post["score_breakdown"],
                is_followed=bool(original.get("is_followed", False)),
            )
            ranked.append(
                {
                    "post_id": post["post_id"],
                    "creator_id": post.get("creator_id"),
                    "topics": post.get("topics", []),
                    "score": post["score"],
                    "score_breakdown": post["score_breakdown"],
                    "reasons": reasons,
                    "source": original.get("source", ""),
                    "is_followed": bool(original.get("is_followed", False)),
                    "age_hours": original.get("age_hours", 0),
                    "likes": original.get("likes", 0),
                    "saves": original.get("saves", 0),
                    "impressions": original.get("impressions", 0),
                }
            )

        diversity_moves = _find_diversity_moves(sorted_posts, diversified)

        return {
            "scored": scored,
            "sorted": sorted_posts,
            "diversified": diversified,
            "ranked": ranked,
            "diversity_moves": diversity_moves,
            "overrides": dict(overrides),
        }


def explain_post(
    post: dict[str, Any],
    user_features: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """Build a step-by-step formula explanation for one post."""
    with apply_config(overrides):
        topic_weights = user_features.get("topic_weights", {})
        creator_engagement = user_features.get("recent_creator_engagement", {})

        topics = post.get("topics", [])
        topic_parts = [
            {
                "topic": topic,
                "weight": float(topic_weights.get(topic, 0.0)),
            }
            for topic in topics
        ]
        topic_raw = sum(max(0.0, part["weight"]) for part in topic_parts)
        topic_score = scoring.calculate_topic_score(topics, topic_weights)

        is_followed = bool(post.get("is_followed", False))
        creator_id = str(post.get("creator_id", ""))
        engagement_with_creator = float(
            creator_engagement.get(creator_id, 0.0)
        )
        relationship_score = scoring.calculate_relationship_score(
            is_followed=is_followed,
            creator_id=creator_id,
            recent_creator_engagement=creator_engagement,
        )

        age_hours = float(post.get("age_hours", 0))
        half_life = (
            config.FOLLOWED_FRESHNESS_HALF_LIFE_HOURS
            if is_followed
            else config.DEFAULT_FRESHNESS_HALF_LIFE_HOURS
        )
        freshness_score = scoring.calculate_freshness_score(age_hours, is_followed)

        likes = int(post.get("likes", 0))
        saves = int(post.get("saves", 0))
        impressions = int(post.get("impressions", 0))
        k = config.ENGAGEMENT_SMOOTHING_K
        prior = config.ENGAGEMENT_PRIOR
        save_weight = config.SAVE_WEIGHT
        engagement_score = scoring.calculate_engagement_score(
            likes=likes,
            saves=saves,
            impressions=impressions,
        )

        source = post.get("source", "")
        exploration_score = scoring.calculate_exploration_score(source)
        penalty = scoring.clamp(float(post.get("penalty", config.DEFAULT_PENALTY)))

        weighted = {
            "topic": config.TOPIC_WEIGHT * topic_score,
            "relationship": config.RELATIONSHIP_WEIGHT * relationship_score,
            "freshness": config.FRESHNESS_WEIGHT * freshness_score,
            "engagement": config.ENGAGEMENT_WEIGHT * engagement_score,
            "exploration": config.EXPLORATION_WEIGHT * exploration_score,
        }
        final_before_floor = sum(weighted.values()) - penalty
        final_score = max(0.0, final_before_floor)

        return {
            "post_id": post.get("post_id"),
            "topic": {
                "parts": topic_parts,
                "raw_sum": topic_raw,
                "score": topic_score,
                "formula": "topic = min(1, sum(user_weight[t] for t in post.topics))",
            },
            "relationship": {
                "is_followed": is_followed,
                "creator_id": creator_id,
                "creator_engagement": engagement_with_creator,
                "score": relationship_score,
                "formula": (
                    "relationship = 1.0 if followed else 0.5 * recent_creator_engagement"
                ),
            },
            "freshness": {
                "age_hours": age_hours,
                "half_life": half_life,
                "score": freshness_score,
                "formula": "freshness = 0.5 ** (age_hours / half_life)",
            },
            "engagement": {
                "likes": likes,
                "saves": saves,
                "impressions": impressions,
                "k": k,
                "prior": prior,
                "save_weight": save_weight,
                "numerator": likes + save_weight * saves + k * prior,
                "denominator": impressions + k,
                "score": engagement_score,
                "formula": (
                    "engagement = (likes + save_weight*saves + k*prior) / (impressions + k)"
                ),
            },
            "exploration": {
                "source": source,
                "exploration_source": config.EXPLORATION_SOURCE,
                "score": exploration_score,
                "formula": "exploration = 1 if source == exploration else 0",
            },
            "final": {
                "weights": {
                    "topic": config.TOPIC_WEIGHT,
                    "relationship": config.RELATIONSHIP_WEIGHT,
                    "freshness": config.FRESHNESS_WEIGHT,
                    "engagement": config.ENGAGEMENT_WEIGHT,
                    "exploration": config.EXPLORATION_WEIGHT,
                },
                "weighted_parts": weighted,
                "penalty": penalty,
                "before_floor": final_before_floor,
                "score": final_score,
                "formula": (
                    "score = w_t*topic + w_r*rel + w_f*fresh + w_e*eng + w_x*expl - penalty"
                ),
            },
        }


def _find_diversity_moves(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """List posts whose position changed because of diversity reordering."""
    before_pos = {
        str(post["post_id"]): index for index, post in enumerate(before)
    }
    moves = []
    for index, post in enumerate(after):
        post_id = str(post["post_id"])
        old_index = before_pos[post_id]
        if old_index != index:
            moves.append(
                {
                    "post_id": post_id,
                    "from": old_index + 1,
                    "to": index + 1,
                    "creator_id": post.get("creator_id"),
                    "topics": post.get("topics", []),
                }
            )
    return moves
