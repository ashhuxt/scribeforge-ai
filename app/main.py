import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from .auth_utils import get_current_user_id

load_dotenv()

app = FastAPI(title="ScribeForge AI API",description="Production-grade modular backend engine powering structured text insights and notes telemetry.",
    version="1.0.0"
)

url: str | None = os.environ.get("SUPABASE_URL")
key: str | None = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("\nCRITICAL WARNING: SUPABASE_URL or SUPABASE_KEY is missing from your .env file.\n")

supabase: Client | None = None
try:
    supabase = create_client(url or "https://placeholder.supabase.co", key or "placeholder")
except Exception as e:
    print(f"\nFailed to initialize Supabase client: {str(e)}\n")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> Client:
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database client uninitialized.")
    return supabase


@app.get("/")
async def root():
    return {"message": "Peblo Notes API is Live"}


@app.get("/shared/{note_id}")
async def get_public_shared_note(note_id: str, db: Client = Depends(get_db)):
    try:
        response = db.table("notes").select("*").eq("id", note_id).eq("is_public", True).execute()
        data = response.data or []
        if len(data) == 0:
            raise HTTPException(status_code=403, detail="This private profile asset is inaccessible or link expired.")
        return data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/insights")
async def get_dashboard_insights(
    current_user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    try:
        response = (
            db.table("notes")
            .select("*")
            .eq("user_id", current_user_id)
            .eq("is_archived", False)
            .order("updated_at", desc=True)
            .execute()
        )
        notes_list = response.data or []

        total_notes = len(notes_list)
        tag_counts: dict[str, int] = {}
        ai_summaries_count = 0

        for n in notes_list:
            for t in n.get("tags", []):
                tag_counts[t] = tag_counts.get(t, 0) + 1
            if n.get("ai_summary") and n.get("ai_summary") != "No summary generated.":
                ai_summaries_count += 1

        top_tags = sorted(tag_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]

        return {
            "total_notes": total_notes,
            "ai_usage_statistics": {"summaries_generated": ai_summaries_count},
            "most_used_tags": top_tags,
            "recently_edited_notes": notes_list[:3],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



from .routes import notes, auth

app.include_router(auth.router)
app.include_router(notes.router, dependencies=[Depends(get_db)])
