import pandas as pd
import io
from fastapi import UploadFile, HTTPException

async def process_upload_to_records(file: UploadFile) -> list[dict]:
    contents = await file.read()
    
    if file.filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(contents))
    elif file.filename.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload .csv or .xlsx")
        
    df.fillna("", inplace=True)
    return df.to_dict(orient="records")
