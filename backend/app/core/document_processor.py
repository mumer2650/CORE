import asyncio
import os
from typing import Dict, Any
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.vector_store import get_vector_store

# In-memory store for task status tracking.
# Note: In production, this should be moved to Redis or PostgreSQL to handle multiple server workers.
TASK_STATUS: Dict[str, Dict[str, Any]] = {}

async def process_document_task(task_id: str, file_path: str, user_id: str, filename: str):
    """
    Background task to process the uploaded document.
    """
    TASK_STATUS[task_id] = {"status": "processing", "filename": filename, "progress": "10%", "message": "Loading document..."}
    try:
        print(f"Starting to process file: {filename} for user: {user_id}")
        
        # 1. Load Document
        if filename.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
            documents = loader.load()
        elif filename.endswith(".txt") or filename.endswith(".md"):
            # Ensure text loaders use utf-8 to prevent encoding errors
            loader = TextLoader(file_path, encoding="utf-8")
            documents = loader.load()
        else:
            raise ValueError("Unsupported file format.")
            
        TASK_STATUS[task_id] = {"status": "processing", "filename": filename, "progress": "40%", "message": "Splitting text..."}
        
        # 2. Add Metadata for Multi-tenancy
        # Every chunk gets tagged with the user_id so users can only query their own docs!
        for doc in documents:
            doc.metadata["user_id"] = user_id
            doc.metadata["source_filename"] = filename
            
        # 3. Split Text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_documents(documents)
        
        TASK_STATUS[task_id] = {"status": "processing", "filename": filename, "progress": "70%", "message": f"Embedding and storing {len(chunks)} chunks..."}
        
        # 4. Store in Vector DB
        vector_store = get_vector_store()
        vector_store.add_documents(chunks)
        
        print(f"Successfully processed and stored file: {filename}")
        TASK_STATUS[task_id] = {"status": "completed", "filename": filename, "progress": "100%", "message": "Document successfully ingested and vectorized."}
        
    except Exception as e:
        print(f"Error processing file {filename}: {str(e)}")
        TASK_STATUS[task_id] = {"status": "failed", "filename": filename, "progress": "0%", "message": str(e)}
    finally:
        # Crucial for deployment: Always clean up the temporary file from the OS temp directory
        if os.path.exists(file_path):
            os.remove(file_path)
