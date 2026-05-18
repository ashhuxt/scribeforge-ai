from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from supabase import Client

from app.schemas import UserCreate, UserResponse, Token
from app.auth_utils import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserCreate,
    db: Client = Depends(lambda: __import__("app.main", fromlist=["get_db"]).get_db()),
):
    try:
        # Check for pre-existing credential profiles
        existing = db.table("users").select("id").eq("email", user_data.email).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email matching this credential profile is already registered.",
            )

        hashed_password = get_password_hash(user_data.password)
        db_user = {
            "email": user_data.email,
            "password_hash": hashed_password,
            "name": user_data.name,
        }

        response = db.table("users").insert(db_user).execute()
        data = response.data or []
        if len(data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to commit user profile record.",
            )

        # Let FastAPI automatically serialize the first dictionary object matching UserResponse
        return data
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration pipeline failure: {str(e)}",
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Client = Depends(lambda: __import__("app.main", fromlist=["get_db"]).get_db()),
):
    try:
        response = db.table("users").select("*").eq("email", form_data.username).execute()
        user_record = response.data or []

        if len(user_record) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email credentials provided.",
            )

        user = user_record
        if not verify_password(form_data.password, user.get("password_hash", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password credentials provided.",
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.get("id"))},
            expires_delta=access_token_expires,
        )

        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication pipeline failure: {str(e)}",
        )