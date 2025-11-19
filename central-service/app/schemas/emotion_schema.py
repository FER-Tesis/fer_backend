from typing import Any, Optional
from datetime import datetime
from bson import ObjectId

from pydantic import BaseModel, Field, ConfigDict
from pydantic_core import core_schema
from pydantic.json_schema import JsonSchemaValue

from app.enums.emotion_type import Emotion


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


class EmotionEventCreate(BaseModel):
    camera_id: str = Field(..., example="64c8af88a9b74e2c1a35c9e1")
    emotion: str = Field(..., example="neutral")
    timestamp: datetime = Field(..., example="2025-02-10T18:01:22Z")


class EmotionEventResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    camera_id: str
    agent_id: str
    emotion: Emotion
    timestamp: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class CurrentEmotionStatusResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    camera_id: str
    agent_id: str
    emotion: Emotion
    timestamp: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
