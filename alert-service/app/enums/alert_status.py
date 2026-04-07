from enum import Enum

class AlertStatus(str, Enum):
    active = "active"
    resolved = "resolved"