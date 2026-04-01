from fastapi import APIRouter, Depends, Form, File as FastAPIFile, UploadFile, HTTPException
from supabase import Client
from app.schemas import file as schemas
from app.api.dependencies import get_supabase
from app.services.file_processor import process_upload_to_records
import logging

router = APIRouter(prefix="/api", tags=["Files"])

@router.get("/categories/{category_id}/files", response_model=list[schemas.FileResponse])
def get_files_by_category(category_id: int, supabase: Client = Depends(get_supabase)):
    try:
        response = supabase.table("files").select("*").eq("category_id", category_id).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload_file", response_model=schemas.FileResponse)
async def upload_file(
    category_id: int = Form(...),
    file: UploadFile = FastAPIFile(...),
    supabase: Client = Depends(get_supabase)
):
    try:
        # Check if category exists
        cat_response = supabase.table("categories").select("id").eq("id", category_id).execute()
        if not cat_response.data:
            raise HTTPException(status_code=404, detail="Category not found")
            
        records = await process_upload_to_records(file)
        
        # Insert File
        file_response = supabase.table("files").insert({
            "name": file.filename, 
            "category_id": category_id
        }).execute()
        
        if not file_response.data:
            raise HTTPException(status_code=500, detail="Failed to create file record")
            
        db_file = file_response.data[0]
        
        # Insert Lead Rows
        lead_rows = [
            {"file_id": db_file["id"], "row_data": record, "lead_score": 0}
            for record in records
        ]
        
        # Chunk the insert if there are too many records (Supabase limits insert size)
        chunk_size = 1000
        for i in range(0, len(lead_rows), chunk_size):
            chunk = lead_rows[i:i + chunk_size]
            supabase.table("lead_rows").insert(chunk).execute()
            
        return db_file
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
