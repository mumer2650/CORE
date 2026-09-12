from app.graph.state import AgentState
from app.core.vector_store import get_vector_store
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, trim_messages
from langchain_core.runnables import RunnableConfig
import os
from pydantic import BaseModel, Field

# Initialize the LLM (Requires GOOGLE_API_KEY in .env)
# Using Gemini 3.1 Flash Lite for ultra-fast, cost-effective inference
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)

async def rag_node(state: AgentState) -> dict:
    """
    RAG Node: Retrieves context based on the latest user message, 
    formats it, and generates an answer using the LLM.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"messages": [AIMessage(content="No input provided.")]}
        
    last_message = messages[-1].content
    user_id = state.get("metadata", {}).get("user_id")
    
    if not user_id:
        return {"messages": [AIMessage(content="Error: user_id missing from state metadata.")]}

    # 1. Retrieve relevant documents
    vector_store = get_vector_store()
    
    # Use metadata filtering to ensure multi-tenancy (only get this user's docs)
    retriever = vector_store.as_retriever(
        search_kwargs={
            "k": 3,
            "filter": {"user_id": user_id}
        }
    )
    
    # Since PGVector is initialized with a synchronous connection string, we use invoke()
    docs = retriever.invoke(last_message)
    
    # 2. Format context
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # 3. Retrieve Long-Term Memory (Mem0)
    try:
        from app.core.memory import long_term_memory
        memories = long_term_memory.search(last_message, filters={"user_id": user_id})
        
        # In newer versions of Mem0, search returns a dict like {"results": [{memory}]}
        if isinstance(memories, dict) and "results" in memories:
            memories_list = memories["results"]
        elif isinstance(memories, list):
            memories_list = memories
        else:
            memories_list = []
            
        if memories_list:
            profile_facts = "\n".join([f"- {m.get('memory', m)}" if isinstance(m, dict) else f"- {m}" for m in memories_list])
        else:
            profile_facts = "No relevant profile facts found."
    except Exception as e:
        print(f"Mem0 search error: {str(e)}")
        profile_facts = "Could not retrieve user profile."
    
    # 4. Generate Answer
    system_prompt = f"""You are a helpful AI assistant representing the CORE platform. 
    Use the following retrieved context to answer the user's question. 
    If the context does not contain the answer, politely state that you do not know based on the provided documents.
    IMPORTANT: Do NOT proactively mention the user's profile facts, name, or memories unless they are explicitly asked about or directly relevant to answering their current question. Keep greetings concise.
    
    FORMATTING RULES:
    - ALWAYS format lists using proper Markdown bullets (e.g., `- **Item Name:** Description`).
    - Never leave dangling markdown syntax like unmatched `**`.
    - Synthesize the retrieved context naturally rather than just copy-pasting raw document fragments.
    
    --- USER PROFILE (Mem0 Long-Term Memory) ---
    {profile_facts}
    --------------------------------------------
    
    Context:
    {context}
    """
    
    # 4. Trim Messages (Context Window Management)
    # We keep only the last 10 messages to avoid hitting token limits,
    # ensuring the trimmed list always starts with a HumanMessage.
    trimmed_messages = trim_messages(
        messages,
        max_tokens=4000, 
        token_counter=len, # Treating each message as 1 token for simplicity
        strategy="last",
        include_system=False,
        start_on="human",
        allow_partial=False
    )
    
    # Fix for Gemini SDK bug: AIMessages with tool calls often have empty content string ""
    # This causes 'ValueError: contents are required' in the Gemini adapter when fed back into history.
    safe_messages = []
    for msg in trimmed_messages:
        if isinstance(msg, AIMessage) and not msg.content:
            safe_msg = AIMessage(content=" ", tool_calls=getattr(msg, "tool_calls", []), additional_kwargs=getattr(msg, "additional_kwargs", {}))
            safe_messages.append(safe_msg)
        else:
            safe_messages.append(msg)
            
    # We pass the system prompt followed by the trimmed conversation history
    invoke_messages = [SystemMessage(content=system_prompt)] + safe_messages
    
    response = await llm.ainvoke(invoke_messages)
    
    # Update the state: append the new AIMessage and update the context string
    return {
        "messages": [response],
        "context": context
    }

class RouteDecision(BaseModel):
    next_node: str = Field(description="The next node to route the conversation to. Options are: 'rag_node' or 'general_chat_node'.")

async def supervisor_node(state: AgentState) -> dict:
    """
    Supervisor Node: Classifies the user intent and routes to the appropriate worker node.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"next_node": "general_chat_node"}
        
    last_message = messages[-1].content
    
    # We use a structured output LLM call for deterministic routing
    system_prompt = """You are a highly intelligent routing supervisor.
Your job is to read the user's input and decide which subsystem should handle it.

Route to 'rag_node' IF AND ONLY IF:
- The user is explicitly asking about uploaded documents, PDFs, specific corporate files, or internal data that is stored in their private database.
- IMPORTANT: Do NOT route to 'rag_node' for queries about GitHub, external integrations, or MCP tools.

Route to 'general_chat_node' IF:
- The user is asking about current events, live news, or external facts.
- The user is asking to use their GitHub account or other connected integrations (this node has access to MCP tools).
- The user is asking general questions, writing code, chatting, greeting, or asking about themselves/their profile facts.

Make your decision carefully."""
    
    supervisor_llm = llm.with_structured_output(RouteDecision)
    
    invoke_messages = [SystemMessage(content=system_prompt), HumanMessage(content=last_message)]
    
    try:
        decision = await supervisor_llm.ainvoke(invoke_messages)
        return {"next_node": decision.next_node}
    except Exception as e:
        print(f"Supervisor routing error: {str(e)}")
        # Default to general chat on failure
        return {"next_node": "general_chat_node"}


