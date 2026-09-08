from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes import rag_node
from app.core.checkpointer import checkpointer

def create_basic_rag_graph():
    """
    Creates a simple workflow graph for Phase 1 & 2.
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("rag", rag_node)
    
    # Add edges
    workflow.set_entry_point("rag")
    workflow.add_edge("rag", END)
    
    # Compile graph with the postgres checkpointer
    return workflow.compile(checkpointer=checkpointer)

# Instantiate the compiled graph so it can be imported by the API
rag_graph = create_basic_rag_graph()
