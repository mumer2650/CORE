import os
import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
import jwt
from app.core.security import SECRET_KEY, ALGORITHM
from app.api.mcp import user_mcp_registry, MCPServerConfig, MCPToolSchema

router = APIRouter(prefix="/api/oauth", tags=["OAuth"])

@router.get("/github/login")
async def github_login(token: str = Query(...)):
    """Redirects user to GitHub OAuth with their JWT token in the state parameter."""
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitHub Client ID not configured.")
        
    # State parameter helps us remember who the user is when GitHub redirects back
    state = token 
    github_auth_url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&state={state}&scope=repo,read:user"
    return RedirectResponse(github_auth_url)

@router.get("/github/callback")
async def github_callback(code: str, state: str):
    """Handles the GitHub OAuth callback, exchanges code for token, and binds the MCP server."""
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
    
    if not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub Client Secret not configured.")
        
    # 1. Validate JWT Token from state
    try:
        payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("No user ID in token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid session state: {str(e)}")

    # 2. Exchange code for access token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code
            },
            headers={"Accept": "application/json"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange OAuth token with GitHub")
            
        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail=f"No access token received: {data}")

    # 3. Register the GitHub MCP Server
    try:
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client, StdioServerParameters
        
        env_dict = os.environ.copy()
        env_dict["GITHUB_PERSONAL_ACCESS_TOKEN"] = access_token
        
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env=env_dict
        )
        
        parsed_tools = []
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                mcp_tools = await session.list_tools()
                for t in mcp_tools.tools:
                    parsed_tools.append(MCPToolSchema(
                        name=t.name, description=t.description or "", inputSchema=t.inputSchema
                    ))
                    
        if user_id not in user_mcp_registry:
            user_mcp_registry[user_id] = []
            
        # Remove any existing connection with the same name to prevent duplicate tools
        user_mcp_registry[user_id] = [s for s in user_mcp_registry[user_id] if s.name != "GitHub (OAuth)"]
            
        user_mcp_registry[user_id].append(MCPServerConfig(
            name="GitHub (OAuth)",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": access_token},
            tools=parsed_tools
        ))
        
        # 4. Redirect back to frontend
        return RedirectResponse("http://localhost:5173/?mcp_connected=true")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to bind MCP Server: {str(e)}")
