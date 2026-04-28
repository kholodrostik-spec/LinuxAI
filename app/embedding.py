import os
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODEL


os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


@lru_cache(maxsize=1)
def get_embedding_model():
    print(f"Loading embedding model from local cache: {EMBEDDING_MODEL}")

    return SentenceTransformer(
        EMBEDDING_MODEL,
        local_files_only=True
    )


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    return model.encode(text).tolist()
