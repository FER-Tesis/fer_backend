from fastapi import APIRouter, HTTPException, status

from app.schemas.capture_schema import (
    CaptureStartResponse,
    CaptureStopResponse,
    CaptureSessionActiveResponse,
    CameraMonitoringStatusResponse,
    LastCaptureSessionResponse
)
from app.services import capture_service

router = APIRouter()

@router.post(
    "/{camera_id}/start",
    response_model=CaptureStartResponse
)
async def start_capture(camera_id: str):
    try:
        result = await capture_service.start_capture(camera_id=camera_id)
        return result

    except capture_service.CaptureDomainError as e:
        if str(e) == "camera_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found"
            )

        if str(e) == "camera_inactive":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Camera is inactive"
            )

        if str(e) == "camera_in_maintenance":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Camera is in maintenance"
            )

        if str(e) == "capture_already_active":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="There is already an active capture session for this camera"
            )

        if str(e) == "hub_start_failed":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to start capture in camera hub"
            )

        if str(e) == "hub_unreachable":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Camera hub is unavailable"
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid capture start request"
        )

@router.post(
    "/{camera_id}/stop",
    response_model=CaptureStopResponse
)
async def stop_capture(camera_id: str):
    try:
        result = await capture_service.stop_capture(camera_id=camera_id)
        return result

    except capture_service.CaptureDomainError as e:
        if str(e) == "camera_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found"
            )

        if str(e) == "active_session_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active capture session found for this camera"
            )

        if str(e) == "hub_stop_failed":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to stop capture in camera hub"
            )

        if str(e) == "hub_unreachable":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Camera hub is unavailable"
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid capture stop request"
        )
    
@router.get(
    "/sessions/{capture_session_id}/active",
    response_model=CaptureSessionActiveResponse
)
async def get_capture_session_active(capture_session_id: str):
    try:
        result = await capture_service.get_capture_session_active(capture_session_id)
        return result

    except capture_service.CaptureDomainError as e:
        if str(e) == "capture_session_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Capture session not found"
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid capture session request"
        )
    
@router.get(
    "/{camera_id}/status",
    response_model=CameraMonitoringStatusResponse
)
async def get_camera_status(camera_id: str):
    try:
        return await capture_service.get_camera_monitoring_status(camera_id)

    except capture_service.CaptureDomainError as e:
        if str(e) == "camera_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found"
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request"
        )
    
@router.get(
    "/{camera_id}/last/session",
    response_model=LastCaptureSessionResponse
)
async def get_last_capture_session(camera_id: str):
    try:
        return await capture_service.get_last_capture_session(camera_id)

    except capture_service.CaptureDomainError as e:
        if str(e) == "camera_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found"
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request"
        )