from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    return SentenceTransformer(EMBEDDING_MODEL)


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    return model.encode(text, normalize_embeddings=True).tolist()