async def general_chat_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    General Chat Node: Handles conversational queries without the overhead of PGVector retrieval.
    Still uses Mem0 for long-term user profile context.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"messages": [AIMessage(content="No input provided.")]}
        
    last_message = messages[-1].content
    user_id = state.get("metadata", {}).get("user_id")
    
    # 1. Retrieve Long-Term Memory (Mem0)
    try:
        from app.core.memory import long_term_memory
        memories = long_term_memory.search(last_message, filters={"user_id": user_id})
        
        if isinstance(memories, dict) and "results" in memories:
            memories_list = memories["results"]
        elif isinstance(memories, list):
            memories_list = memories
        else:
            memories_list = []
            
        if memories_list:
            profile_facts = "\n".join([f"- {m.get('memory', m)}" if isinstance(m, dict) else f"- {m}" for m in memories_list])
        else:
            profile_facts = "No relevant profile facts found."
    except Exception as e:
        print(f"Mem0 search error: {str(e)}")
        profile_facts = "Could not retrieve user profile."
    # 2. Fetch Active Integrations
    user_id = config["configurable"].get("user_id")
    from app.api.mcp import user_mcp_registry
    
    active_integrations = []
    if user_id and user_id in user_mcp_registry:
        for s in user_mcp_registry[user_id]:
            if not getattr(s, 'disabled', False):
                active_integrations.append(s.name)
    integration_text = ""
    if active_integrations:
        integration_text = f"\n--- ACTIVE INTEGRATIONS (MCP) ---\nYou currently have the following external integrations enabled: {', '.join(active_integrations)}\nWhen the user asks if you have access to these services, enthusiastically confirm that you DO have full access and are ready to help. Do not add defensive caveats about 'persistent access' or 'only when requested'.\n---------------------------------"

    # 3. Generate Answer
    system_prompt = f"""You are a helpful AI assistant representing the CORE platform. 
    You are in a general conversation with the user.
    IMPORTANT: Do NOT proactively mention the user's profile facts, name, or memories unless they are explicitly asked about or directly relevant to answering their current question. Keep greetings concise.
    
    FORMATTING RULES:
    - ALWAYS format lists using proper Markdown bullets (e.g., `- **Item Name:** Description`).
    - Never leave dangling markdown syntax like unmatched `**`.
    - Provide clear, highly readable, and structured responses. 
    - If summarizing data (like tools, repositories, or lists), state the total count first before listing them.
    - NEVER output raw tool names in your text response. If you want to use a tool, invoke it properly.
    
    --- USER PROFILE (Mem0 Long-Term Memory) ---
    {profile_facts}
    --------------------------------------------
    {integration_text}
    """
    
    # 4. Trim Messages
    trimmed_messages = trim_messages(
        messages,
        max_tokens=4000, 
        token_counter=len, # Note: using len is a naive token counter (character count), so 4000 is ~1000 tokens
        strategy="last",
        include_system=False,
        start_on="human",
        allow_partial=False
    )
    
    # Fix for Gemini SDK bug: AIMessages with tool calls often have empty content string ""
    # This causes 'ValueError: contents are required' in the Gemini adapter when fed back into history.
    safe_messages = []
    for msg in trimmed_messages:
        if isinstance(msg, AIMessage) and not msg.content:
            safe_msg = AIMessage(content=" ", tool_calls=getattr(msg, "tool_calls", []), additional_kwargs=getattr(msg, "additional_kwargs", {}))
            safe_messages.append(safe_msg)
        else:
            safe_messages.append(msg)
            
    invoke_messages = [SystemMessage(content=system_prompt)] + safe_messages
    
    from app.graph.tools import all_tools
    
    # 5. Fetch Dynamic MCP Tools for this user
    dynamic_tool_schemas = []
    if user_id and user_id in user_mcp_registry:
        for server in user_mcp_registry[user_id]:
            if getattr(s, 'disabled', False) or getattr(server, 'disabled', False):
                continue
            for t in server.tools:
                schema = {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema
                    }
                }
                dynamic_tool_schemas.append(schema)
                
    # Bind statically defined tools + dynamic schemas
    llm_with_tools = llm.bind_tools(all_tools + dynamic_tool_schemas)
    response = await llm_with_tools.ainvoke(invoke_messages)
    
    return {
        "messages": [response],
        "context": "No context retrieved. (General Chat Node)"
    }

