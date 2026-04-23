from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


SYSTEM_PROMPT = """Ты помощник по внутренней документации компании.
Отвечай только на основе предоставленного контекста.
Если в контексте нет ответа, скажи: "Не нашёл в документации".
В конце дай список источников в формате:
- <файл>, стр. <номер_страницы_или_n/a>
"""


def _embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=settings.embedding_model_name)


def _vector_store() -> Chroma:
    settings.vector_db_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.collection_name,
        embedding_function=_embeddings(),
        persist_directory=str(settings.vector_db_dir),
    )


def _build_llm():
    provider = settings.llm_provider.strip().lower()
    if provider == "ollama":
        return ChatOllama(
            model=settings.ollama_model_name,
            base_url=settings.ollama_base_url,
            temperature=0,
        )
    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.openai_api_key or None,
        base_url=settings.openai_base_url,
        temperature=0,
    )


def split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    return splitter.split_documents(documents)


def index_documents(documents: list[Document]) -> int:
    chunks = split_documents(documents)
    if not chunks:
        return 0
    db = _vector_store()
    db.add_documents(chunks)
    db.persist()
    return len(chunks)


def _format_context(documents: list[Document]) -> str:
    sections: list[str] = []
    for idx, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "n/a")
        sections.append(
            f"[{idx}] source={source}; page={page}\n{doc.page_content.strip()}"
        )
    return "\n\n".join(sections)


def _format_sources(documents: list[Document]) -> list[dict[str, str]]:
    unique: dict[tuple[str, str], dict[str, str]] = {}
    for doc in documents:
        source = str(doc.metadata.get("source", "unknown"))
        page = str(doc.metadata.get("page", "n/a"))
        key = (source, page)
        unique[key] = {"source": source, "page": page}
    return list(unique.values())


def _format_history(history: list[dict[str, str]] | None) -> str:
    if not history:
        return ""
    lines: list[str] = []
    for item in history[-8:]:
        user_text = item.get("user", "").strip()
        bot_text = item.get("assistant", "").strip()
        if user_text:
            lines.append(f"Пользователь: {user_text}")
        if bot_text:
            lines.append(f"Ассистент: {bot_text}")
    return "\n".join(lines)


def ask_question(
    question: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    db = _vector_store()
    retriever = db.as_retriever(search_kwargs={"k": settings.top_k})
    docs = retriever.invoke(question)

    if not docs:
        return {
            "answer": "Не нашёл в документации.",
            "sources": [],
        }

    llm = _build_llm()
    context = _format_context(docs)
    history_text = _format_history(history)
    history_block = f"История диалога:\n{history_text}\n\n" if history_text else ""
    user_prompt = f"{history_block}Вопрос: {question}\n\nКонтекст:\n{context}"
    answer = llm.invoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    ).content

    return {
        "answer": str(answer),
        "sources": _format_sources(docs),
    }


def has_index(path: Path | None = None) -> bool:
    target = path or settings.vector_db_dir
    return target.exists() and any(target.iterdir())
