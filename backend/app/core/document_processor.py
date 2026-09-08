import asyncio
import os
from typing import Dict, Any

# In-memory store for task status tracking.
# Note: In production, this should be moved to Redis or PostgreSQL to handle multiple server workers.
TASK_STATUS: Dict[str, Dict[str, Any]] = {}

async def process_document_task(task_id: str, file_path: str, user_id: str, filename: str):
    """
    Background task to process the uploaded document.
    Extracted from the API routing layer for better separation of concerns.
    """
    TASK_STATUS[task_id] = {"status": "processing", "filename": filename, "progress": "0%", "message": "Extracting text..."}
    try:
        print(f"Starting to process file: {filename} for user: {user_id}")
        
        # Simulate processing time for now
        await asyncio.sleep(2)
        
        print(f"Successfully processed file: {filename}")
        TASK_STATUS[task_id] = {"status": "completed", "filename": filename, "progress": "100%", "message": "Document successfully ingested."}
        
    except Exception as e:
        print(f"Error processing file {filename}: {str(e)}")
        TASK_STATUS[task_id] = {"status": "failed", "filename": filename, "progress": "0%", "message": str(e)}
    finally:
        # Crucial for deployment: Always clean up the temporary file from the OS temp directory
        if os.path.exists(file_path):
            os.remove(file_path)
