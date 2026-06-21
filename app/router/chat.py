import json
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from portfolio_model.workflow import generate_response

router = APIRouter(prefix="/chat", tags=["chat"])


def _validate_premium(username: str, password: str) -> bool:
    try:
        users = json.loads(os.environ.get("premium_users", "[]"))
        return any(u["username"] == username and u["password"] == password for u in users)
    except Exception:
        return False


class PremiumAuthRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    query: str
    session_id: str = "visitor"
    mode: str = "free"
    username: str = ""
    password: str = ""


@router.post("/verify-premium")
async def verify_premium(req: PremiumAuthRequest):
    return {"valid": _validate_premium(req.username, req.password)}


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    use_premium = req.mode == "premium"
    if use_premium and not _validate_premium(req.username, req.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials. Please use Free mode.",
        )

    async def event_generator():
        async for chunk in generate_response(
            query=req.query,
            session_id=req.session_id,
            use_premium=use_premium,
        ):
            if isinstance(chunk, dict) and chunk.get("done"):
                yield "data: [DONE]\n\n"
                return
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
