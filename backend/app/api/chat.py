from fastapi import APIRouter, Depends, HTTPException, Path, BackgroundTasks
from pydantic import BaseModel
from app.core.security import get_current_user_id
from app.graph.graph import rag_graph
from app.core.checkpointer import checkpointer
from app.core.memory import extract_memory_background
from langchain_core.messages import HumanMessage

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    thread_id: str

@router.post("/")
async def chat_with_agent(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id)
):
    """
    Endpoint to send a message to the RAG Agent and get a response.
    Includes thread_id for short-term memory (LangGraph checkpointer).
    Triggers Mem0 extraction in the background.
    """
    # Spawn background task for Mem0 extraction (doesn't block the chat response)
    background_tasks.add_task(extract_memory_background, request.message, user_id)
    
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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{thread_id}/history")
async def get_chat_history(
    thread_id: str = Path(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieve the full chat history for a specific thread.
    This fetches the untrimmed history directly from the LangGraph checkpointer.
    Ensures that only the owner of the thread can access it.
    """
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    try:
        # Fetch the state from the Postgres checkpointer
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        
        if not checkpoint_tuple:
            return {"messages": []}
            
        # The actual graph state is stored in channel_values
        state = checkpoint_tuple.checkpoint.get("channel_values", {})
        metadata = state.get("metadata", {})
        
        # Security check: Ensure the thread belongs to the current user
        if metadata.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this thread.")
            
        # Convert Langchain message objects to raw dicts for JSON response
        messages = state.get("messages", [])
        formatted_messages = [
            {
                "role": "user" if isinstance(msg, HumanMessage) else "assistant", 
                "content": msg.content
            }
            for msg in messages
        ]
        
        return {"messages": formatted_messages}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
