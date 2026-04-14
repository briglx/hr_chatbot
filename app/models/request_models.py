from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    text: str = Field(..., min_length=1, description="The user's message text")
    employee_name: str = Field(None, description="The employee's name (optional)")
