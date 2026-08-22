from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserType


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    user_type: UserType = UserType.STUDENT


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    user_type: UserType | None = None


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    user_type: UserType
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
