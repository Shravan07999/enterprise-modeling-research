import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

root_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(root_env_path)

if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_key_here":
    print("Error: OPENAI_API_KEY is missing or invalid in .env file.")
    sys.exit(1)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHROMA_DB_PATH = str(Path(__file__).resolve().parent.parent / "chroma_db")
COLLECTION_NAME = "hyde_collection"


def main():
    parser = argparse.ArgumentParser(description="Ingest PDFs into ChromaDB.")
    parser.add_argument(
        "--framework",
        type=str,
        default=None,
        help="Optional framework identifier (TOGAF, Zachman, 4EM, BPMN)",
    )
    args = parser.parse_args()

    pdf_files = list(DATA_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"Error: no PDFs found in {DATA_DIR}", file=sys.stderr)
        sys.exit(1)

    docs = []
    for pdf_path in pdf_files:
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        for page in pages:
            page.metadata["source_book"] = pdf_path.stem
        docs.extend(pages)

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    if args.framework:
        for chunk in chunks:
            chunk.metadata["framework"] = args.framework

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DB_PATH,
    )

    tag_info = f" [framework={args.framework}]" if args.framework else ""
    print(f"Ingested {len(chunks)} chunks from {len(pdf_files)} PDF(s) into {COLLECTION_NAME}{tag_info}")


if __name__ == "__main__":
    main()
