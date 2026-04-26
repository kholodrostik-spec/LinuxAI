import json
import hashlib
import time
from pathlib import Path
import sys

import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.db import get_connection
from app.embedding import embed_text

SOURCES_PATH = PROJECT_ROOT / "data" / "sources.json"

CHUNK_MIN = 300     # minimum characters per chunk
CHUNK_MAX = 1200    # maximum characters per chunk
REQUEST_DELAY = 1.5 # seconds between HTTP requests


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_text(url: str) -> str:
    """Fetch a web page and return its plain text content."""
    headers = {"User-Agent": "LinuxAI-Ingest/1.0 (research bot)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # Remove navigation, scripts, styles
    for tag in soup(["nav", "script", "style", "footer", "header"]):
        tag.decompose()

    return soup.get_text(separator="\n", strip=True)


def split_into_chunks(text: str) -> list[str]:
    """
    Split text into chunks of CHUNK_MIN–CHUNK_MAX characters.
    Splits on paragraph boundaries where possible.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= CHUNK_MAX:
            current = (current + "\n\n" + para).strip()
        else:
            if len(current) >= CHUNK_MIN:
                chunks.append(current)
            current = para

    if len(current) >= CHUNK_MIN:
        chunks.append(current)

    return chunks


def main() -> None:
    if not SOURCES_PATH.exists():
        print(f"No sources file found at {SOURCES_PATH}. Create it first.")
        return

    sources: list[dict] = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))

    if not sources:
        print("sources.json is empty. Add URLs to ingest.")
        return

    total_sources   = 0
    total_chunks    = 0
    skipped_chunks  = 0
    failed_sources  = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            for entry in sources:
                url    = entry.get("url", "").strip()
                title  = entry.get("title", url)
                stype  = entry.get("source_type", "web")
                topic  = entry.get("topic")
                trust  = entry.get("trust_level", "medium")

                if not url:
                    print(f"  [skip] Entry has no URL: {title}")
                    continue

                print(f"\nFetching: {title}")
                print(f"  URL: {url}")

                try:
                    raw_text = fetch_text(url)
                except Exception as exc:
                    print(f"  [error] Failed to fetch: {exc}")
                    failed_sources += 1
                    continue

                # Upsert source record
                cur.execute(
                    """
                    INSERT INTO sources
                        (title, url, source_type, topic, trust_level)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (title, source_type) DO UPDATE
                        SET url = EXCLUDED.url
                    RETURNING id
                    """,
                    (title, url, stype, topic, trust),
                )
                source_id = cur.fetchone()[0]
                total_sources += 1

                # Split and ingest chunks
                chunks = split_into_chunks(raw_text)
                print(f"  Chunks found: {len(chunks)}")

                for chunk_text in chunks:
                    chunk_hash = sha256(chunk_text)

                    cur.execute(
                        "SELECT id FROM document_chunks WHERE chunk_hash = %s",
                        (chunk_hash,),
                    )
                    if cur.fetchone():
                        skipped_chunks += 1
                        continue

                    embedding = embed_text(chunk_text)

                    cur.execute(
                        """
                        INSERT INTO document_chunks
                            (source_id, title, chunk_text, chunk_hash,
                             topic, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (chunk_hash) DO NOTHING
                        """,
                        (source_id, title, chunk_text, chunk_hash,
                         topic, embedding),
                    )
                    total_chunks += 1

                conn.commit()
                time.sleep(REQUEST_DELAY)

    print("\n" + "=" * 60)
    print("Ingestion complete.")
    print(f"  Sources processed: {total_sources}")
    print(f"  Chunks added:      {total_chunks}")
    print(f"  Chunks skipped:    {skipped_chunks}")
    print(f"  Sources failed:    {failed_sources}")


if __name__ == "__main__":
    main()
