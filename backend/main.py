from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

@app.get("/")
async def root():
    return {"message": "Welcome to the CORE API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
