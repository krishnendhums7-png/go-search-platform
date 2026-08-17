"""
Authentication models.
"""

from datetime import datetime

from pydantic import BaseModel
from pydantic import EmailStr


class LoginRequest(BaseModel):
    """
    Login request.
    """

    email: EmailStr

    password: str


class TokenResponse(BaseModel):
    """
    JWT response.
    """

    access_token: str

    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    Payload stored inside JWT.
    """

    user_id: str

    email: EmailStr

    role: str

    exp: datetime