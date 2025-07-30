import redis
from app.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


class RedisClient:
    def __init__(self):
        self.client = None
        self.connect()
    
    def connect(self):
        """Create Redis connection"""
        try:
            self.client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self.client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    def get_client(self):
        """Get Redis client instance"""
        if not self.client:
            self.connect()
        return self.client


# Global Redis client instance
redis_client = RedisClient()


def get_redis():
    """Dependency to get Redis client"""
    return redis_client.get_client()