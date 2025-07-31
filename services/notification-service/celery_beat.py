#!/usr/bin/env python3
"""
Celery beat scheduler entry point for the notification service
"""

import os
import sys

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.workers.notification_worker import celery_app

if __name__ == "__main__":
    celery_app.start(["beat", "--loglevel=info"])