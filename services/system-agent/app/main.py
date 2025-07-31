from fastapi import FastAPI
from contextlib import asynccontextmanager
import structlog

from app.config import get_settings
from app.api.endpoints import router
from app.utils.logging import configure_logging
from app.db.database import init_db, close_db

# Configure logging
configure_logging()
logger = structlog.get_logger()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    # Startup
    logger.info("Starting System Agent Service", version="1.0.0", port=8083)
    
    # Initialize services
    try:
        # Initialize database
        await init_db()
        
        # Import and initialize services (this will create connections)
        from app.services.task_service import TaskService
        from app.services.chat_service import ChatService
        from app.services.knowledge_service import KnowledgeService
        
        # Initialize services
        task_service = TaskService()
        chat_service = ChatService()
        knowledge_service = KnowledgeService()
        
        # Test ChromaDB connection
        _ = knowledge_service.collection
        
        logger.info("Services initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down System Agent Service")
    try:
        await close_db()
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    description="System Agent service with AI-powered chat, knowledge management, and task processing"
)

# Include routers
app.include_router(router, prefix=settings.api_v1_str)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "System Agent",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": f"{settings.api_v1_str}/health",
            "docs": "/docs",
            "tasks": f"{settings.api_v1_str}/tasks",
            "chat": f"{settings.api_v1_str}/chat",
            "knowledge": f"{settings.api_v1_str}/knowledge"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8083,
        reload=settings.debug,
        log_config=None  # We use structlog instead
    )