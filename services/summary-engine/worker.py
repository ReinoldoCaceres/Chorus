#!/usr/bin/env python3
"""
Celery worker startup script for Summary Engine
"""

from app.celery_app import celery_app
from app.utils.logging import configure_logging

if __name__ == "__main__":
    # Configure logging
    configure_logging()
    
    # Start Celery worker
    celery_app.start()