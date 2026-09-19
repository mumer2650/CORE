from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes import general_chat_node, sensitive_tools_node
from app.core.checkpointer import checkpointer
from langgraph.prebuilt import ToolNode
from app.graph.tools import safe_tools, sensitive_tools, all_tools
from langchain_core.runnables import RunnableConfig



def route_tools(state: AgentState, config: RunnableConfig) -> str:
    """Routes to sensitive_tools if ANY tool call is dangerous or remote, else safe_tools."""
    messages = state.get("messages", [])
    if not messages:
        return END
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        user_id = config["configurable"].get("user_id")
        from app.api.mcp import user_mcp_registry
        dynamic_tool_names = []
        if user_id and user_id in user_mcp_registry:
            for s in user_mcp_registry[user_id]:
                if getattr(s, 'disabled', False):
                    continue
                for t in s.tools:
                    dynamic_tool_names.append(t.name)
                    
        sensitive_tool_names = [t.name for t in sensitive_tools] + dynamic_tool_names
        
        if any(tc["name"] in sensitive_tool_names for tc in last_message.tool_calls):
            return "sensitive_tools"
        return "safe_tools"
    return END

def create_basic_rag_graph():
    """
    Creates a streamlined workflow graph with Agentic RAG.
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("general_chat_node", general_chat_node)
    
    # Tool nodes
    workflow.add_node("safe_tools", ToolNode(safe_tools))
    workflow.add_node("sensitive_tools", sensitive_tools_node) # Custom node that supports dynamic remote tools
    
    # Add edges
    workflow.set_entry_point("general_chat_node")
    
    # Route general_chat_node output based on tool types
    workflow.add_conditional_edges("general_chat_node", route_tools, {
        "safe_tools": "safe_tools",
        "sensitive_tools": "sensitive_tools",
        END: END
    })
    
    # Tools nodes always route back to the chat node
    workflow.add_edge("safe_tools", "general_chat_node")
    workflow.add_edge("sensitive_tools", "general_chat_node")
    
    # Compile graph with the postgres checkpointer and HITL interrupt
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["sensitive_tools"]
    )

# Instantiate the compiled graph so it can be imported by the API
rag_graph = create_basic_rag_graph()
