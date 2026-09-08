from app.graph.state import AgentState
from app.core.vector_store import get_vector_store
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import os

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
    
    # 3. Generate Answer
    system_prompt = f"""You are a helpful AI assistant representing the CORE platform. 
    Use the following retrieved context to answer the user's question. 
    If the context does not contain the answer, politely state that you do not know based on the provided documents.
    
    Context:
    {context}
    """
    
    # We pass the system prompt followed by the user's conversation history
    invoke_messages = [SystemMessage(content=system_prompt)] + messages
    
    response = await llm.ainvoke(invoke_messages)
    
    # Update the state: append the new AIMessage and update the context string
    return {
        "messages": [response],
        "context": context
    }
