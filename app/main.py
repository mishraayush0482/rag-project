from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

import os

# Disable tokenizer parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables
load_dotenv()

from app.services.rag_service import RAGService, set_rag_instance
from app.services.translation_service import TranslationService
from app.services.whatsapp_service import router as whatsapp_router

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Global service instances
rag_service = None
translator = None


@asynccontextmanager
async def lifespan(app: FastAPI):

    global rag_service
    global translator

    print("🚀 Starting application...")

    # Initialize translation service
    translator = TranslationService()

    # Initialize RAG service
    rag_service = RAGService()

    # Build / load vector DB
    rag_service.initialize()

    # Share instance globally
    set_rag_instance(rag_service)

    print("✅ Application started successfully")

    yield

    # Cleanup
    print("🛑 Shutting down application...")
    print("Cleaning up resources...")


# Create FastAPI app
app = FastAPI(
    title="Multilingual RAG WhatsApp Backend",
    version="1.0.0",
    lifespan=lifespan
)

# Register routes
app.include_router(whatsapp_router)


# Health check route
@app.get("/")
def home():
    return {
        "status": "running",
        "message": "Multilingual RAG Backend Live 🚀"
    }