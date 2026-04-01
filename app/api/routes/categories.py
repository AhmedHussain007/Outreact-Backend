from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from app.schemas import category
from app.api.dependencies import get_supabase

router = APIRouter(prefix="/api/categories", tags=["Categories"])

@router.get("", response_model=list[category.CategoryResponse])
def get_categories(supabase: Client = Depends(get_supabase)):
    try:
        response = supabase.table("categories").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=category.CategoryResponse)
def create_category(payload: category.CategoryCreate, supabase: Client = Depends(get_supabase)):
    try:
        response = supabase.table("categories").insert({"name": payload.name}).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create category")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
