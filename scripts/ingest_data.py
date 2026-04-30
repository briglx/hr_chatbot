#!/usr/bin/env python3
"""Ingest HR documents (PDF, DOCX) into pgvector store.

Usage:
    python scripts/ingest_data.py --source ./data/hr-docs --format pdf,docx
"""

import argparse
import asyncio
import json
from pathlib import Path

import asyncpg
from docx import Document
from openai import AzureOpenAI
from pypdf import PdfReader

from app.config.settings import get_settings

settings = get_settings()

# ── Config ────────────────────────────────────────────────────────────────────

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

azure_client = AzureOpenAI(
    azure_endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
    api_version=settings.azure_openai_api_version,
)

# ── Text extraction ───────────────────────────────────────────────────────────


def extract_text_from_pdf(path: Path) -> str:
    """Extract text from a PDF file, concatenating the text of all pages with double newlines."""
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def extract_text_from_docx(path: Path) -> str:
    """Extract text from a DOCX file, concatenating non-empty paragraphs with double newlines."""
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


EXTRACTORS = {
    ".pdf": extract_text_from_pdf,
    ".docx": extract_text_from_docx,
}


# ── Chunking ──────────────────────────────────────────────────────────────────


def chunk_text(
    text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Split the input text into chunks of approximately `chunk_size` characters, with an `overlap` between chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if c]


# ── Embeddings ────────────────────────────────────────────────────────────────


def get_embedding(text: str) -> list[float]:
    """Get the embedding vector for the given text using Azure OpenAI."""
    response = azure_client.embeddings.create(
        model=settings.azure_openai_embedding_model,
        input=text.replace("\n", " "),
    )
    return response.data[0].embedding


# ── Database ──────────────────────────────────────────────────────────────────


async def get_connection():
    """Return an asyncpg connection using settings as the single source of truth."""
    return await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )


async def insert_document(conn, content: str, embedding: list[float], metadata: dict):
    """Insert a document chunk into the database with the given content, embedding, and metadata."""
    source = metadata.get("source", "unknown")
    print(f"    Inserting chunk from {source} (metadata: {metadata})...")

    await conn.execute(
        """
        INSERT INTO documents (content, source, embedding, metadata)
        VALUES ($1, $2, $3, $4)
        """,
        content,
        source,
        str(embedding),
        json.dumps(metadata),
    )


# def insert_document(conn, content: str, embedding: list[float], metadata: dict):
#     source = metadata.get("source", "unknown")  # fallback if source is missing in metadata
#     print(f"    Inserting chunk from {source} (metadata: {metadata})...")
#     with conn.cursor() as cur:
#         cur.execute(
#             """
#             INSERT INTO documents (content, source, embedding, metadata)
#             VALUES (%s, %s, %s::vector, %s)
#             """,
#             (content, source, embedding, json.dumps(metadata)),
#         )


# ── Main ingestion logic ──────────────────────────────────────────────────────


async def ingest_file(path: Path, conn) -> int:
    """Ingest a single file: extract text, chunk it, get embeddings, and insert into DB."""
    ext = path.suffix.lower()
    extractor = EXTRACTORS.get(ext)
    if extractor is None:
        print(f"  [skip] unsupported format: {path.name}")
        return 0

    print(f"  Reading {path.name}...")
    text = extractor(path)

    if not text.strip():
        print(f"  [warn] no text extracted from {path.name}")
        return 0

    chunks = chunk_text(text)
    print(f"  → {len(chunks)} chunks")

    async with conn.transaction():
        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            metadata = {
                "source": path.name,
                "file_type": ext.lstrip("."),
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            await insert_document(conn, chunk, embedding, metadata)

    return len(chunks)


async def ingest_directory(source: Path, formats: list[str], conn) -> None:
    """Ingest all files in the source directory that match the specified formats."""
    extensions = {f".{fmt.lower().strip('.')}" for fmt in formats}
    files = [
        f for f in source.iterdir() if f.is_file() and f.suffix.lower() in extensions
    ]

    if not files:
        print(f"No matching files found in {source} for formats: {formats}")
        return

    total_chunks = 0
    for file in sorted(files):
        print(f"\nIngesting: {file.name}")
        total_chunks += await ingest_file(file, conn)

    print(f"\n✓ Done. Inserted {total_chunks} chunks from {len(files)} file(s).")


def parse_args(args=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Ingest HR documents into pgvector.")
    parser.add_argument("--source", type=Path, required=True, help="source directory")
    parser.add_argument("--format", type=str, default="pdf,docx")
    return parser.parse_args(args)  # None means "read sys.argv", list means use that


async def main():
    """Main entry point for the script."""

    args = parse_args()

    # Validate required Azure env vars are set

    formats = [f.strip() for f in args.format.split(",")]

    if not args.source.is_dir():
        raise SystemExit(f"Error: source path '{args.source}' is not a directory.")

    print(
        f"Connecting to Postgres at {settings.postgres_host}:{settings.postgres_port}..."
    )
    conn = await get_connection()

    try:
        await ingest_directory(args.source, formats, conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
