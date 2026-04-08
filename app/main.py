from fastapi import FastAPI
from app.services.rag_service import RAGService, set_rag_instance
from app.services.translation_service import TranslationService
from app.services.whatsapp_service import router as whatsapp_router
from dotenv import load_dotenv
import os

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = FastAPI()

# ✅ include whatsapp route
app.include_router(whatsapp_router)

rag_service = RAGService()
translator = TranslationService()

@app.on_event("startup")
def startup():
    rag_service = RAGService()
    rag_service.initialize()
    set_rag_instance(rag_service)

@app.on_event("shutdown")
def shutdown_event():
    print("Cleaning up resources...")