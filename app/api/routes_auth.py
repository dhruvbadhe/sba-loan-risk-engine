from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from app.core.security import create_access_token, verify_password

router = APIRouter(tags=["Authentication"])

class Token(BaseModel):
    access_token: str
    token_type: str

USER_DATABASE = {
    "admin": "$2b$12$MeyfKud/uLC0ArGMg./i1ONbd1wG1AdEjVw833dXKFumDvUvkxbXe"
}

@router.post("/login", response_model= Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    hashed_password = USER_DATABASE.get(form_data.username)

    if not hashed_password or not verify_password(form_data.password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub" : form_data.username})

    return {"access_token": access_token, "token_type" : "bearer"}
