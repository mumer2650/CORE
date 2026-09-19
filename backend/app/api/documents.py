from fastapi import APIRouter, Depends, HTTPException
import os
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.security import get_current_user_id
from app.core.checkpointer import pool

# Try to initialize Supabase client
url: str = os.getenv("SUPABASE_URL", "")
key: str = os.getenv("SUPABASE_KEY", "")

try:
    from supabase import create_client, Client
    if url and key:
        supabase: Client = create_client(url, key)
    else:
        supabase = None
except ImportError:
    supabase = None

router = APIRouter(prefix="/api/documents", tags=["Documents"])

class DocumentResponse(BaseModel):
    id: int
    filename: str
    storage_url: Optional[str]
    created_at: datetime

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(user_id: str = Depends(get_current_user_id)):
    """
    Fetch all uploaded documents for the current user.
    """
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id, filename, storage_url, created_at FROM user_documents WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,)
                )
                rows = await cur.fetchall()
                
        return [
            DocumentResponse(
                id=r[0],
                filename=r[1],
                storage_url=r[2],
                created_at=r[3]
            ) for r in rows
        ]
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{doc_id}")
async def delete_document(doc_id: int, user_id: str = Depends(get_current_user_id)):
    """
    Delete a document from:
    1. Postgres user_documents table
    2. Vector database embeddings
    3. Supabase storage bucket
    """
    try:
        # 1. Fetch the document metadata
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT filename FROM user_documents WHERE id = %s AND user_id = %s",
                    (doc_id, user_id)
                )
                row = await cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Document not found")
                
                filename = row[0]
                
                # 2. Delete from Postgres user_documents table
                await cur.execute(
                    "DELETE FROM user_documents WHERE id = %s AND user_id = %s",
                    (doc_id, user_id)
                )
                
                # 3. Delete embeddings from vector DB
                # Note: PGVector table is usually langchain_pg_embedding
                # We use JSONB operator @> to match metadata
                await cur.execute(
                    """
                    DELETE FROM langchain_pg_embedding 
                    WHERE cmetadata->>'user_id' = %s 
                    AND cmetadata->>'source_filename' = %s
                    """,
                    (user_id, filename)
                )

        # 4. Delete from Supabase Storage
        if supabase:
            # We assume the file in storage is named "{user_id}/{filename}"
            # as will be implemented in ingestion.py
            storage_path = f"{user_id}/{filename}"
            try:
                res = supabase.storage.from_("user-documents").remove([storage_path])
                print(f"Supabase storage delete response: {res}")
            except Exception as se:
                print(f"Warning: Failed to delete from Supabase storage: {str(se)}")

        return {"status": "success", "message": f"Document {filename} deleted."}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
