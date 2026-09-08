from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import get_current_user_id
from app.graph.graph import rag_graph
from langchain_core.messages import HumanMessage

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    thread_id: str

@router.post("/")
async def chat_with_agent(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Endpoint to send a message to the RAG Agent and get a response.
    Includes thread_id for short-term memory (LangGraph checkpointer).
    """
    # When using a checkpointer, we only need to pass the NEW message.
    # LangGraph will automatically load the historical messages from the database.
    input_state = {
        "messages": [HumanMessage(content=request.message)],
        "metadata": {"user_id": user_id}
    }
    
    # Configuration for the checkpointer
    config = {
        "configurable": {
            "thread_id": request.thread_id,
            "user_id": user_id
        }
    }
    
    try:
        # Invoke the LangGraph workflow
        result = await rag_graph.ainvoke(input_state, config)
        
        # Extract the AI's response from the last message in the state
        ai_message = result["messages"][-1].content
        
        return {
            "response": ai_message,
            "context_used": result.get("context", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
