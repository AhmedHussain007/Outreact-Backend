from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from typing import List
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse
from app.api.dependencies import get_supabase

router = APIRouter(prefix="/api/templates", tags=["Templates"])

@router.get("", response_model=List[TemplateResponse])
def get_all_templates(supabase: Client = Depends(get_supabase)):
    try:
        response = supabase.table("email_templates").select("*").order("updated_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=TemplateResponse)
def create_template(payload: TemplateCreate, supabase: Client = Depends(get_supabase)):
    try:
        data = payload.model_dump()
        res = supabase.table("email_templates").insert(data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create template")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(template_id: str, payload: TemplateUpdate, supabase: Client = Depends(get_supabase)):
    try:
        data = payload.model_dump(exclude_unset=True)
        # Handle set explicit updated_at if needed, but supabase should handle it via triggers or we can do it here.
        import datetime
        data['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        res = supabase.table("email_templates").update(data).eq("id", template_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Template not found or couldn't update")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{template_id}")
def delete_template(template_id: str, supabase: Client = Depends(get_supabase)):
    try:
        res = supabase.table("email_templates").delete().eq("id", template_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"detail": "Template deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        if "Foreign key violation" in str(e):
            raise HTTPException(status_code=400, detail="Cannot delete template in use")
        raise HTTPException(status_code=500, detail=str(e))
