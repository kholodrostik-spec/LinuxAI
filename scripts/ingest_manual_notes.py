import json
import hashlib
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.db import get_connection
from app.embedding import embed_text

NOTES_PATH = PROJECT_ROOT / "data" / "manual_notes.json"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    notes: list[dict] = json.loads(NOTES_PATH.read_text(encoding="utf-8"))

    inserted_sources = 0
    inserted_chunks  = 0
    skipped          = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            for note in notes:
                text       = note["text"].strip()
                title      = note["title"]
                topic      = note.get("topic")
                stype      = note.get("source_type", "manual_note")
                trust      = note.get("trust_level", "medium")
                chunk_hash = sha256(text)

                # Insert or find existing source
                cur.execute(
                    """
                    INSERT INTO sources
                        (title, source_type, topic, trust_level, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (title, source_type) DO NOTHING
                    RETURNING id
                    """,
                    (title, stype, topic, trust, "Inserted from manual_notes.json"),
                )
                row = cur.fetchone()

                if row:
                    source_id = row[0]
                    inserted_sources += 1
                else:
                    # Source already exists — fetch its id
                    cur.execute(
                        "SELECT id FROM sources WHERE title = %s AND source_type = %s",
                        (title, stype),
                    )
                    source_id = cur.fetchone()[0]

                # Skip if chunk already exists
                cur.execute(
                    "SELECT id FROM document_chunks WHERE chunk_hash = %s",
                    (chunk_hash,),
                )
                if cur.fetchone():
                    skipped += 1
                    continue

                # Build embedding and insert chunk
                embedding = embed_text(text)

                cur.execute(
                    """
                    INSERT INTO document_chunks
                        (source_id, title, chunk_text, chunk_hash,
                         topic, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_hash) DO NOTHING
                    """,
                    (source_id, title, text, chunk_hash, topic, embedding),
                )
                inserted_chunks += 1

        conn.commit()

    print("Manual notes ingested successfully.")
    print(f"  Sources added:          {inserted_sources}")
    print(f"  Chunks added:           {inserted_chunks}")
    print(f"  Chunks skipped (dupes): {skipped}")


if __name__ == "__main__":
    main()
