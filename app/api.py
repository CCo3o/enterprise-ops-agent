"""HTTP API for the incident agent.

Run with: uvicorn app.api:app --reload
"""
from __future__ import annotations

from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import analyze

app = FastAPI(title="Enterprise Ops Agent", version="0.1.0")
sessions: dict[str, list[dict[str, str]]] = {}
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: dict
    history: list[dict[str, str]]


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid4())
    history = sessions.setdefault(session_id, [])
    history.append({"role": "user", "content": request.message})
    # Keep user turns as context; feeding the previous answer back as a question
    # makes a deterministic agent repeat its conclusion.
    context = "\n".join(item["content"] for item in history if item["role"] == "user")
    result = analyze(context)
    answer = result.as_dict()
    history.append({"role": "assistant", "content": result.findings[0]})
    return ChatResponse(session_id=session_id, answer=answer, history=history)
