from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    notification_type: str
    payload: dict
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
