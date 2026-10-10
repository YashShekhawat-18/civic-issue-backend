from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models.complaint import ComplaintStatus


class StatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields are rejected, not ignored

    status: ComplaintStatus
    # Optional message for the citizen, e.g. "Pothole filled with asphalt". Sent in the notification.
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
