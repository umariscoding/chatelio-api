import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router
from app.api.auth_endpoints import router as auth_router
from app.api.user_endpoints import router as user_router
from app.api.chat_endpoints import router as chat_router

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    logger.info(f"API hit: {request.method} {request.url.path}")
    response = await call_next(request)
    return response


# Include the routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(chat_router)
app.include_router(api_router)

# Add this line to make the app importable
main = app

# Run the app with uvicorn when this script is executed directly
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting the application")
    uvicorn.run("app.main:app", port=8081)