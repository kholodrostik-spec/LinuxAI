from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.rag_context import build_rag_context


def main():
    query = "Ubuntu NVIDIA RTX 4050 driver not working"
    context = build_rag_context(query)

    print(context)


if __name__ == "__main__":
    main()
