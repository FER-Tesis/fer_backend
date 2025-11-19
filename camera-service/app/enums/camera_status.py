from enum import Enum

class CameraStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    maintenance = "maintenance"
