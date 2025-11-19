from fastapi import APIRouter, HTTPException, status
from app.schemas.auth_schema import RegisterRequest, LoginRequest, TokenResponse, TokenRequest, TokenVerificationResponse
from app.services.auth_service import register_user, authenticate_user, verify_token, AuthError

router = APIRouter()

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest):
    try:
        return await register_user(data.dict())
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    try:
        return await authenticate_user(credentials.email, credentials.password)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/verify-token", response_model=TokenVerificationResponse)
async def verify_token_endpoint(body: TokenRequest):
    try:
        return verify_token(body.token)
    except Exception:
        return {"valid": False, "error": "Invalid token"}
