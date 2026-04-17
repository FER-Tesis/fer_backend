from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.enums.emotion_type import Emotion

class AgentCurrentEmotionResponse(BaseModel):
    emotion: Optional[str]
    timestamp: Optional[datetime]

class AgentDayHistoryResponse(BaseModel):
    labels: List[str]
    values: List[Optional[Emotion]]

class AgentWeekHistoryResponse(BaseModel):
    labels: List[str]
    values: List[Optional[Emotion]]

class SupervisorAgentStatus(BaseModel):
    id: str
    name: str
    email: str
    emotion: Optional[Emotion] = None
    timestamp: Optional[datetime] = None

class SupervisorCameraTableItem(BaseModel):
    camera_id: Optional[str]
    camera_name: str
    agent_id: str
    agent_name: str
    status: Optional[str]
    last_connection: Optional[datetime]
    monitoring_active: bool