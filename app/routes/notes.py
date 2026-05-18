from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.schemas import NoteCreate, NoteUpdate, NoteResponse
from app.ai_service import generate_note_insights
from app.auth_utils import get_current_user_id

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.post("", response_model=NoteResponse)
async def create_note(
    note: NoteCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: Client = Depends(lambda: __import__("app.main", fromlist=["get_db"]).get_db()),
):
    try:
        note_data = note.model_dump() if hasattr(note, "model_dump") else note.dict()
        note_data["user_id"] = current_user_id
        note_data.setdefault("tags", [])
        note_data.setdefault("is_archived", False)

        # AI Insights Processing
        ai_insights = await generate_note_insights(note_data.get("title", ""), note_data.get("content", ""))
        note_data["ai_summary"] = ai_insights.get("summary", "No summary generated.")
        note_data["ai_action_items"] = ai_insights.get("action_items", [])
        note_data["suggested_title"] = ai_insights.get("suggested_title", note_data.get("title"))

        response = db.table("notes").insert(note_data).execute()
        data_returned = response.data or []

        if len(data_returned) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Database insertion returned an empty payload."
            )

        return data_returned
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI pipeline failure: {str(e)}")


@router.get("", response_model=list[NoteResponse])
async def get_notes(
    tag: str | None = None,
    keyword: str | None = None,
    current_user_id: str = Depends(get_current_user_id),
    db: Client = Depends(lambda: __import__("app.main", fromlist=["get_db"]).get_db()),
):
    try:
        query = db.table("notes").select("*").eq("user_id", current_user_id).eq("is_archived", False)

        if keyword:
            query = query.or_(f"title.ilike.%{keyword}%,content.ilike.%{keyword}%")
        if tag:
            query = query.contains("tags", [tag])

        response = query.order("updated_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shared/{note_id}", response_model=NoteResponse)
async def get_public_shared_note(
    note_id: str,
    db: Client = Depends(lambda: __import__('app.main', fromlist=['get_db']).get_db())
):
    """
    Public read-only endpoint. Bypasses user authentication to serve notes marked as public.
    """
    try:
        response = db.table("notes").select("*").eq("id", note_id).execute()
        data = response.data or []
        
        if not data:
            raise HTTPException(status_code=404, detail="Shared note resource not found.")
            
        # Extract the singular dictionary object out of the list wrapper
        note = data
        
        # Secure checking: If the note isn't public, reject anonymous viewing
        if not note.get("is_public"):
            raise HTTPException(status_code=403, detail="Access denied. This note configuration profile is private.")
            
        return note
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Public delivery pipeline failure: {str(e)}")


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note_by_id(
    note_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Client = Depends(lambda: __import__("app.main", fromlist=["get_db"]).get_db()),
):
    try:
        response = db.table("notes").select("*").eq("id", note_id).eq("user_id", current_user_id).execute()
        data = response.data or []
        if len(data) == 0:
            raise HTTPException(status_code=404, detail="Note not found or unauthorized access")
        return data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    note_update: NoteUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: Client = Depends(lambda: __import__("app.main", fromlist=["get_db"]).get_db()),
):
    try:
        update_data = {k: v for k, v in note_update.model_dump(exclude_unset=True).items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        existing_response = db.table("notes").select("*").eq("id", note_id).eq("user_id", current_user_id).execute()
        existing_data = existing_response.data or []

        if len(existing_data) == 0:
            raise HTTPException(status_code=404, detail="Requested note resource not found or modification unauthorized.")

        current_note = existing_data
        new_title = update_data.get("title", current_note.get("title"))
        new_content = update_data.get("content", current_note.get("content"))

        if "title" in update_data or "content" in update_data:
            ai_insights = await generate_note_insights(new_title, new_content)
            update_data["ai_summary"] = ai_insights.get("summary", "No summary generated.")
            update_data["ai_action_items"] = ai_insights.get("action_items", [])
            update_data["suggested_title"] = ai_insights.get("suggested_title", new_title)

        response = db.table("notes").update(update_data).eq("id", note_id).eq("user_id", current_user_id).execute()
        data_returned = response.data or []

        if len(data_returned) == 0:
            raise HTTPException(status_code=404, detail="Failed to update target record storage node.")

        return data_returned
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Modification loop mutation failure: {str(e)}")


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Client = Depends(lambda: __import__("app.main", fromlist=["get_db"]).get_db()),
):
    try:
        response = db.table("notes").delete().eq("id", note_id).eq("user_id", current_user_id).execute()
        data = response.data or []
        if len(data) == 0:
            raise HTTPException(status_code=404, detail="Note not found or deletion unauthorized")
        return {"message": f"Note {note_id} successfully deleted"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{note_id}/archive", response_model=NoteResponse)
async def archive_note(
    note_id: str,
    is_archived: bool = True,
    current_user_id: str = Depends(get_current_user_id),
    db: Client = Depends(lambda: __import__("app.main", fromlist=["get_db"]).get_db()),
):
    try:
        response = (
            db.table("notes")
            .update({"is_archived": is_archived})
            .eq("id", note_id)
            .eq("user_id", current_user_id)
            .execute()
        )
        data_returned = response.data or []

        if len(data_returned) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note resource not found or modification unauthorized.",
            )

        return data_returned
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Archive pipeline failure: {str(e)}",
        )