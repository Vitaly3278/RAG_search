from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def _load_one_file(file_path: Path) -> list[Document]:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        docs = PyPDFLoader(str(file_path)).load()
    elif suffix == ".docx":
        docs = Docx2txtLoader(str(file_path)).load()
    elif suffix in {".txt", ".md"}:
        docs = TextLoader(str(file_path), encoding="utf-8").load()
    else:
        raise ValueError(f"Unsupported file type: {file_path.name}")

    for doc in docs:
        doc.metadata["source"] = file_path.name
    return docs


def load_documents(path: Path) -> list[Document]:
    if path.is_file():
        return _load_one_file(path)

    documents: list[Document] = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            documents.extend(_load_one_file(file_path))
    return documents
