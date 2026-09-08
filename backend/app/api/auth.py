from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
import jwt
from app.core.security import SECRET_KEY, ALGORITHM

router = APIRouter(tags=["Auth"])

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    TESTING ENDPOINT: Generates a JWT token for testing.
    In a real app, this would verify passwords against a database.
    For now, enter ANY username and password. 
    The 'username' you enter will become your 'user_id' in the database!
    """
    payload = {"sub": form_data.username}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": token, "token_type": "bearer"}
