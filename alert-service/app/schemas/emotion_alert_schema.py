from typing import Any, Optional
from datetime import datetime
from bson import ObjectId

from pydantic import BaseModel, Field, ConfigDict
from pydantic_core import core_schema
from pydantic.json_schema import JsonSchemaValue

from app.enums.emotion_alert_enum import (
    EmotionAlertRuleType,
    EmotionAlertSeverity,
    EmotionAlertStatus,
    PolicyStatus,
)


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler
    ) -> JsonSchemaValue:
        return {"type": "string", "example": "64c8af88a9b74e2c1a35c9e1"}

    @classmethod
    def validate(cls, v: Any) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


# ============== POLICY SCHEMAS ==============

class EmotionAlertPolicyCreate(BaseModel):
    supervisor_id: PyObjectId = Field(..., example="64c8af88a9b74e2c1a35c9e1")
    name: str = Field(..., example="Monitoreo estándar")


class EmotionAlertPolicyUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[PolicyStatus] = None


class EmotionAlertPolicyResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    supervisor_id: PyObjectId
    name: str
    status: PolicyStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


# ============== RULE SCHEMAS ==============

class EmotionAlertRuleCreate(BaseModel):
    policy_id: PyObjectId = Field(..., example="64c8af88a9b74e2c1a35c9e1")
    type: EmotionAlertRuleType = Field(..., example="negative_count")
    emotions: list[str] = Field(..., example=["sad", "anger", "fear", "disgust"])
    threshold: int = Field(..., example=5)
    window_seconds: int = Field(..., example=600)
    cooldown_seconds: int = Field(..., example=300)
    severity: EmotionAlertSeverity = Field(..., example="medium")


class EmotionAlertRuleUpdate(BaseModel):
    type: Optional[EmotionAlertRuleType] = None
    emotions: Optional[list[str]] = None
    threshold: Optional[int] = None
    window_seconds: Optional[int] = None
    cooldown_seconds: Optional[int] = None
    severity: Optional[EmotionAlertSeverity] = None
    status: Optional[PolicyStatus] = None


class EmotionAlertRuleResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    policy_id: PyObjectId
    type: EmotionAlertRuleType
    emotions: list[str]
    threshold: int
    window_seconds: int
    cooldown_seconds: int
    severity: EmotionAlertSeverity
    status: PolicyStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


# ============== EVALUATION STATE SCHEMAS ==============

class EmotionWindow(BaseModel):
    emotion: str
    timestamp: datetime


class EmotionEvaluationStateResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    agent_id: PyObjectId
    rule_id: PyObjectId
    policy_id: PyObjectId
    current_count: int
    emotions_window: list[EmotionWindow]
    continuous_emotion_start: Optional[datetime] = None
    last_alert_at: Optional[datetime] = None
    cooldown_end_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


# ============== ALERT SCHEMAS ==============

class EmotionAlertCreate(BaseModel):
    agent_id: PyObjectId
    supervisor_id: PyObjectId
    policy_id: PyObjectId
    rule_id: PyObjectId
    rule_type: EmotionAlertRuleType
    severity: EmotionAlertSeverity


class EmotionAlertUpdate(BaseModel):
    status: Optional[EmotionAlertStatus] = None


class EmotionAlertResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    agent_id: PyObjectId
    supervisor_id: PyObjectId
    policy_id: PyObjectId
    rule_id: PyObjectId
    rule_type: EmotionAlertRuleType
    severity: EmotionAlertSeverity
    status: EmotionAlertStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
