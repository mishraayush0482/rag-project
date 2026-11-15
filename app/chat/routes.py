from fastapi import APIRouter, Depends
from app.models.chat import ChatRequest, ChatResponse
from app.auth.dependencies import get_current_user
from app.services.rag_service import query_rag

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, current_user=Depends(get_current_user)):
    """Run a RAG query in the authenticated user's conversation context."""
    user_id = str(current_user["_id"])

    answer = query_rag(
        text=request.message,
        user_id=user_id
    )

    return ChatResponse(answer=answer)
