from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes import rag_node

def create_basic_rag_graph():
    """
    Creates a simple workflow graph for Phase 1.
    Currently, it only contains the RAG Node. In Phase 3, we will add the Supervisor router here.
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("rag", rag_node)
    
    # Add edges
    workflow.set_entry_point("rag")
    workflow.add_edge("rag", END)
    
    # Compile graph
    return workflow.compile()

# Instantiate the compiled graph so it can be imported by the API
rag_graph = create_basic_rag_graph()
