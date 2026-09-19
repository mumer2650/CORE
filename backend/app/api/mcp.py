from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.core.security import get_current_user_id

router = APIRouter(prefix="/api/mcp", tags=["MCP"])

class MCPToolSchema(BaseModel):
    name: str
    description: str
    inputSchema: dict

class MCPServerConfig(BaseModel):
    name: str
    transport: str = "sse" # "sse" or "stdio"
    url: Optional[str] = None
    token: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    tools: List[MCPToolSchema]
    disabled: bool = False

# Global In-Memory Registry (In production, move to Postgres)
# Maps user_id -> List of MCPServerConfig
user_mcp_registry: Dict[str, List[MCPServerConfig]] = {}

class MCPRegisterRequest(BaseModel):
    name: str
    transport: str = "sse" # "sse" or "stdio"
    sse_url: Optional[str] = None
    auth_token: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None

@router.post("/register")
async def register_mcp_server(
    request: MCPRegisterRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Registers a remote MCP server (via SSE) or local command (via stdio) to a specific user's profile.
    This fetches the tool schema immediately so the LLM doesn't have to wait during chat.
    """
    try:
        from mcp import ClientSession
        parsed_tools = []
        
        if request.transport == "sse":
            from mcp.client.sse import sse_client
            headers = {}
            if request.auth_token:
                headers["Authorization"] = f"Bearer {request.auth_token}"
                
            async with sse_client(request.sse_url, headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    mcp_tools = await session.list_tools()
                    for t in mcp_tools.tools:
                        parsed_tools.append(MCPToolSchema(
                            name=t.name, description=t.description or "", inputSchema=t.inputSchema
                        ))
        elif request.transport == "stdio":
            from mcp.client.stdio import stdio_client, StdioServerParameters
            import os
            
            # Merge custom environment with system environment (so npx/node can be found in PATH)
            env_dict = None
            if request.env:
                env_dict = os.environ.copy()
                env_dict.update(request.env)
                
            server_params = StdioServerParameters(
                command=request.command,
                args=request.args or [],
                env=env_dict
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    mcp_tools = await session.list_tools()
                    for t in mcp_tools.tools:
                        parsed_tools.append(MCPToolSchema(
                            name=t.name, description=t.description or "", inputSchema=t.inputSchema
                        ))
        else:
            raise ValueError(f"Unknown transport: {request.transport}")
                    
        if user_id not in user_mcp_registry:
            user_mcp_registry[user_id] = []
            
        # Remove any existing connection with the same name to prevent duplicate tools
        user_mcp_registry[user_id] = [s for s in user_mcp_registry[user_id] if s.name != request.name]
            
        user_mcp_registry[user_id].append(MCPServerConfig(
            name=request.name,
            transport=request.transport,
            url=request.sse_url,
            token=request.auth_token,
            command=request.command,
            args=request.args,
            env=request.env,
            tools=parsed_tools
        ))
        
        return {
            "status": "success", 
            "message": f"Successfully bound MCP server '{request.name}' to your account using {request.transport}.",
            "tools_discovered": len(parsed_tools)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Failed to connect to MCP Server: {str(e)}")

@router.get("/connections")
async def get_connections(user_id: str = Depends(get_current_user_id)):
    """Returns a list of all active MCP servers for the user."""
    servers = user_mcp_registry.get(user_id, [])
    return {
        "connections": [
            {"name": s.name, "disabled": s.disabled}
            for s in servers
        ]
    }

@router.patch("/connections/{name}/toggle")
async def toggle_connection(name: str, user_id: str = Depends(get_current_user_id)):
    """Toggles the disabled state of a specific MCP server."""
    servers = user_mcp_registry.get(user_id, [])
    for s in servers:
        if s.name == name:
            s.disabled = not s.disabled
            return {"status": "success", "disabled": s.disabled}
    raise HTTPException(status_code=404, detail="Server not found.")

@router.delete("/connections/{name}")
async def delete_connection(name: str, user_id: str = Depends(get_current_user_id)):
    """Disconnects and completely removes an MCP server."""
    servers = user_mcp_registry.get(user_id, [])
    for idx, s in enumerate(servers):
        if s.name == name:
            del servers[idx]
            return {"status": "success", "message": f"Disconnected {name}."}
    raise HTTPException(status_code=404, detail="Server not found.")
