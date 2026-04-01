from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from datetime import datetime, timedelta
import pytz
from app.schemas.campaign import CampaignLaunchRequest, CampaignResponse
from app.api.dependencies import get_supabase
import os

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])

# Using IANA Timezones directly from the frontend payload.

def get_email_from_dict(d):
    for k, v in d.items():
        if isinstance(k, str) and k.strip().lower() == 'email':
            return str(v).strip()
    return ""

@router.get("", response_model=list[CampaignResponse])
def get_campaigns(supabase: Client = Depends(get_supabase)):
    try:
        response = supabase.table("campaigns").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/launch", response_model=CampaignResponse)
async def launch_campaign(payload: CampaignLaunchRequest, supabase: Client = Depends(get_supabase)):
    if not payload.file_id:
        raise HTTPException(status_code=400, detail="No file selected for campaign")

    try:
        # Fetch file
        file_res = supabase.table("files").select("*").eq("id", payload.file_id).execute()
        if not file_res.data:
            raise HTTPException(status_code=404, detail="Selected file not found")
        
        file = file_res.data[0]

        # Fetch lead rows for formatting
        rows_res = supabase.table("lead_rows").select("row_data").eq("file_id", payload.file_id).execute()
        leads_list = [row.get("row_data") for row in rows_res.data if row.get("row_data")]
        
        total_leads = len(leads_list)

        # Save to database
        campaign_data = {
            "name": payload.campaign_name,
            "target_files": file["name"],
            "status": "RUNNING",
            "total_leads": total_leads,
            "sent": 0,
            "opens": 0,
            "replies": 0,
            "start_date": payload.start_date,
            "timezone": payload.timezone,
            "daily_limit": payload.daily_limit,
            "templates": payload.templates,
            "delays": payload.delays
        }
        
        camp_res = supabase.table("campaigns").insert(campaign_data).execute()
        if not camp_res.data:
            raise HTTPException(status_code=500, detail="Failed to create campaign")
            
        new_campaign = camp_res.data[0]

        # Drip-Feed Calculation Logic
        target_tz_str = payload.timezone or "UTC"
        try:
            tz = pytz.timezone(target_tz_str)
        except pytz.UnknownTimeZoneError:
            tz = pytz.timezone("UTC")
        
        initial_time_str = payload.templates.get("Initial", {}).get("time", "09:00 AM")
        datetime_str = f"{payload.start_date} {initial_time_str}"
        try:
            base_dt = datetime.strptime(datetime_str, "%Y-%m-%d %I:%M %p")
        except ValueError:
            # Fallback if time format is unexpected
            base_dt = datetime.strptime(f"{payload.start_date} 09:00 AM", "%Y-%m-%d %I:%M %p")
            
        base_dt_localized = tz.localize(base_dt)

        # Build bulk insert array
        leads_payload = []
        for index, lead_dict in enumerate(leads_list):
            days_to_add = index // (payload.daily_limit if payload.daily_limit > 0 else 1)
            scheduled_dt = base_dt_localized + timedelta(days=days_to_add)
            utc_scheduled_dt = scheduled_dt.astimezone(pytz.utc).isoformat()
            
            leads_payload.append({
                "campaign_id": new_campaign["id"],
                "email": get_email_from_dict(lead_dict),
                "personalization_data": lead_dict,
                "status": "pending",
                "next_scheduled_action": utc_scheduled_dt
            })

        # Bulk Insert Execution
        if leads_payload:
            chunk_size = 1000
            for i in range(0, len(leads_payload), chunk_size):
                chunk = leads_payload[i:i + chunk_size]
                supabase.table("leads").insert(chunk).execute()

        return new_campaign
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
