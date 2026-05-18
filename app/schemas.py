from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

# --- Authentication Schemas ---
class UserSignup(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[str] = None


# --- Notes Workspace Schemas ---
class NoteCreate(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = False
    is_archived: Optional[bool] = False


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    is_archived: Optional[bool] = None


class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    tags: List[str]
    is_public: bool
    is_archived: bool
    user_id: str
    ai_summary: Optional[str] = None
    ai_action_items: Optional[List[str]] = None
    suggested_title: Optional[str] = None  # Added for AI title suggestions match
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NoteInsightsResponse(BaseModel):
    summary: str = Field(description="A concise, high-level summary of the note context.")
    action_items: List[str] = Field(description="An array of extracted, clear, actionable tasks.")
    suggested_title: str = Field(description="A catchy, concise title suggested based on the note content.")