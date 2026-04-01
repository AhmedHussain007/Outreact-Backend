from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from app.schemas import row as schemas
from app.api.dependencies import get_supabase
import logging

router = APIRouter(prefix="/api", tags=["Rows"])

@router.get("/files/{file_id}/rows", response_model=list[schemas.LeadRowResponse])
def get_rows_by_file(file_id: int, supabase: Client = Depends(get_supabase)):
    try:
        response = supabase.table("lead_rows").select("*").eq("file_id", file_id).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/rows/{row_id}")
def update_row_data(row_id: int, payload: schemas.RowUpdatePayload, supabase: Client = Depends(get_supabase)):
    try:
        # Fetch the row
        row_response = supabase.table("lead_rows").select("row_data").eq("id", row_id).execute()
        if not row_response.data:
            raise HTTPException(status_code=404, detail="Row not found")
            
        row_data = row_response.data[0]["row_data"] or {}
        row_data[payload.key] = payload.value
        
        # Update the row
        update_response = supabase.table("lead_rows").update({"row_data": row_data}).eq("id", row_id).execute()
        
        if not update_response.data:
            raise HTTPException(status_code=500, detail="Failed to update row")
            
        return {"status": "success", "updated_row_id": row_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transfer_rows")
def transfer_rows(payload: schemas.TransferRowsPayload, supabase: Client = Depends(get_supabase)):
    try:
        # Verify target file
        file_res = supabase.table("files").select("id").eq("id", payload.target_file_id).execute()
        if not file_res.data:
            raise HTTPException(status_code=404, detail="Target file not found")
            
        # Get rows to transfer
        rows_res = supabase.table("lead_rows").select("*").in_("id", payload.row_ids).execute()
        rows = rows_res.data
        
        processed_count = 0
        for lead_record in rows:
            update_payload = {"file_id": payload.target_file_id}
            
            if payload.header_mapping_dict:
                old_data = lead_record.get("row_data", {})
                new_data = {}
                for old_key, val in old_data.items():
                    new_key = payload.header_mapping_dict.get(old_key, old_key)
                    new_data[new_key] = val
                update_payload["row_data"] = new_data
                
            supabase.table("lead_rows").update(update_payload).eq("id", lead_record["id"]).execute()
            processed_count += 1
            
        return {"status": "success", "transferred_count": processed_count}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error transferring rows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_rows")
def delete_rows(payload: schemas.DeleteRowsPayload, supabase: Client = Depends(get_supabase)):
    try:
        # Delete using in_
        res = supabase.table("lead_rows").delete().in_("id", payload.row_ids).execute()
        return {"status": "success", "deleted_count": len(res.data) if res.data else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
