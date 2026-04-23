import argparse
from pathlib import Path

from app.document_loader import load_documents
from app.rag import index_documents


def main() -> None:
    parser = argparse.ArgumentParser(description="Index company documents into Chroma.")
    parser.add_argument(
        "--path",
        type=str,
        default="data/docs",
        help="Path to a file or directory with documents.",
    )
    args = parser.parse_args()

    source_path = Path(args.path)
    if not source_path.exists():
        raise FileNotFoundError(f"Path not found: {source_path}")

    docs = load_documents(source_path)
    chunks_count = index_documents(docs)
    print(f"Indexed chunks: {chunks_count}")


if __name__ == "__main__":
    main()
