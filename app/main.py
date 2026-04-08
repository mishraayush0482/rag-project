from fastapi import FastAPI
from app.services.rag_service import RAGService
from app.services.translation_service import TranslationService
from app.api.routes import router
from dotenv import load_dotenv
import os

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
app = FastAPI()

rag_service = RAGService()
translator = TranslationService()

@app.on_event("startup")
def startup():
    rag_service.initialize()

@app.on_event("shutdown")
def shutdown_event():
    print("Cleaning up resources...")

app.include_router(router)