async def sensitive_tools_node(state: AgentState, config: RunnableConfig):
    """
    Custom node to execute sensitive tools (both local and remote MCP).
    """
    from langchain_core.messages import ToolMessage
    from app.api.mcp import user_mcp_registry
    
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", [])
    user_id = config["configurable"].get("user_id")
    
    results = []
    
    for tc in tool_calls:
        name = tc["name"]
        args = tc["args"]
        
        # 1. Check if it's a local tool
        from app.graph.tools import sensitive_tools, safe_tools
        local_tool = next((t for t in sensitive_tools + safe_tools if t.name == name), None)
        if local_tool:
            try:
                res = await local_tool.ainvoke(args)
                results.append(ToolMessage(tool_call_id=tc["id"], name=name, content=str(res)))
            except Exception as e:
                results.append(ToolMessage(tool_call_id=tc["id"], name=name, content=f"Error: {e}"))
            continue
            
        # 2. Check if it's a dynamic remote tool
        found = False
        if user_id and user_id in user_mcp_registry:
            for server in user_mcp_registry[user_id]:
                if server.disabled:
                    continue
                if any(t.name == name for t in server.tools):
                    if server.transport == "sse":
                        from mcp.client.sse import sse_client
                        from mcp import ClientSession
                        
                        headers = {}
                        if server.token:
                            headers["Authorization"] = f"Bearer {server.token}"
                            
                        try:
                            async with sse_client(server.url, headers=headers) as (read, write):
                                async with ClientSession(read, write) as session:
                                    await session.initialize()
                                    mcp_res = await session.call_tool(name, arguments=args)
                                    content_str = "\n".join([c.text for c in mcp_res.content if c.type == "text"])
                                    results.append(ToolMessage(tool_call_id=tc["id"], name=name, content=content_str))
                        except Exception as e:
                            results.append(ToolMessage(tool_call_id=tc["id"], name=name, content=f"Remote MCP Error: {e}"))
                    elif server.transport == "stdio":
                        from mcp.client.stdio import stdio_client, StdioServerParameters
                        from mcp import ClientSession
                        import os
                        
                        env_dict = None
                        if server.env:
                            env_dict = os.environ.copy()
                            env_dict.update(server.env)
                            
                        server_params = StdioServerParameters(
                            command=server.command,
                            args=server.args or [],
                            env=env_dict
                        )
                        try:
                            async with stdio_client(server_params) as (read, write):
                                async with ClientSession(read, write) as session:
                                    await session.initialize()
                                    mcp_res = await session.call_tool(name, arguments=args)
                                    content_str = "\n".join([c.text for c in mcp_res.content if c.type == "text"])
                                    results.append(ToolMessage(tool_call_id=tc["id"], name=name, content=content_str))
                        except Exception as e:
                            results.append(ToolMessage(tool_call_id=tc["id"], name=name, content=f"Local MCP Error: {e}"))
                    
                    found = True
                    break
                    
        if not found:
            results.append(ToolMessage(tool_call_id=tc["id"], name=name, content="Error: Tool not found."))
            
    return {"messages": results}
