import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db.database import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

# --- State Machine: current_status -> (next_status, delay_key) ---
# delay_key is the key inside campaign.delays JSON to look up days to wait
STATE_TRANSITIONS = {
    "pending":   ("initial",    "DaysToWaitBeforeFU1"),
    "initial":   ("first_fu",   "DaysToWaitBeforeFU2"),
    "first_fu":  ("second_fu",  "DaysToWaitBeforeFU3"),
    "second_fu": ("completed",  None),              # No further follow-up
}


class N8NCallbackPayload(BaseModel):
    lead_id: str  # UUID string from Supabase
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    status_update: str  # "success" or "fail"
    emails: Optional[dict] = None


@router.post("/n8n/callback")
async def n8n_callback(payload: N8NCallbackPayload):
    """
    Receives the result from n8n after an email is actually sent.

    - Looks up the lead's current status.
    - Fetches the parent campaign's delays JSON.
    - Applies the state machine to compute next_status + next_scheduled_action.
    - Persists: status, next_scheduled_action, message_id, thread_id.
    """
    lead_id = payload.lead_id

    # ------------------------------------------------------------------
    # 1. Fetch the lead + its parent campaign's delays
    # ------------------------------------------------------------------
    try:
        lead_res = (
            supabase
            .table("leads")
            .select("id, status, campaign_id, campaigns(delays)")
            .eq("id", lead_id)
            .single()
            .execute()
        )
    except Exception as e:
        logger.error(f"[Webhook] DB error fetching lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error while fetching lead")

    lead = lead_res.data
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    current_status = lead.get("status", "pending")
    campaign_delays: dict = (lead.get("campaigns") or {}).get("delays") or {}

    logger.info(f"[Webhook] Lead {lead_id}: current_status='{current_status}', status_update='{payload.status_update}'")

    # ------------------------------------------------------------------
    # 2. If email failed, mark as 'error' and stop; don't advance state
    # ------------------------------------------------------------------
    if payload.status_update.lower() != "success":
        try:
            supabase.table("leads").update({
                "status": "bounced",
                "message_id": payload.message_id,
                "thread_id": payload.thread_id,
            }).eq("id", lead_id).execute()
        except Exception as e:
            logger.error(f"[Webhook] Failed to mark lead {lead_id} as bounced: {e}")
        return {"message": "Lead marked as bounced", "lead_id": lead_id}

    # ------------------------------------------------------------------
    # 3. State transition
    # ------------------------------------------------------------------
    transition = STATE_TRANSITIONS.get(current_status)
    if not transition:
        logger.warning(f"[Webhook] Lead {lead_id}: No transition defined for status '{current_status}'.")
        raise HTTPException(status_code=400, detail=f"No state transition for status '{current_status}'")

    next_status, delay_key = transition

    # Calculate next_scheduled_action
    if delay_key and delay_key in campaign_delays:
        days_to_add = int(campaign_delays[delay_key])
        next_action_dt = datetime.now(timezone.utc) + timedelta(days=days_to_add)
        next_action_iso = next_action_dt.isoformat()
    else:
        # sequence has ended or missing delay config -> completed
        next_status = "completed"
        next_action_iso = None

    # ------------------------------------------------------------------
    # 4. Persist the update
    # ------------------------------------------------------------------
    update_payload = {
        "status": next_status,
        "next_scheduled_action": next_action_iso,
    }
    if payload.message_id is not None:
        update_payload["message_id"] = payload.message_id
    if payload.thread_id is not None:
        update_payload["thread_id"] = payload.thread_id
    
    # Store generated follow-ups if they were provided
    if payload.emails is not None:
        try:
            emails_list = payload.emails.get("output", {}).get("emails", [])
            followups_map = {}
            for email in emails_list:
                key = email.get("template_key")
                if key == "FollowUp1":
                    followups_map["fu1"] = email
                elif key == "FollowUp2":
                    followups_map["fu2"] = email
                elif key == "FollowUp3":
                    followups_map["fu3"] = email
            
            if followups_map:
                update_payload["followups"] = followups_map
        except Exception as e:
            logger.error(f"[Webhook] Failed to parse emails for lead {lead_id}: {e}")

    try:
        update_res = (
            supabase
            .table("leads")
            .update(update_payload)
            .eq("id", lead_id)
            .execute()
        )
        if not update_res.data:
            raise HTTPException(status_code=500, detail="Update returned no data")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Webhook] Failed to update lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error while updating lead")

    logger.info(
        f"[Webhook] Lead {lead_id}: {current_status} -> {next_status}, "
        f"next_action={next_action_iso}"
    )

    return {
        "message": "Lead updated successfully",
        "lead_id": lead_id,
        "previous_status": current_status,
        "new_status": next_status,
        "next_scheduled_action": next_action_iso,
    }
