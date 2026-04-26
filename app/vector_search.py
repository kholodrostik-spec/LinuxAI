from app.db import get_connection
from app.embedding import embed_text


def vector_search(query: str, limit: int = 5) -> list[dict]:
    query_embedding = embed_text(query)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH query_vec AS (
                    SELECT %s::vector AS vec
                )
                SELECT
                    dc.id,
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
                (query_embedding, limit)
            )

            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
            "topic": row[2],
            "text": row[3],
            "similarity": float(row[4]),
        }
        for row in rows
    ]