from fastapi import APIRouter
from typing import List
from apps.api.schemas import ChatRequest, ChatResponse, ChatMessage, FeedbackRequest, Citation

router = APIRouter()

@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    return ChatResponse(
        response_text="working",
        citations=[],
        confidence_score=1.0
    )

@router.get("/history/{session_id}", response_model=List[ChatMessage])
async def get_history(session_id: str):
    return [
        ChatMessage(role="system", content="working", timestamp="2024-01-01T00:00:00Z")
    ]

@router.post("/feedback/{message_id}")
async def submit_feedback(message_id: str, request: FeedbackRequest):
    return {"status": "working", "message": "Feedback received"}
