from typing import Any
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict
from pydantic_core import core_schema
from pydantic.json_schema import JsonSchemaValue


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
        cls,
        core_schema: core_schema.CoreSchema,
        handler
    ) -> JsonSchemaValue:
        return {"type": "string", "example": "64c8af88a9b74e2c1a35c9e1"}

    @classmethod
    def validate(cls, v: Any) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


class SupervisorAgentCreate(BaseModel):
    supervisor_id: PyObjectId = Field(..., example="64c8af88a9b74e2c1a35c9e1")
    agent_id: PyObjectId = Field(..., example="64c8af88a9b74e2c1a35c9e9")


class SupervisorAgentResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    supervisor_id: PyObjectId
    agent_id: PyObjectId

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        json_encoders={ObjectId: str},
    )

class RelationLookup(BaseModel):
    agent_id: str = Field(..., example="691dbadecd777ce88c0ebd66")

class AgentMinimal(BaseModel):
    id: str
    name: str
    email: str