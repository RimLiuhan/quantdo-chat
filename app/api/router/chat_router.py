from fastapi import APIRouter
from pydantic import BaseModel
from app.services.chat_agent import ask

chat_router = APIRouter()

class ExtractRequest(BaseModel):
    query: str


@chat_router.post("/chat")
async def chat(request: ExtractRequest):
    response = ask(request.query)
    return response
