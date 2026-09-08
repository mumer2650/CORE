from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes import rag_node, supervisor_node, general_chat_node
from app.core.checkpointer import checkpointer

def route_decision(state: AgentState) -> str:
    # Read the next_node string from the state to determine the route
    return state.get("next_node", "general_chat_node")

def create_basic_rag_graph():
    """
    Creates a supervisor-routed workflow graph for Phase 3.
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("rag_node", rag_node)
    workflow.add_node("general_chat_node", general_chat_node)
    
    # Add edges
    workflow.set_entry_point("supervisor")
    
    # Conditional edge from supervisor to workers
    workflow.add_conditional_edges(
        "supervisor",
        route_decision,
        {
            "rag_node": "rag_node",
            "general_chat_node": "general_chat_node"
        }
    )
    
    # End edges
    workflow.add_edge("rag_node", END)
    workflow.add_edge("general_chat_node", END)
    
    # Compile graph with the postgres checkpointer
    return workflow.compile(checkpointer=checkpointer)

# Instantiate the compiled graph so it can be imported by the API
rag_graph = create_basic_rag_graph()
