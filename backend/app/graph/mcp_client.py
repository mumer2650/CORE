import os

# Note: The 'langchain_mcp_adapters' library provides native wrappers for MCP.
# This is a boilerplate script. You will need to pip install mcp and langchain-mcp-adapters when ready to use it.
# from langchain_mcp_adapters.client import MCPClient
# from langchain_mcp_adapters.tools import load_mcp_tools

async def get_github_mcp_tools():
    """
    Connects to the official GitHub MCP server and returns a list of Langchain-compatible tools.
    Requires GITHUB_PERSONAL_ACCESS_TOKEN in .env.
    """
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        print("No GitHub token found, skipping MCP GitHub integration.")
        return []
        
    try:
        from langchain_mcp_adapters.client import MCPClient
        from langchain_mcp_adapters.tools import load_mcp_tools
        
        # Standard configuration for the official github server
        # Running via npx ensures we don't need to manually install node packages
        client = MCPClient(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": token}
        )
        
        # Initialize connection
        await client.initialize()
        
        # Load the tools and convert them to Langchain @tool format
        tools = await load_mcp_tools(client)
        print(f"Successfully loaded {len(tools)} GitHub tools via MCP!")
        return tools
    except Exception as e:
        print(f"Failed to connect to MCP Server: {e}")
        return []
