from app.sql_search import sql_search
from app.vector_search import vector_search


def build_rag_context(query: str) -> str:
    sql_results = sql_search(query)
    vector_results = vector_search(query)

    parts = []

    parts.append("=== SQL FACTS ===")

    for section, rows in sql_results.items():
        parts.append(f"\n[{section.upper()}]")

        if not rows:
            parts.append("No results.")
            continue

        for row in rows:
            parts.append(str(row))

    parts.append("\n=== VECTOR DOCUMENTS ===")

    if not vector_results:
        parts.append("No vector results.")
    else:
        for item in vector_results:
            parts.append(
                f"\nTitle: {item['title']}\n"
                f"Topic: {item['topic']}\n"
                f"Similarity: {item['similarity']:.4f}\n"
                f"Text: {item['text']}"
            )

    return "\n".join(parts)
