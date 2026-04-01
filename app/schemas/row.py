from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class LeadRowBase(BaseModel):
    file_id: int
    row_data: Dict[str, Any]
    lead_score: Optional[int] = 0

class LeadRowResponse(LeadRowBase):
    id: int
    class Config:
        from_attributes = True

class RowUpdatePayload(BaseModel):
    key: str
    value: Any

class TransferRowsPayload(BaseModel):
    row_ids: List[int]
    target_file_id: int
    header_mapping_dict: Optional[Dict[str, str]] = None

class DeleteRowsPayload(BaseModel):
    row_ids: List[int]
