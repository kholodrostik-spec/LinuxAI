import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5-coder:7b")