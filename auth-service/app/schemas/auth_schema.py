from pydantic import BaseModel, EmailStr, Field
from typing import Union

class RegisterRequest(BaseModel):
    name: str = Field(..., example="Carlos Ruiz")
    email: EmailStr = Field(..., example="carlos@empresa.com")
    password: str = Field(..., min_length=6, example="StrongPass123")
    role: str = Field(default="supervisor")
    is_active: bool = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenRequest(BaseModel):
    token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")

class TokenVerificationResponse(BaseModel):
    valid: bool
    user_id: str | None = None
    role: str | None = None
    exp: Union[int, str, None] = None
    error: str | None = None
