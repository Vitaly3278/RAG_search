from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.config import settings
from app.document_loader import load_documents
from app.rag import ask_question, has_index, index_documents


app = FastAPI(title="Company Docs RAG")
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)
templates = Jinja2Templates(directory="web/templates")


class AskRequest(BaseModel):
    question: str


@app.get("/", response_class=HTMLResponse)
def web_home(request: Request) -> HTMLResponse:
    history = request.session.get("chat_history", [])
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "indexed": has_index(),
            "chat_history": history,
        },
    )


@app.post("/api/upload")
async def upload_docs(files: list[UploadFile] = File(...)) -> dict[str, object]:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        for file in files:
            target = temp_path / file.filename
            data = await file.read()
            target.write_bytes(data)

        documents = load_documents(temp_path)
        chunks = index_documents(documents)

    return {
        "indexed_chunks": chunks,
        "files": [f.filename for f in files],
    }


@app.post("/upload", response_class=HTMLResponse)
async def upload_docs_web(request: Request, files: list[UploadFile] = File(...)) -> HTMLResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        for file in files:
            target = temp_path / file.filename
            data = await file.read()
            target.write_bytes(data)

        documents = load_documents(temp_path)
        chunks = index_documents(documents)

    message = f"Загружено файлов: {len(files)}. Добавлено чанков: {chunks}."
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "indexed": has_index(),
            "upload_message": message,
            "chat_history": request.session.get("chat_history", []),
        },
    )


@app.post("/api/ask")
def ask_api(payload: AskRequest) -> dict[str, object]:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    return ask_question(question)


@app.post("/ask", response_class=HTMLResponse)
def ask_web(request: Request, question: str = Form(...)) -> HTMLResponse:
    normalized_question = question.strip()
    history = request.session.get("chat_history", [])
    result = ask_question(normalized_question, history=history)
    history.append({"user": normalized_question, "assistant": str(result["answer"])})
    request.session["chat_history"] = history[-10:]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "indexed": has_index(),
            "question": normalized_question,
            "answer": result["answer"],
            "sources": result["sources"],
            "chat_history": request.session.get("chat_history", []),
        },
    )


@app.post("/reset-chat", response_class=HTMLResponse)
def reset_chat(request: Request) -> HTMLResponse:
    request.session["chat_history"] = []
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "indexed": has_index(),
            "chat_history": [],
            "upload_message": "История диалога очищена.",
        },
    )
