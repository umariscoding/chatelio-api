import os

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-pro-latest")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/embedding-001")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "chroma_db")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///chat_history.db")