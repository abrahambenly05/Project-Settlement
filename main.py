from fastapi import FastAPI, UploadFile, File, HTTPException

from config import ALLOWED_CONTENT_TYPES
from pipeline import run_keypoint_extraction
from schemas import ExtractResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware (
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
    
@app.post("/keypoints", response_model=ExtractResponse)
async def find_keypoints(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Hanya file PDF yang didukung")
    
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Content-type tidak didukung: {file.content_type}")
    
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="File Kosong")
    
    return await run_keypoint_extraction(file.filename, contents)