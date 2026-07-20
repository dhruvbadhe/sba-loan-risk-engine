from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from app.core.config import settings
from app.core.security import decode_access_token

api_key_header = APIKeyHeader(name= "X-API-KEY", auto_error=False)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)

async def verify_api_access(
        api_key: str = Security(api_key_header),
        token: str = Security(oauth2_scheme)
):
    if api_key and api_key == settings.API_KEY:
        return {"auth_method" : "api_key"}
    
    if token:
        payload = decode_access_token(token)
        if payload is not None:
            return {"auth_method" : "jwt", "user" : payload.get("sub")}
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "Invalid, missing, or expired credentials (API Key or JWT Token)",
            headers={"WWW-Authenticate": "Bearer"},
        )