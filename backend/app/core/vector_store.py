from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()

# Fetch the database URL. 
# We use the DIRECT_URL (port 5432) because SQLAlchemy doesn't always play nicely with PgBouncer prepared statements.
DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy requires the connection string to use the psycopg driver explicitly
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Initialize the embedding model (runs locally)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_vector_store() -> PGVector:
    """
    Returns an instance of the PGVector vector store connected to Supabase.
    """
    return PGVector(
        embeddings=embeddings,
        collection_name="core_documents",
        connection=DATABASE_URL,
        use_jsonb=True, # Recommended for faster metadata filtering
    )
