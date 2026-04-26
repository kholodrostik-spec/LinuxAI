from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.sql_search import sql_search
from app.vector_search import vector_search


def main():
    query = "Ubuntu NVIDIA driver"

    print("=" * 80)
    print("SQL SEARCH")
    print("=" * 80)

    sql_results = sql_search(query)

    for section, rows in sql_results.items():
        print(f"\n{section.upper()}:")
        if not rows:
            print("  No results")
        for row in rows:
            print(" ", row)

    print("\n" + "=" * 80)
    print("VECTOR SEARCH")
    print("=" * 80)

    vector_results = vector_search(query)

    for item in vector_results:
        print(f"\nTitle: {item['title']}")
        print(f"Topic: {item['topic']}")
        print(f"Similarity: {item['similarity']:.4f}")
        print(f"Text: {item['text'][:250]}...")


if __name__ == "__main__":
    main()