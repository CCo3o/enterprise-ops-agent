"""HTTP API for the incident agent.

Run with: uvicorn app.api:app --reload
"""
from __future__ import annotations

from uuid import uuid4
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import analyze
from .llm import enabled as llm_enabled
from .store import add_message, add_trace, get_history

app = FastAPI(title="Enterprise Ops Agent", version="0.1.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"
DOCUMENTS_DIR = Path(__file__).resolve().parents[1] / "data" / "documents"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    trace_id: str
    latency_ms: int
    model_mode: str
    answer: dict
    history: list[dict[str, str]]


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": "enabled" if llm_enabled() else "offline-fallback"}


try:
    import multipart  # type: ignore
except ImportError:
    multipart = None


if multipart is not None:
    @app.post("/documents")
    async def upload_document(file: UploadFile = File(...)) -> dict[str, str]:
        """Store Markdown, text, or PDF content for subsequent RAG queries."""
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".md", ".txt", ".pdf"}:
            raise HTTPException(status_code=400, detail="只支持 .md、.txt 和 .pdf 文件")
        target = DOCUMENTS_DIR / Path(file.filename or "document").name
        content = await file.read()
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
                import io
                text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
            except ImportError as exc:
                raise HTTPException(status_code=500, detail="PDF 解析依赖未安装") from exc
            target = target.with_suffix(".md")
            target.write_text(f"# {target.stem}\n\n{text}", encoding="utf-8")
        else:
            target.write_bytes(content)
        return {"status": "ok", "filename": target.name, "message": "文档已加入知识库"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    started = perf_counter()
    session_id = request.session_id or str(uuid4())
    trace_id = str(uuid4())
    add_message(session_id, "user", request.message)
    history = get_history(session_id)
    # Keep user turns as context; feeding the previous answer back as a question
    # makes a deterministic agent repeat its conclusion.
    context = "\n".join(item["content"] for item in history if item["role"] == "user")
    result = analyze(context)
    answer = result.as_dict()
    add_message(session_id, "assistant", result.findings[0])
    history = get_history(session_id)
    latency_ms = round((perf_counter() - started) * 1000)
    mode = "model" if llm_enabled() else "offline-fallback"
    add_trace(trace_id, session_id, latency_ms, result.plan, mode)
    return ChatResponse(session_id=session_id, trace_id=trace_id, latency_ms=latency_ms, model_mode=mode, answer=answer, history=history)
