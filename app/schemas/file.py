from pydantic import BaseModel
import datetime

class FileBase(BaseModel):
    name: str
    category_id: int

class FileCreate(FileBase):
    pass

class FileResponse(FileBase):
    id: int
    upload_date: datetime.datetime
    class Config:
        from_attributes = True
