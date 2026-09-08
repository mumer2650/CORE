from langchain_core.tools import tool
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

# The list of tools to bind to the LLM and ToolNode
core_tools = [calculator, web_search]
