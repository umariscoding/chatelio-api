import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path='app/.env')

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-pro-latest")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/embedding-001")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "chroma_db")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///chat_history.db")

# Subdomain configuration for public chatbots
BASE_DOMAIN = os.getenv("BASE_DOMAIN", "mysite.com")
CHATBOT_PROTOCOL = os.getenv("CHATBOT_PROTOCOL", "https")  # http for dev, https for prod
USE_SUBDOMAIN_ROUTING = os.getenv("USE_SUBDOMAIN_ROUTING", "true").lower() == "true"

def get_chatbot_url(slug: str) -> str:
    """
    Generate the public chatbot URL for a given company slug.
    
    Args:
        slug: Company slug
        
    Returns:
        str: Full chatbot URL
        
    Examples:
        - Development: http://kfcchatbot.localhost:8000
        - Production: https://kfcchatbot.mysite.com
    """
    if USE_SUBDOMAIN_ROUTING:
        return f"{CHATBOT_PROTOCOL}://{slug}.{BASE_DOMAIN}"
    else:
        # Fallback to path-based routing
        return f"{CHATBOT_PROTOCOL}://{BASE_DOMAIN}/public/chatbot/{slug}"