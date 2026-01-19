"""
Main FastAPI application entry point
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from functools import partial
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import router as pdf_router_v1
from src.api.routes import router_v2 as pdf_router_v2
from src.utils.pdf_generator import get_browser, generate_minimal_test_pdf

# Import the core module which configures logging automatically
from src.core import configure_logger

# Get logger
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources when the app starts and shuts down"""
    # Initialize browser on startup
    logger.info("Initializing Playwright browser...")
    try:
        await get_browser()
        logger.info("Browser initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize browser: {e}", exc_info=True)
    
    yield
    
    # Clean up on shutdown
    logger.info("Shutting down resources...")
    # Import inside the function to avoid circular imports
    from src.utils.pdf_generator import _browser, _playwright
    
    # Close the browser if it exists
    if _browser:
        try:
            await _browser.close()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {e}", exc_info=True)
    
    # Close playwright if it exists
    if _playwright:
        try:
            await _playwright.__aexit__(None, None, None)
            logger.info("Playwright closed successfully")
        except Exception as e:
            logger.error(f"Error closing playwright: {e}", exc_info=True)

# Create FastAPI app with lifespan context
app = FastAPI(
    title="PDF Generation API",
    description="API for generating PDFs from HTML or URLs",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for all domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pdf_router_v1)
app.include_router(pdf_router_v2)

# Root endpoint
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "PDF Generation API",
        "version": "2.0.0",
        "endpoints": [
            "/v1/pdf",
            "/v2/pdf"
        ]
    }

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    try:
        response = await generate_minimal_test_pdf()
        if response.status_code == 200:
            logger.info("Health check passed")
            return {"status": "healthy"}
        else:
            logger.warning(f"Health check failed with status code: {response.status_code}")
            raise HTTPException(status_code=500, detail="PDF service unhealthy")
    except Exception as e:
        # Log error with full traceback
        logger.error(f"Health check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="PDF service unhealthy")


@app.exception_handler(Exception)
async def handle_generic_exception(request: Request, exc: Exception):
    """Global exception handler to ensure all errors are properly logged with tracebacks"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "detail": str(exc)},
    )

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
