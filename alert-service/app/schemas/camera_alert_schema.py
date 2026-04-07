from typing import Any
from datetime import datetime
from bson import ObjectId

from pydantic import BaseModel, Field, ConfigDict
from pydantic_core import core_schema
from pydantic.json_schema import JsonSchemaValue

from app.enums.alert_status import AlertStatus


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


class CameraAlertCreate(BaseModel):
    camera_id: str = Field(..., example="64c8af88a9b74e2c1a35c9e1")
    description: str = Field(
        ...,
        example="La cámara fue reportada en mantenimiento.",
    )


class CameraAlertResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    camera_id: str
    agent_id: str
    description: str
    status: AlertStatus
    created_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )