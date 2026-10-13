import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints, model_validator

from app.models.complaint import Priority

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
ShortName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
Phone = Annotated[str, Field(pattern=r"^\+?[0-9]{10,15}$")]
LowerEmail = Annotated[EmailStr, AfterValidator(lambda value: value.lower())]


def _upper_code(value: str) -> str:
    value = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9_]{2,30}", value):
        raise ValueError("Code must be 2-30 characters: capital letters, digits and underscores only")
    return value


Code = Annotated[str, AfterValidator(_upper_code)]


def check_password_strength(value: str) -> str:
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one number")
    return value


Password = Annotated[str, Field(min_length=8, max_length=72), AfterValidator(check_password_strength)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields (like "role") are rejected


class UpdateModel(StrictModel):
    """Base for PATCH bodies: at least one field must be sent."""

    @model_validator(mode="after")
    def at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("Send at least one field to update")
        return self


# ---------- departments and categories ----------

class DepartmentCreate(StrictModel):
    name: ShortName
    code: Code
    description: Description = ""


class DepartmentUpdate(UpdateModel):
    name: ShortName | None = None
    code: Code | None = None
    description: Description | None = None
    is_active: bool | None = Field(default=None, alias="isActive")


class CategoryCreate(StrictModel):
    name: ShortName
    code: Code
    description: Description = ""
    department_id: str = Field(alias="departmentId")


class CategoryUpdate(UpdateModel):
    name: ShortName | None = None
    code: Code | None = None
    description: Description | None = None
    department_id: str | None = Field(default=None, alias="departmentId")
    is_active: bool | None = Field(default=None, alias="isActive")


# ---------- workers ----------

class WorkerCreate(StrictModel):
    name: Name
    email: LowerEmail
    password: Password
    phone: Phone | None = None
    department_id: str = Field(alias="departmentId")


class WorkerUpdate(UpdateModel):
    name: Name | None = None
    phone: Phone | None = None
    department_id: str | None = Field(default=None, alias="departmentId")
    is_active: bool | None = Field(default=None, alias="isActive")
    password: Password | None = None  # lets an admin reset a forgotten password


# ---------- complaints (admin) ----------

class ComplaintUpdate(UpdateModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=150)] | None = None
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)] | None = None
    priority: Priority | None = None
    category_id: str | None = Field(default=None, alias="categoryId")
    # Send null to un-assign. Leave it out to keep the current worker.
    assigned_worker_id: str | None = Field(default=None, alias="assignedWorkerId")


# ---------- own profile ----------

class ProfileUpdate(UpdateModel):
    name: Name | None = None
    phone: Phone | None = None  # send null to remove the phone number


class ChangePasswordRequest(StrictModel):
    current_password: str = Field(alias="currentPassword", min_length=1, max_length=128)
    new_password: Password = Field(alias="newPassword")
