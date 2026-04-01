from pydantic import BaseModel, Field
from typing import List

class CampaignLaunchRequest(BaseModel):
    campaign_name: str = Field(..., description="The name of the campaign to launch")
    file_id: int = Field(..., description="The dataset file ID to run the campaign on")
    start_date: str = Field(..., description="Start date of the campaign")
    timezone: str = Field(default="UTC", description="Timezone of the leads")
    daily_limit: int = Field(default=50, description="Daily email sending limit")
    templates: dict = Field(default_factory=dict, description="Email templates and times JSON")
    delays: dict = Field(default_factory=dict, description="Follow-up delays JSON")

class CampaignResponse(BaseModel):
    id: int
    name: str
    target_files: str
    status: str
    total_leads: int
    sent: int
    opens: int
    replies: int
    
    class Config:
        from_attributes = True

