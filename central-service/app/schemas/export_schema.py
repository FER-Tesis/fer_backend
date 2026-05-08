from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, model_validator


ExportType = Literal["current", "team", "agent"]
ExportFormat = Literal["csv", "xlsx"]
GroupBy = Literal["day", "week", "month"]
Aggregate = Literal["emotion_count", "emotion_percentage", "dominant_emotion"]


class CurrentExportSnapshotRow(BaseModel):
    name: str
    emotion_label: str
    updated_at: str


class ExportJobCreateRequest(BaseModel):
    type: ExportType
    format: ExportFormat = "csv"

    # current
    snapshot: Optional[List[CurrentExportSnapshotRow]] = None

    # team / agent
    agent_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    group_by: Optional[GroupBy] = None
    aggregates: Optional[List[Aggregate]] = None

    @model_validator(mode="after")
    def validate_by_type(self):
        if self.type == "current":
            if not self.snapshot:
                raise ValueError("For type='current', snapshot is required.")

        elif self.type == "team":
            if not self.start_date or not self.end_date or not self.group_by or not self.aggregates:
                raise ValueError(
                    "For type='team', start_date, end_date, group_by and aggregates are required."
                )

        elif self.type == "agent":
            if (
                not self.agent_id
                or not self.start_date
                or not self.end_date
                or not self.group_by
                or not self.aggregates
            ):
                raise ValueError(
                    "For type='agent', agent_id, start_date, end_date, group_by and aggregates are required."
                )

        return self


class ExportJobCreateResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ExportJobStatusResponse(BaseModel):
    job_id: str
    status: str
    type: str
    format: str
    file_name: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None