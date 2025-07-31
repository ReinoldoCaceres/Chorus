from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
import asyncio

from app.config import get_settings
from app.api.endpoints import router
from app.utils.logging import configure_logging
from app.models.database import Base
from app.db.database import engine
from app.background.tasks import BackgroundTaskManager

# Configure logging
configure_logging()
logger = structlog.get_logger()

settings = get_settings()

# Global background task manager
background_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    global background_manager
    
    # Startup
    logger.info("Starting Process Monitor API", version="1.0.0")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise
    
    # Start background tasks
    try:
        background_manager = BackgroundTaskManager()
        # Start background tasks in a separate task to avoid blocking startup
        asyncio.create_task(background_manager.start())
        logger.info("Background tasks started")
    except Exception as e:
        logger.error("Failed to start background tasks", error=str(e))
        # Don't fail startup if background tasks fail
    
    yield
    
    # Shutdown
    logger.info("Shutting down Process Monitor API")
    
    # Stop background tasks
    if background_manager:
        try:
            await background_manager.stop()
            logger.info("Background tasks stopped")
        except Exception as e:
            logger.error("Error stopping background tasks", error=str(e))


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix=settings.api_v1_str)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Process Monitor API",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "System metrics collection",
            "Process monitoring",
            "Service health checks",
            "Alert management",
            "Real-time monitoring dashboard"
        ]
    }


@app.get("/status")
async def status():
    """Extended status endpoint with system information"""
    import socket
    import psutil
    from datetime import datetime
    
    try:
        # Get basic system info
        hostname = socket.gethostname()
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        boot_time = psutil.boot_time()
        
        return {
            "service": "Process Monitor API",
            "version": "1.0.0",
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "hostname": hostname,
            "system": {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_mb": round(memory.available / (1024**2), 2),
                "uptime_hours": round((datetime.utcnow().timestamp() - boot_time) / 3600, 2)
            },
            "background_tasks": {
                "running": background_manager.running if background_manager else False,
                "task_count": len(background_manager.tasks) if background_manager else 0
            }
        }
    except Exception as e:
        logger.error("Error getting status", error=str(e))
        return {
            "service": "Process Monitor API",
            "version": "1.0.0",
            "status": "error",
            "timestamp": datetime.utcnow(),
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8082,
        reload=settings.debug,
        log_config=None  # We use structlog instead
    )