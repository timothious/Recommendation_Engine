# recommendation/diversity.py

from typing import Any

import config


def has_same_topic(
    first_topics: list[str],
    second_topics: list[str],
) -> bool:
    """Return True when two posts share at least one topic."""
    return bool(set(first_topics) & set(second_topics))


def violates_diversity(
    candidate: dict[str, Any],
    selected_posts: list[dict[str, Any]],
) -> bool:
    """
    Check whether adding a candidate would create more than
    the allowed number of consecutive posts from one creator
    or one topic.
    """
    if len(selected_posts) < 2:
        return False

    previous_two = selected_posts[-2:]

    candidate_creator = candidate.get("creator_id")
    candidate_topics = candidate.get("topics", [])

    # Check creator repetition.
    same_creator = all(
        post.get("creator_id") == candidate_creator
        for post in previous_two
    )

    if (
        same_creator
        and config.MAX_CONSECUTIVE_SAME_CREATOR == 2
    ):
        return True

    # Check topic repetition.
    same_topic = all(
        has_same_topic(
            post.get("topics", []),
            candidate_topics,
        )
        for post in previous_two
    )

    if (
        candidate_topics
        and same_topic
        and config.MAX_CONSECUTIVE_SAME_TOPIC == 2
    ):
        return True

    return False


def apply_diversity(
    ranked_posts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Reorder scored posts to reduce repeated creators and topics.

    The original score order is preserved as much as possible.
    A post that violates diversity is delayed, not removed.

    If no remaining post can satisfy the rule, the highest-ranked
    remaining post is placed next so that no candidate is lost.
    """
    remaining = ranked_posts.copy()
    selected: list[dict[str, Any]] = []

    while remaining:
        selected_index = None

        # Find the highest-ranked post that satisfies diversity.
        for index, candidate in enumerate(remaining):
            if not violates_diversity(candidate, selected):
                selected_index = index
                break

        # If all remaining posts violate the rule, preserve the
        # highest-ranked one. It may be impossible to satisfy
        # diversity when the remaining candidates are too similar.
        if selected_index is None:
            selected_index = 0

        selected_post = remaining.pop(selected_index)
        selected.append(selected_post)

    return selected