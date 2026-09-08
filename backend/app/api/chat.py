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
        
        # Check if the graph hit a Human-in-the-Loop breakpoint
        state = await rag_graph.aget_state(config)
        if state.next:
            last_msg = result["messages"][-1]
            return {
                "status": "requires_action",
                "pending_tools": last_msg.tool_calls
            }
            
        # Normal return
        ai_message = result["messages"][-1].content
        return {
            "status": "completed",
            "response": ai_message,
            "context_used": result.get("context", "")
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class ApproveRequest(BaseModel):
    thread_id: str
    approved: bool

@router.post("/approve")
async def approve_action(
    request: ApproveRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Endpoint to approve or reject a pending sensitive tool execution.
    """
    config = {"configurable": {"thread_id": request.thread_id, "user_id": user_id}}
    
    try:
        from langchain_core.messages import ToolMessage
        state = await rag_graph.aget_state(config)
        
        if not state.next:
            return {"status": "error", "detail": "No pending action to approve."}
            
        if request.approved:
            # Resume graph normally (it will execute the tools node)
            result = await rag_graph.ainvoke(None, config)
        else:
            # User rejected. Provide a ToolMessage simulating a rejection
            last_msg = state.values["messages"][-1]
            rejection_msgs = [
                ToolMessage(
                    tool_call_id=tc["id"],
                    name=tc["name"],
                    content="ERROR: The human user rejected this action for security reasons. Apologize and ask for a different approach."
                ) for tc in last_msg.tool_calls
            ]
            # Trick the graph into thinking the "sensitive_tools" node ran and returned the rejection
            await rag_graph.aupdate_state(config, {"messages": rejection_msgs}, as_node="sensitive_tools")
            
            # Now resume graph from the node AFTER sensitive_tools (which is general_chat_node)
            result = await rag_graph.ainvoke(None, config)

        # Check if it interrupted again
        new_state = await rag_graph.aget_state(config)
        if new_state.next:
            return {"status": "requires_action", "pending_tools": result["messages"][-1].tool_calls}
            
        return {
            "status": "completed",
            "response": result["messages"][-1].content
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
