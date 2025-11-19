from typing import Optional, Any
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from pydantic_core import core_schema
from pydantic.json_schema import JsonSchemaValue
from app.enums.camera_status import CameraStatus

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.no_info_after_validator_function(
            cls.validate, core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema()
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: core_schema.CoreSchema, handler) -> JsonSchemaValue:
        return {"type": "string", "example": "64c8af88a9b74e2c1a35c9e1"}

    @classmethod
    def validate(cls, v: Any) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

class CameraCreate(BaseModel):
    name: str = Field(..., example="Cámara Piso 2")
    location: str = Field(..., example="Piso 2 - Sector B")
    ip_address: str = Field(..., example="192.168.0.101")
    status: str = Field(default="active")
    assigned_user_id: Optional[str] = Field(None, example="64c8af88a9b74e2c1a35c9e1")
    last_checked: Optional[datetime] = None

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    status: Optional[str] = None
    assigned_user_id: Optional[str] = None
    last_checked: Optional[datetime] = None

class CameraResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    location: str
    ip_address: str
    status: CameraStatus
    assigned_user_id: str
    last_checked: Optional[datetime]

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
