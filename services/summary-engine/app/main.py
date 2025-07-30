from fastapi import FastAPI
from contextlib import asynccontextmanager
import structlog

from app.config import get_settings
from app.api.endpoints import router
from app.utils.logging import configure_logging

# Configure logging
configure_logging()
logger = structlog.get_logger()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    # Startup
    logger.info("Starting Summary Engine Service", version="1.0.0")
    
    # Initialize services
    try:
        # Import here to ensure proper initialization order
        from app.services.vector_store import VectorStoreService
        from app.services.summary_service import SummaryService
        
        # Initialize services (this will create connections)
        vector_service = VectorStoreService()
        summary_service = SummaryService()
        
        logger.info("Services initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Summary Engine Service")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include routers
app.include_router(router, prefix=settings.api_v1_str)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Summary Engine",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.debug,
        log_config=None  # We use structlog instead
    )