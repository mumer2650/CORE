import os
from urllib.parse import urlparse, unquote
from mem0 import Memory
from dotenv import load_dotenv

load_dotenv()

# Parse the database URL for Mem0's PGVector config
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql+psycopg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)
    
parsed_url = urlparse(DATABASE_URL) if DATABASE_URL else None

# Mem0 Configuration
config = {
    "llm": {
        "provider": "gemini",
        "config": {
            # Use the direct Gemini provider instead of LiteLLM, matching the RAG node model
            "model": "gemini-3.1-flash-lite", 
            "api_key": os.getenv("GOOGLE_API_KEY"),
        }
    },
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "sentence-transformers/all-MiniLM-L6-v2"
            # Running this locally completely bypasses the Gemini 404 embedding errors!
        }
    },
}

# Only configure vector store if DATABASE_URL is properly parsed
if parsed_url:
    config["vector_store"] = {
        "provider": "pgvector",
        "config": {
            "dbname": parsed_url.path[1:] if parsed_url.path else "postgres",
            "user": parsed_url.username,
            "password": unquote(parsed_url.password) if parsed_url.password else None,
            "host": parsed_url.hostname,
            "port": parsed_url.port or 5432,
            "collection_name": "memories_hf", # Force a new table to fix the 1536 -> 384 dimension mismatch
            "embedding_model_dims": 384 # all-MiniLM-L6-v2 has 384 dimensions
        }
    }

# Initialize Mem0 client
long_term_memory = Memory.from_config(config)

def extract_memory_background(message: str, user_id: str):
    """
    Background task to extract memories from a user message.
    """
    try:
        print(f"Extracting memories for user: {user_id}...")
        # Mem0 analyzes the message and stores findings under the user_id
        long_term_memory.add(message, user_id=user_id)
        print(f"Memory extraction complete for user: {user_id}.")
    except Exception as e:
        print(f"Mem0 extraction failed: {str(e)}")
