from fastapi import APIRouter, Form
from fastapi.responses import Response
from app.services.rag_service import query_rag

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    response_text = query_rag(Body, user_id=From)

    return Response(
        content=f"<Response><Message>{response_text}</Message></Response>",
        media_type="application/xml"
    )