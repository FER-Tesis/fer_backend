from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class CaptureStartResponse(BaseModel):
    capture_session_id: str
    camera_id: str
    active: bool

class CaptureStopResponse(BaseModel):
    message: str
    capture_session_id: str
    camera_id: str
    active: bool

class CaptureSessionResponse(BaseModel):
    id: str = Field(alias="_id")
    camera_id: str
    active: bool
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

class CaptureSessionActiveResponse(BaseModel):
    capture_session_id: str
    active: bool

class CameraMonitoringStatusResponse(BaseModel):
    camera_id: str
    active: bool

class LastCaptureSessionResponse(BaseModel):
    camera_id: str
    capture_session_id: Optional[str]
    active: bool
    started_at: Optional[datetime]
    ended_at: Optional[datetime]