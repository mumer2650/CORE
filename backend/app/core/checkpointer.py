import os
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from dotenv import load_dotenv

load_dotenv()

# We use the same Supabase connection URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Create a global connection pool
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0, # Disable prepared statements for PgBouncer compatibility
}

# The pool is created synchronously but opened asynchronously on app startup
pool = AsyncConnectionPool(
    conninfo=DATABASE_URL,
    max_size=20,
    kwargs=connection_kwargs,
    open=False
)

# Initialize the checkpointer
checkpointer = AsyncPostgresSaver(pool)
