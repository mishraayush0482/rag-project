from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from app.auth.routes import router as auth_router
from app.chat.routes import router as chat_router

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

# The browser frontend is served separately during development, so allow it to
# call this API from the Vite/simple local server origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(whatsapp_router)

app.include_router(auth_router)

app.include_router(chat_router)

# Health check route
@app.get("/")
def home():
    return {
        "status": "running",
        "message": "Multilingual RAG Backend Live 🚀"
    }
