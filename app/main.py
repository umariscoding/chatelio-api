import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router
from app.api.auth_endpoints import router as auth_router
from app.api.user_endpoints import router as user_router
from app.api.chat_endpoints import router as chat_router
from app.api.public_endpoints import router as public_router

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable CORS with subdomain support
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # For development - will be more restrictive in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add subdomain detection middleware
@app.middleware("http")
async def subdomain_middleware(request: Request, call_next):
    """
    Middleware to detect and extract subdomain information from requests.
    Sets subdomain info in request.state for use by endpoints.
    
    Examples:
    - kfcchatbot.mysite.com → subdomain="kfcchatbot", is_subdomain_request=True
    - www.mysite.com → subdomain="www", is_subdomain_request=False  
    - mysite.com → subdomain=None, is_subdomain_request=False
    - localhost:8000 → subdomain=None, is_subdomain_request=False
    """
    host = request.headers.get("host", "").lower()
    
    # Extract subdomain
    if "." in host:
        parts = host.split(".")
        if len(parts) >= 3:  # subdomain.domain.tld
            subdomain = parts[0].split(":")[0]  # Remove port if present
        else:
            subdomain = None
    else:
        subdomain = None
    
    # Determine if this is a chatbot subdomain request
    is_subdomain_request = (
        subdomain is not None and 
        subdomain not in ["www", "api", "admin", "dashboard"] and
        len(subdomain) >= 3  # Minimum slug length
    )
    
    # Store in request state
    request.state.subdomain = subdomain
    request.state.is_subdomain_request = is_subdomain_request
    request.state.original_host = host
    
    # Log subdomain detection for debugging
    if is_subdomain_request:
        logger.info(f"Detected chatbot subdomain: {subdomain} from host: {host}")
    
    response = await call_next(request)
    return response

# Add middleware to log API hits
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log incoming API requests.

    Args:
        request (Request): The incoming request object.
        call_next: A function to call the next middleware or endpoint.

    Returns:
        Response: The response object after processing the request.
    """
    subdomain_info = f" [subdomain: {getattr(request.state, 'subdomain', 'none')}]" if hasattr(request.state, 'subdomain') else ""
    logger.info(f"API hit: {request.method} {request.url.path}{subdomain_info}")
    response = await call_next(request)
    return response

# Include the routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(chat_router)
app.include_router(public_router)
app.include_router(api_router)

# Add root health check
@app.get("/")
async def root():
    """Root endpoint for health checking and basic info."""
    return {
        "message": "Chatelio Multi-Tenant Chatbot API",
        "status": "healthy",
        "version": "1.0.0"
    }

# Add this line to make the app importable
main = app

# Run the app with uvicorn when this script is executed directly
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting the application")
    uvicorn.run("app.main:app", port=8081)