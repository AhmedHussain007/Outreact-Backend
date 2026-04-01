import logging
import httpx
from datetime import datetime, timezone
from app.db.database import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)

# Map from current lead status -> template key to use from campaign.templates
TEMPLATE_MAP = {
    "pending":    "Initial",
    "initial":    "FollowUp1",
    "first_fu":   "FollowUp2",
    "second_fu":  "FollowUp3",
}

# Statuses that are terminal / should never be dispatched again
SKIP_STATUSES = {"replied", "bounced", "completed"}

N8N_WEBHOOK_URL = settings.N8N_WEBHOOK_URL
N8N_FOLLOWUP_WEBHOOK_URL = settings.N8N_FOLLOWUP_WEBHOOK_URL


async def dispatch_due_emails():
    """
    Main dispatcher – called by APScheduler every 30 minutes.

    1. Queries `leads` for rows where next_scheduled_action <= NOW()
       and status NOT IN ('replied', 'bounced', 'completed').
    2. For each lead, checks parent campaign status == 'running'.
    3. Picks the correct template from campaign.templates JSON.
    4. Fires an async POST to the n8n webhook (fire-and-forget).
       Does NOT update lead status – that is handled by the callback.
    """
    logger.info("[Worker] Starting dispatch cycle …")

    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        leads_res = (
            supabase
            .table("leads")
            .select("*, campaigns(status, templates, delays)")
            .lte("next_scheduled_action", now_iso)
            .not_.in_("status", list(SKIP_STATUSES))
            .execute()
        )
    except Exception as e:
        logger.error(f"[Worker] Failed to query leads: {e}")
        return

    due_leads = leads_res.data or []
    if not due_leads:
        logger.info("[Worker] No due leads found.")
        return

    logger.info(f"[Worker] {len(due_leads)} due lead(s) found.")

    async with httpx.AsyncClient(timeout=15.0) as client:
        for lead in due_leads:
            lead_id = lead.get("id")
            campaign_id = lead.get("campaign_id")
            lead_status = lead.get("status", "pending")

            # --- Validate campaign is running ---
            campaign = lead.get("campaigns")
            if not campaign:
                logger.warning(f"[Worker] Lead {lead_id}: No campaign record found, skipping.")
                continue

            campaign_status = (campaign.get("status") or "").lower()
            if campaign_status != "running":
                logger.info(f"[Worker] Lead {lead_id}: Campaign not running (status={campaign_status}), skipping.")
                continue

            # --- pick template / route logic ---
            if lead_status == "pending":
                # Initial Dispatch: Send all templates so n8n can generate follow-ups
                templates = campaign.get("templates") or {}
                payload = {
                    "lead_id": lead_id,
                    "campaign_id": campaign_id,
                    "personalization_data": lead.get("personalization_data") or {},
                    "thread_id": None,
                    "templates": templates,
                }
                target_url = N8N_WEBHOOK_URL
                template_name_log = "All Templates (Init)"
            else:
                # Follow-up Dispatch
                step_map = {
                    "initial": "fu1",
                    "first_fu": "fu2",
                    "second_fu": "fu3",
                }
                step = step_map.get(lead_status)
                if not step:
                    logger.warning(f"[Worker] Lead {lead_id}: Unknown followup status '{lead_status}', skipping.")
                    continue

                followups = lead.get("followups") or {}
                template_obj = followups.get(step)

                if not template_obj:
                    logger.info(f"[Worker] Lead {lead_id}: No customized follow-up found for step '{step}', skipping.")
                    continue

                payload = {
                    "lead_id": lead_id,
                    "campaign_id": campaign_id,
                    "personalization_data": lead.get("personalization_data") or {},
                    "thread_id": lead.get("thread_id"),
                    "template": template_obj,
                    "step": step,
                }
                target_url = N8N_FOLLOWUP_WEBHOOK_URL
                template_name_log = f"Follow-up ({step})"

            # --- Fire and forget ---
            try:
                await client.post(target_url, json=payload)
                logger.info(f"[Worker] Lead {lead_id}: Dispatched to n8n (template='{template_name_log}').")

            except Exception as e:
                logger.error(f"[Worker] Lead {lead_id}: Failed to reach n8n – {e}")
