from enum import Enum


class EmotionAlertRuleType(str, Enum):
    negative_count = "negative_count"
    continuous_emotion = "continuous_emotion"


class EmotionAlertSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class EmotionAlertStatus(str, Enum):
    pending = "pending"
    acknowledged = "acknowledged"
    resolved = "resolved"


class PolicyStatus(str, Enum):
    active = "active"
    inactive = "inactive"
