from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException
import uuid
import shutil
import tempfile
import os
from app.core.security import get_current_user_id
from app.core.document_processor import process_document_task, TASK_STATUS

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])

@router.post("/")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Endpoint to upload a document for asynchronous processing.
    """
    if not file.filename.endswith(('.pdf', '.txt', '.md')):
        raise HTTPException(status_code=400, detail="Only PDF, TXT, and Markdown files are supported.")
    
    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    
    # We use tempfile.mkstemp() instead of a hardcoded local directory.
    # In cloud deployments (AWS Lambda, Docker, Heroku), local folders might be read-only.
    # The OS temporary directory (/tmp) is guaranteed to be writable and is standard for ephemeral processing.
    fd, temp_file_path = tempfile.mkstemp(suffix=file_extension)
    
    try:
        with os.fdopen(fd, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        # Ensure we delete the temp file if the write fails
        os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")
    
    # Initialize the task status before starting the background task
    TASK_STATUS[task_id] = {"status": "pending", "filename": file.filename, "progress": "0%", "message": "Task queued."}
    
    # Dispatch the background task
    background_tasks.add_task(process_document_task, task_id, temp_file_path, user_id, file.filename)
    
    return {
        "status": "accepted",
        "task_id": task_id,
        "message": "Document is being processed in the background."
    }

@router.get("/{task_id}")
async def get_task_status(task_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Endpoint for the frontend to poll and check the processing status of a document.
    """
    status_info = TASK_STATUS.get(task_id)
    if not status_info:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return {
        "task_id": task_id,
        **status_info
    }
