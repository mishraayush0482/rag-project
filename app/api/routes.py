from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse
from app.services.whatsapp_service import format_whatsapp_response

router = APIRouter()

@router.post("/webhook")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    from app.main import rag_service, translator

    user_id = From.replace("whatsapp:", "")

    try:
        
        lang = translator.detect_lang(Body)

        
        if lang == "en":
            
            eng_query = translator.hinglish_to_english(Body)
        else:
            eng_query = translator.translate(Body, lang, "en")

        
        answer = rag_service.query(eng_query, user_id=user_id)

        
        if lang != "en":
            answer = translator.translate(answer, "en", lang)

        return PlainTextResponse(format_whatsapp_response(answer))

    except Exception as e:
        print("Webhook error:", e)
        return PlainTextResponse(format_whatsapp_response("Error processing request"))