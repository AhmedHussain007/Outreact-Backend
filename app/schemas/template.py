from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class TemplateBase(BaseModel):
    name: str
    subject_line: Optional[str] = ""
    body_content: str
    format_type: Literal["markdown", "html", "plain_text"] = "html"

class TemplateCreate(TemplateBase):
    user_id: Optional[str] = None # Support future multi-tenancy

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject_line: Optional[str] = None
    body_content: Optional[str] = None
    format_type: Optional[Literal["markdown", "html", "plain_text"]] = None
    user_id: Optional[str] = None

class TemplateResponse(TemplateBase):
    id: str
    created_at: datetime
    updated_at: datetime
    user_id: Optional[str] = None

    class Config:
        from_attributes = True
