from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.ingestion import router as ingestion_router
from contextlib import asynccontextmanager
from app.core.checkpointer import pool, checkpointer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Open the connection pool and create checkpointer tables in Supabase
    await pool.open()
    await checkpointer.setup()
    yield
    # Shutdown: Close the connection pool
    await pool.close()

app = FastAPI(
    title="CORE - Agentic Chatbot API",
    description="Backend API for the CORE multi-tenant agentic chatbot.",
    version="0.1.0",
    lifespan=lifespan,
)

# Set up CORS for the frontend React app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.ingestion import router as ingestion_router
from app.api.mcp import router as mcp_router
from app.api.oauth import router as oauth_router

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(ingestion_router)
app.include_router(mcp_router)
app.include_router(oauth_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the CORE API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
