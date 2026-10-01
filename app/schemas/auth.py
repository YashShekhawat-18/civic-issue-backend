import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

# Emails are always stored in lowercase so "Asha@x.com" and "asha@x.com" are the same account
NormalizedEmail = Annotated[EmailStr, AfterValidator(lambda value: value.lower())]


class RegisterRequest(BaseModel):
    # extra="forbid": if someone sends {"role": "ADMIN"}, the request is rejected
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
    email: NormalizedEmail
    password: str = Field(min_length=8, max_length=72)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{10,15}$")

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must contain at least one letter and one number")
        if len(value.encode("utf-8")) > 72:  # bcrypt only reads the first 72 bytes
            raise ValueError("Password is too long")
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalizedEmail
    password: str = Field(min_length=1, max_length=128)