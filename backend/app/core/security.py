from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
import os
from dotenv import load_dotenv

# Load variables from .env file into the environment
load_dotenv()

# The URL where the frontend would send credentials to get a token.
# Adjust this based on your actual authentication endpoint.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# In production, ALWAYS load this from an environment variable!
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-for-dev")
ALGORITHM = "HS256"

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    Extracts the user_id from the JWT token provided in the Authorization header.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 'sub' (subject) is the standard JWT claim for user ID
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        return user_id
    except jwt.PyJWTError:
        # For development purposes, if token is invalid, we'll raise an exception.
        # You can comment out 'raise credentials_exception' and return a dummy ID if testing without tokens.
        raise credentials_exception
