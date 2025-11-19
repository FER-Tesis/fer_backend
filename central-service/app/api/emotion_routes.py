from typing import List

from fastapi import APIRouter, HTTPException, status

from app.schemas.emotion_schema import (
    EmotionEventCreate,
    EmotionEventResponse,
    CurrentEmotionStatusResponse,
)
from app.services import emotion_service

router = APIRouter()


@router.post(
    "/emotion-events",
    response_model=EmotionEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_emotion_event(payload: EmotionEventCreate):
    try:
        created = await emotion_service.register_emotion_event(payload)
        return created

    except emotion_service.EmotionDomainError as e:
        if str(e) == "invalid_emotion":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid emotion",
            )
        if str(e) == "camera_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found",
            )
        if str(e) == "agent_not_assigned":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Camera has no assigned agent",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid emotion event data",
        )


@router.get(
    "/emotion-events",
    response_model=List[EmotionEventResponse],
    status_code=status.HTTP_200_OK,
)
async def list_emotion_events():
    return await emotion_service.list_emotion_events()


@router.get(
    "/current-status",
    response_model=List[CurrentEmotionStatusResponse],
    status_code=status.HTTP_200_OK,
)
async def list_current_statuses():
    return await emotion_service.list_current_statuses()


@router.get(
    "/current-status/{camera_id}",
    response_model=CurrentEmotionStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_current_status(camera_id: str):
    status_doc = await emotion_service.get_current_status(camera_id)

    if not status_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Status not found for this camera",
        )

    return status_doc
