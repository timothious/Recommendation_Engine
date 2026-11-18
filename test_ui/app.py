"""
Recommendation Engine — interactive test UI.

Run from the project root:
    .venv/bin/streamlit run test_ui/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from test_ui.engine_runner import (  # noqa: E402
        DEFAULT_OVERRIDES,
        explain_post,
        list_scenario_files,
        load_scenario,
        run_pipeline,
    )
except ImportError:
    from engine_runner import (  # noqa: E402
        DEFAULT_OVERRIDES,
        explain_post,
        list_scenario_files,
        load_scenario,
        run_pipeline,
    )


st.set_page_config(
    page_title="Recommendation Engine Lab",
    page_icon="📊",
    layout="wide",
)


def format_weight_sum(overrides: dict) -> float:
    return (
        overrides["TOPIC_WEIGHT"]
        + overrides["RELATIONSHIP_WEIGHT"]
        + overrides["FRESHNESS_WEIGHT"]
        + overrides["ENGAGEMENT_WEIGHT"]
        + overrides["EXPLORATION_WEIGHT"]
    )


def _init_slider_defaults() -> None:
    defaults = {
        "w_topic": float(DEFAULT_OVERRIDES["TOPIC_WEIGHT"]),
        "w_relationship": float(DEFAULT_OVERRIDES["RELATIONSHIP_WEIGHT"]),
        "w_freshness": float(DEFAULT_OVERRIDES["FRESHNESS_WEIGHT"]),
        "w_engagement": float(DEFAULT_OVERRIDES["ENGAGEMENT_WEIGHT"]),
        "w_exploration": float(DEFAULT_OVERRIDES["EXPLORATION_WEIGHT"]),
        "half_life": int(DEFAULT_OVERRIDES["DEFAULT_FRESHNESS_HALF_LIFE_HOURS"]),
        "followed_half_life": int(DEFAULT_OVERRIDES["FOLLOWED_FRESHNESS_HALF_LIFE_HOURS"]),
        "eng_k": int(DEFAULT_OVERRIDES["ENGAGEMENT_SMOOTHING_K"]),
        "eng_prior": float(DEFAULT_OVERRIDES["ENGAGEMENT_PRIOR"]),
        "save_weight": int(DEFAULT_OVERRIDES["SAVE_WEIGHT"]),
        "max_creator": int(DEFAULT_OVERRIDES["MAX_CONSECUTIVE_SAME_CREATOR"]),
        "max_topic": int(DEFAULT_OVERRIDES["MAX_CONSECUTIVE_SAME_TOPIC"]),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def sidebar_controls() -> tuple[Path | None, dict]:
    st.sidebar.title("Controls")
    _init_slider_defaults()

    if st.sidebar.button("Reset to plan defaults"):
        for key in list(st.session_state.keys()):
            if key.startswith(("w_", "half_", "followed_", "eng_", "save_", "max_")):
                del st.session_state[key]
        _init_slider_defaults()
        st.rerun()

    files = list_scenario_files()
    if not files:
        st.sidebar.error("No JSON files found in `data/`.")
        return None, dict(DEFAULT_OVERRIDES)

    labels = {path.name: path for path in files}
    selected_name = st.sidebar.selectbox(
        "Candidate scenario",
        options=list(labels.keys()),
        help="All `.json` files in the `data/` folder appear here.",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Score weights")
    st.sidebar.caption("Drag bars to change how much each signal matters.")

    topic = st.sidebar.slider("Topic", 0.0, 1.0, key="w_topic")
    relationship = st.sidebar.slider("Relationship", 0.0, 1.0, key="w_relationship")
    freshness = st.sidebar.slider("Freshness", 0.0, 1.0, key="w_freshness")
    engagement = st.sidebar.slider("Engagement", 0.0, 1.0, key="w_engagement")
    exploration = st.sidebar.slider("Exploration", 0.0, 1.0, key="w_exploration")

    weight_sum = topic + relationship + freshness + engagement + exploration
    if abs(weight_sum - 1.0) < 0.001:
        st.sidebar.success(f"Weights sum to {weight_sum:.2f}")
    else:
        st.sidebar.warning(f"Weights sum to {weight_sum:.2f} (plan target is 1.00)")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Freshness & engagement")

    half_life = st.sidebar.slider("Default half-life (hours)", 1, 168, key="half_life")
    followed_half_life = st.sidebar.slider(
        "Followed half-life (hours)", 1, 168, key="followed_half_life"
    )
    k = st.sidebar.slider("Engagement smoothing k", 1, 100, key="eng_k")
    prior = st.sidebar.slider("Engagement prior", 0.0, 0.5, step=0.01, key="eng_prior")
    save_weight = st.sidebar.slider("Save weight", 1, 5, key="save_weight")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Diversity")
    max_creator = st.sidebar.slider(
        "Max consecutive same creator", 1, 5, key="max_creator"
    )
    max_topic = st.sidebar.slider(
        "Max consecutive same topic", 1, 5, key="max_topic"
    )

    overrides = {
        "TOPIC_WEIGHT": topic,
        "RELATIONSHIP_WEIGHT": relationship,
        "FRESHNESS_WEIGHT": freshness,
        "ENGAGEMENT_WEIGHT": engagement,
        "EXPLORATION_WEIGHT": exploration,
        "DEFAULT_FRESHNESS_HALF_LIFE_HOURS": half_life,
        "FOLLOWED_FRESHNESS_HALF_LIFE_HOURS": followed_half_life,
        "ENGAGEMENT_SMOOTHING_K": k,
        "ENGAGEMENT_PRIOR": prior,
        "SAVE_WEIGHT": save_weight,
        "MAX_CONSECUTIVE_SAME_CREATOR": max_creator,
        "MAX_CONSECUTIVE_SAME_TOPIC": max_topic,
        "EXPLORATION_SOURCE": DEFAULT_OVERRIDES["EXPLORATION_SOURCE"],
    }
    return labels[selected_name], overrides


def show_process_overview(scenario: dict, result: dict) -> None:
    st.subheader("1. Process overview")
    candidates = scenario.get("candidates", [])
    sources = {}
    for candidate in candidates:
        source = candidate.get("source", "unknown")
        sources[source] = sources.get(source, 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Candidates", len(candidates))
    c2.metric("User", scenario.get("user_id", "—"))
    c3.metric("Top score", f"{result['ranked'][0]['score']:.4f}" if result["ranked"] else "—")
    c4.metric("Diversity moves", len(result["diversity_moves"]))

    steps = [
        ("Load", f"{len(candidates)} posts from selected scenario"),
        ("Score", "Five signals × live weights from the sidebar"),
        ("Sort", "Highest score first"),
        ("Diversity", "Delay repeats of creator / topic"),
        ("Reasons", "Short labels for why each post ranked"),
    ]
    cols = st.columns(len(steps))
    for col, (title, detail) in zip(cols, steps):
        col.markdown(f"**{title}**")
        col.caption(detail)

    st.markdown("**Candidate sources in this batch**")
    source_df = pd.DataFrame(
        [{"source": key, "count": value} for key, value in sorted(sources.items())]
    )
    st.dataframe(source_df, hide_index=True, width="stretch")


def show_ranked_feed(result: dict, top_n: int) -> None:
    st.subheader("2. Ranked feed")
    ranked = result["ranked"][:top_n]
    rows = []
    for index, post in enumerate(ranked, start=1):
        rows.append(
            {
                "#": index,
                "post_id": post["post_id"],
                "score": post["score"],
                "creator": post["creator_id"],
                "topics": ", ".join(post.get("topics") or []),
                "source": post.get("source", ""),
                "followed": post.get("is_followed", False),
                "reasons": ", ".join(post.get("reasons") or []),
                "topic": post["score_breakdown"]["topic"],
                "relationship": post["score_breakdown"]["relationship"],
                "freshness": post["score_breakdown"]["freshness"],
                "engagement": post["score_breakdown"]["engagement"],
                "exploration": post["score_breakdown"]["exploration"],
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def show_activity(scenario: dict, result: dict, overrides: dict) -> None:
    st.subheader("3. Activity — how formulas apply")
    st.caption(
        "Pick a post to see the exact numbers used for each formula. "
        "Change the sidebar bars and this section updates live."
    )

    candidates = scenario.get("candidates", [])
    user_features = scenario.get("user_features", {})
    ranked = result["ranked"]

    if not ranked:
        st.info("No ranked posts to inspect.")
        return

    options = {
        f"#{index}  {post['post_id']}  (score {post['score']:.4f})": post["post_id"]
        for index, post in enumerate(ranked, start=1)
    }
    selected_label = st.selectbox("Inspect post", list(options.keys()))
    selected_id = options[selected_label]
    original = next(c for c in candidates if str(c["post_id"]) == str(selected_id))
    explanation = explain_post(original, user_features, overrides)

    st.markdown("##### Pipeline for this post")
    st.code(
        "candidate → topic / relationship / freshness / engagement / exploration "
        "→ weighted sum − penalty → sort → diversity → reasons",
        language="text",
    )

    left, right = st.columns(2)

    with left:
        st.markdown("**Topic relevance**")
        st.code(explanation["topic"]["formula"], language="text")
        if explanation["topic"]["parts"]:
            parts = " + ".join(
                f"{part['topic']}({part['weight']:.2f})"
                for part in explanation["topic"]["parts"]
            )
            st.write(
                f"`{parts}` = **{explanation['topic']['raw_sum']:.4f}** "
                f"→ clamped **{explanation['topic']['score']:.4f}**"
            )
        else:
            st.write("No topics on this post → score **0.0**")

        st.markdown("**Creator relationship**")
        st.code(explanation["relationship"]["formula"], language="text")
        if explanation["relationship"]["is_followed"]:
            st.write("Followed creator → score **1.0**")
        else:
            st.write(
                f"0.5 × {explanation['relationship']['creator_engagement']:.4f} "
                f"= **{explanation['relationship']['score']:.4f}**"
            )

        st.markdown("**Freshness**")
        st.code(explanation["freshness"]["formula"], language="text")
        st.write(
            f"0.5 ** ({explanation['freshness']['age_hours']:.2f} / "
            f"{explanation['freshness']['half_life']}) "
            f"= **{explanation['freshness']['score']:.4f}**"
        )

    with right:
        st.markdown("**Engagement quality**")
        st.code(explanation["engagement"]["formula"], language="text")
        eng = explanation["engagement"]
        st.write(
            f"({eng['likes']} + {eng['save_weight']}×{eng['saves']} + "
            f"{eng['k']}×{eng['prior']}) / ({eng['impressions']} + {eng['k']}) "
            f"= {eng['numerator']:.2f} / {eng['denominator']} "
            f"= **{eng['score']:.4f}**"
        )

        st.markdown("**Exploration**")
        st.code(explanation["exploration"]["formula"], language="text")
        st.write(
            f"source=`{explanation['exploration']['source']}` → "
            f"score **{explanation['exploration']['score']:.1f}**"
        )

        st.markdown("**Final weighted score**")
        st.code(explanation["final"]["formula"], language="text")
        final = explanation["final"]
        lines = []
        for name, value in final["weighted_parts"].items():
            weight = final["weights"][name]
            signal = value / weight if weight else 0.0
            lines.append(f"{weight:.2f} × {signal:.4f} = {value:.4f}   ({name})")
        st.code("\n".join(lines), language="text")
        st.write(
            f"Sum − penalty({final['penalty']:.4f}) = "
            f"**{final['before_floor']:.4f}** → floor at 0 → "
            f"**{final['score']:.4f}**"
        )

    st.markdown("##### Diversity activity")
    move = next(
        (item for item in result["diversity_moves"] if item["post_id"] == selected_id),
        None,
    )
    if move:
        st.warning(
            f"This post moved from rank **#{move['from']}** to **#{move['to']}** "
            "to avoid too many consecutive posts from the same creator or topic."
        )
    else:
        st.success("This post kept its score order — no diversity delay needed.")

    if result["diversity_moves"]:
        with st.expander("All diversity position changes"):
            st.dataframe(
                pd.DataFrame(result["diversity_moves"]),
                hide_index=True,
                width="stretch",
            )
    else:
        st.caption("No diversity reordering happened for this batch.")

    ranked_post = next(p for p in ranked if str(p["post_id"]) == str(selected_id))
    st.markdown("##### Reasons attached to the response")
    st.write(", ".join(ranked_post.get("reasons") or ["general relevance"]))


def show_compare_before_after(result: dict, top_n: int) -> None:
    st.subheader("4. Sort vs diversity order")
    before = [
        {
            "#": index,
            "post_id": post["post_id"],
            "score": post["score"],
            "creator": post.get("creator_id"),
        }
        for index, post in enumerate(result["sorted"][:top_n], start=1)
    ]
    after = [
        {
            "#": index,
            "post_id": post["post_id"],
            "score": post["score"],
            "creator": post.get("creator_id"),
        }
        for index, post in enumerate(result["diversified"][:top_n], start=1)
    ]
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**After score sort**")
        st.dataframe(pd.DataFrame(before), hide_index=True, width="stretch")
    with col_b:
        st.markdown("**After diversity**")
        st.dataframe(pd.DataFrame(after), hide_index=True, width="stretch")


def main() -> None:
    st.title("Recommendation Engine Lab")
    st.write(
        "Simulate the AI ranking service: load a candidate batch from `data/`, "
        "tune weights with the bars, and watch scoring + diversity step by step."
    )

    scenario_path, overrides = sidebar_controls()
    if scenario_path is None:
        st.stop()

    scenario = load_scenario(scenario_path)
    candidates = scenario.get("candidates", [])
    user_features = scenario.get("user_features", {})

    if not candidates:
        st.error("Selected scenario has no candidates.")
        st.stop()

    top_n = st.slider("Rows to show in tables", 10, min(100, len(candidates)), 20)

    result = run_pipeline(candidates, user_features, overrides)

    show_process_overview(scenario, result)
    st.markdown("---")
    show_ranked_feed(result, top_n)
    st.markdown("---")
    show_activity(scenario, result, overrides)
    st.markdown("---")
    show_compare_before_after(result, top_n)


if __name__ == "__main__":
    main()
