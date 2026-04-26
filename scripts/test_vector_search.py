"""
scripts/test_vector_search.py
Tests semantic vector search against document_chunks.
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.db import get_connection
from app.embedding import embed_text

TEST_QUERIES = [
    "Ubuntu does not load NVIDIA driver after installation",
    "Wi-Fi not working after kernel update",
    "how to check which driver is used by the GPU",
]


def search(cur, query: str, limit: int = 5) -> list:
    query_embedding = embed_text(query)

    # Pass embedding once via CTE to avoid duplicate large parameter
    cur.execute(
        """
        WITH query_vec AS (
            SELECT %s::vector AS vec
        )
        SELECT
            dc.title,
            dc.topic,
            dc.chunk_text,
            1 - (dc.embedding <=> qv.vec) AS similarity
        FROM document_chunks dc, query_vec qv
        WHERE dc.embedding IS NOT NULL
          AND dc.is_active = TRUE
        ORDER BY dc.embedding <=> qv.vec
        LIMIT %s
        """,
        (query_embedding, limit),
    )
    return cur.fetchall()


def main() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                "SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL"
            )
            total = cur.fetchone()[0]
            print(f"Total chunks with embedding: {total}")
            print("=" * 80)

            if total == 0:
                print("No data found. Run ingest scripts first.")
                return

            for query in TEST_QUERIES:
                print(f"\nQuery: {query}")
                print("-" * 80)

                rows = search(cur, query)

                if not rows:
                    print("  No results found.")
                    continue

                for i, (title, topic, text, similarity) in enumerate(rows, 1):
                    print(f"  [{i}] {title}  (topic: {topic}, similarity: {similarity:.4f})")
                    preview = text[:200].replace("\n", " ")
                    print(f"      {preview}...")

    print("\nTest complete.")


if __name__ == "__main__":
    main()
