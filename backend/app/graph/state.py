from typing import Annotated, TypedDict, List, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    The state structure for the CORE LangGraph agent.
    """
    # The messages list manages the conversational history.
    # The `add_messages` reducer appends new messages to the existing list.
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Retrieved context from the RAG pipeline
    context: str
    
    # To manage routing decisions
    next_node: str
    
    # To store metadata like user_id for multi-tenancy
    metadata: Dict[str, Any]
