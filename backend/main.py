from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.ingestion import router as ingestion_router

app = FastAPI(
    title="CORE - Agentic Chatbot API",
    description="Backend API for the CORE multi-tenant agentic chatbot.",
    version="0.1.0",
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
from app.api.ingestion import router as ingestion_router
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router

app.include_router(auth_router)
app.include_router(ingestion_router)
app.include_router(chat_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the CORE API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
