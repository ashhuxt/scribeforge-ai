import os
import logging
from google import genai
from google.genai import types
from .schemas import NoteInsightsResponse

client = genai.Client()

async def generate_note_insights(title: str, content: str) -> dict:
    """
    Leverages Gemini 2.5 Flash to generate structured text insights
    with zero local overhead and minimal network bandwidth.
    """
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        logging.error("Inference halted: API Key missing from environment context.")
        return {
            "summary": "AI Insight engine unconfigured. Please provision an API Key.",
            "action_items": [],
            "suggested_title": title  # Fallback to current title
        }

    prompt = f"""
    You are an expert full-stack developer and architectural assistant.
    Analyze the following technical note and extract a summary, explicit action items, and a concise, highly accurate suggested title.
    
    Document Title: {title}
    Document Content: {content}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=NoteInsightsResponse,
                temperature=0.2,
            ),
        )

        parsed = response.parsed
        if parsed is None:
            raise ValueError("Structured response parsing returned None.")
        return parsed.model_dump()

    except Exception as e:
        logging.error(f"Gemini API Inference Failure: {str(e)}")
        return {
            "summary": "Failed to compute insights via secure cloud provider channel.",
            "action_items": [],
            "suggested_title": title  # Fallback to keep data pipelines safe
        }