# recommendation/config.py

# Recommendation score weights
TOPIC_WEIGHT = 0.30 #Topic relevance
RELATIONSHIP_WEIGHT = 0.25
FRESHNESS_WEIGHT = 0.20
ENGAGEMENT_WEIGHT = 0.15
EXPLORATION_WEIGHT = 0.10

# Freshness settings (hours)
DEFAULT_FRESHNESS_HALF_LIFE_HOURS = 24
FOLLOWED_FRESHNESS_HALF_LIFE_HOURS = 72

# Engagement smoothing assumptions
ENGAGEMENT_SMOOTHING_K = 20
ENGAGEMENT_PRIOR = 0.05
SAVE_WEIGHT = 2

# Diversity settings
MAX_CONSECUTIVE_SAME_CREATOR = 2
MAX_CONSECUTIVE_SAME_TOPIC = 2

# Exploration source name
EXPLORATION_SOURCE = "exploration"

# API/service settings
MODEL_NAME = "rules_v1"
MAX_CANDIDATES = 200
MIN_CANDIDATES = 1

# Penalty size is not finalized in the implementation plan.
# For now, scoring.py accepts an optional penalty value per candidate.
DEFAULT_PENALTY = 0.0