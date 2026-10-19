"""
AskGuruGranthSahib - PDF Ingestion Script
Parses the Sri Guru Granth Sahib PDF, splits it into chunks,
generates embeddings, and stores them in ChromaDB.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

# --- Configuration ---
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma_db")
COLLECTION_NAME = "guru_granth_sahib"

# Chunk settings tuned for scripture: smaller chunks preserve verse-level context
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract text from each page of the PDF.
    Returns a list of dicts with 'text', 'page_number', and 'ang' (page in SGGS).
    """
    print(f"📖 Reading PDF from: {pdf_path}")
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"   Total pages in PDF: {total_pages}")

    pages_data = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages_data.append({
                "text": text.strip(),
                "page_number": i + 1,
                "ang": i + 1,  # In SGGS, page number = Ang number
            })

        # Progress indicator
        if (i + 1) % 100 == 0 or (i + 1) == total_pages:
            print(f"   Extracted {i + 1}/{total_pages} pages...")

    print(f"✅ Successfully extracted text from {len(pages_data)} pages")
    return pages_data


def chunk_documents(pages_data: list[dict]) -> tuple[list[str], list[dict]]:
    """
    Split extracted page texts into overlapping chunks for embedding.
    Returns (texts, metadatas) ready for ChromaDB ingestion.
    """
    print(f"\n✂️  Splitting text into chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", "।", "॥", ". ", " ", ""],
    )

    all_texts = []
    all_metadatas = []

    for page_data in pages_data:
        chunks = splitter.split_text(page_data["text"])
        for j, chunk in enumerate(chunks):
            all_texts.append(chunk)
            all_metadatas.append({
                "source": "Sri Guru Granth Sahib Ji",
                "ang": page_data["ang"],
                "page_number": page_data["page_number"],
                "chunk_index": j,
            })

    print(f"✅ Created {len(all_texts)} chunks from {len(pages_data)} pages")
    return all_texts, all_metadatas


def ingest_into_chromadb(texts: list[str], metadatas: list[dict]):
    """
    Generate OpenAI embeddings and store chunks in ChromaDB.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found in environment variables.")
        print("   Create a .env file with: OPENAI_API_KEY=your-key-here")
        sys.exit(1)

    print(f"\n🧠 Generating embeddings and storing in ChromaDB...")
    print(f"   Persist directory: {CHROMA_PERSIST_DIR}")

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=api_key,
    )

    # Process in batches to avoid rate limits and show progress
    batch_size = 100
    total_batches = (len(texts) + batch_size - 1) // batch_size

    # Create or overwrite the vector store
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

    vectorstore = None
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_metadatas = metadatas[i : i + batch_size]
        batch_num = (i // batch_size) + 1

        if vectorstore is None:
            vectorstore = Chroma.from_texts(
                texts=batch_texts,
                metadatas=batch_metadatas,
                embedding=embeddings,
                persist_directory=CHROMA_PERSIST_DIR,
                collection_name=COLLECTION_NAME,
            )
        else:
            vectorstore.add_texts(
                texts=batch_texts,
                metadatas=batch_metadatas,
            )

        print(f"   Batch {batch_num}/{total_batches} ingested ({min(i + batch_size, len(texts))}/{len(texts)} chunks)")

        # Small delay to respect rate limits
        if batch_num < total_batches:
            time.sleep(0.5)

    print(f"\n🎉 Ingestion complete! {len(texts)} chunks stored in ChromaDB.")
    print(f"   Collection: {COLLECTION_NAME}")
    print(f"   Location: {CHROMA_PERSIST_DIR}")
    return vectorstore


def main():
    """Main ingestion pipeline."""
    print("=" * 60)
    print("  AskGuruGranthSahib — Knowledge Base Ingestion")
    print("=" * 60)

    # Configure UTF-8 stdout if possible on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Check for PDF path
    if len(sys.argv) >= 2:
        pdf_path = sys.argv[1]
    else:
        # Search common project locations
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "HolyScripture", "Siri Guru Granth - English Translation (matching pages).pdf"),
            os.path.join(os.path.dirname(__file__), "data", "sggs.pdf"),
        ]
        
        # Check HolyScripture folder for any PDF
        scripture_dir = os.path.join(os.path.dirname(__file__), "..", "HolyScripture")
        if os.path.isdir(scripture_dir):
            for file in os.listdir(scripture_dir):
                if file.lower().endswith(".pdf"):
                    possible_paths.insert(0, os.path.join(scripture_dir, file))

        pdf_path = None
        for candidate in possible_paths:
            if os.path.exists(candidate):
                pdf_path = os.path.abspath(candidate)
                break

    if not pdf_path or not os.path.exists(pdf_path):
        print(f"\n❌ PDF not found!")
        print("   Usage: python ingest.py <path-to-sggs-pdf>")
        print("   Or place the PDF in the HolyScripture/ or backend/data/ folder.")
        sys.exit(1)

    # Validate API Key before doing heavy extraction
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "your-openai-api-key-here":
        print("\n⚠️  OPENAI_API_KEY is not configured yet in backend/.env!")
        print("   Please add your real OpenAI API key to:")
        print("   backend/.env -> OPENAI_API_KEY=sk-...")
        print("   Embeddings generation requires this key.")
        return

    start_time = time.time()

    # Step 1: Extract text
    pages_data = extract_text_from_pdf(pdf_path)

    # Step 2: Chunk the text
    texts, metadatas = chunk_documents(pages_data)

    # Step 3: Ingest into ChromaDB
    ingest_into_chromadb(texts, metadatas)

    elapsed = time.time() - start_time
    print(f"\n⏱️  Total time: {elapsed:.1f} seconds")
    print("=" * 60)


if __name__ == "__main__":
    main()
