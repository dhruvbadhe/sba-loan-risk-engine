from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings
from supabase import create_client, Client
import logging

logger = logging.getLogger("app")
router = APIRouter(tags=["Authentication"])

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str = Field(..., example="dhruv")
    password: str = Field(..., example="mypassword123")

# Initialize Supabase client
supabase_client: Client = None
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    try:
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client in auth: {e}")

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user: UserCreate):
    """
    Registers a new user in the Supabase database.
    """
    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not configured."
        )

    # 1. Check if username already exists
    try:
        existing = supabase_client.table("users").select("username").eq("username", user.username).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Supabase query error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error."
        )

    # 2. Hash password and insert user record
    hashed = get_password_hash(user.password)
    try:
        supabase_client.table("users").insert({
            "username": user.username,
            "password_hash": hashed
        }).execute()
        return {"message": "User registered successfully."}
    except Exception as e:
        logger.error(f"Supabase insert error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user."
        )

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Validates user credentials against Supabase and issues a JWT token.
    """
    if not supabase_client:
        # Fallback to local admin user for testing if Supabase is offline
        if form_data.username == "admin" and form_data.password == "admin":
            access_token = create_access_token(data={"sub": "admin"})
            return {"access_token": access_token, "token_type": "bearer"}
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not configured."
        )

    # 1. Fetch user hash from Supabase
    try:
        res = supabase_client.table("users").select("password_hash").eq("username", form_data.username).execute()
        user_data = res.data
    except Exception as e:
        logger.error(f"Supabase auth query error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database verification error."
        )

    # 2. Verify username exists and password matches
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    hashed_password = user_data[0]["password_hash"]
    if not verify_password(form_data.password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Generate token
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}
