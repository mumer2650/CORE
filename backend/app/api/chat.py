from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import get_current_user_id
from app.graph.graph import rag_graph
from langchain_core.messages import HumanMessage

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str

@router.post("/")
async def chat_with_agent(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Endpoint to send a message to the RAG Agent and get a response.
    """
    # Initialize the state for this request
    # Note: In Phase 2, we will use a Checkpointer to load existing messages. 
    # For Phase 1, it's a stateless single-turn RAG.
    initial_state = {
        "messages": [HumanMessage(content=request.message)],
        "metadata": {"user_id": user_id}
    }
    
    try:
        # Invoke the LangGraph workflow
        result = await rag_graph.ainvoke(initial_state)
        
        # Extract the AI's response from the last message in the state
        ai_message = result["messages"][-1].content
        
        return {
            "response": ai_message,
            "context_used": result.get("context", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
