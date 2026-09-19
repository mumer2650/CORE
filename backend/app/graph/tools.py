from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
import ast
import operator as op

# Supported operators for our safe calculator
operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.BitXor: op.xor,
    ast.USub: op.neg
}

def _eval(node):
    if isinstance(node, ast.Constant): # <number>
        return node.value
    elif isinstance(node, ast.BinOp): # <left> <operator> <right>
        return operators[type(node.op)](_eval(node.left), _eval(node.right))
    elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
        return operators[type(node.op)](_eval(node.operand))
    else:
        raise TypeError(node)

def safe_eval(expr):
    """Safely evaluate a mathematical expression string."""
    return _eval(ast.parse(expr, mode='eval').body)

@tool
def calculator(expression: str) -> str:
    """Evaluates mathematical expressions safely. Use this for math questions. Example expression: '(25 * 4) / 3'"""
    try:
        result = safe_eval(expression)
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {str(e)}. Make sure to only use basic math operators."

@tool
def web_search(query: str) -> str:
    """Searches the web using DuckDuckGo. Use this to find current events or real-world facts."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            # We fetch top 3 results
            results = list(ddgs.text(query, max_results=3))
            
        if not results:
            return "No results found."
            
        # Format the results into a string
        formatted_results = ""
        for i, res in enumerate(results):
            formatted_results += f"[{i+1}] {res.get('title')}\nSnippet: {res.get('body')}\nURL: {res.get('href')}\n\n"
        return formatted_results
    except Exception as e:
        return f"Error performing web search: {str(e)}"

@tool
def delete_file(file_path: str) -> str:
    """DANGEROUS: Deletes a file from the system."""
    return f"File {file_path} successfully deleted. (Mock)"

@tool
def search_knowledge_base(query: str, config: RunnableConfig) -> str:
    """Searches the user's uploaded documents (PDFs, TXT, MD) for specific information. Use this when the user asks about their own documents or internal corporate knowledge."""
    try:
        from app.core.vector_store import get_vector_store
        vector_store = get_vector_store()
        
        user_id = config.get("configurable", {}).get("user_id")
        if not user_id:
            return "Error: user_id not found in configuration."
            
        # Perform similarity search with relevance scores and thresholding
        results = vector_store.similarity_search_with_relevance_scores(query, k=5, filter={"user_id": user_id})
        
        # Filter out chunks that don't meet a minimum similarity threshold
        # (Using a baseline threshold like 0.3 for MiniLM embeddings)
        docs = [doc for doc, score in results if score > 0.3]
        
        if not docs:
            return "No relevant information found in your uploaded documents."
            
        context = "\n\n".join([f"--- Document Source: {doc.metadata.get('source_filename', 'Unknown')} ---\n{doc.page_content}" for doc in docs])
        return context
    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"

safe_tools = [calculator, web_search, search_knowledge_base]
sensitive_tools = [delete_file]
all_tools = safe_tools + sensitive_tools
