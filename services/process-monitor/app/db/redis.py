import redis
import json
from typing import Optional, Any
from app.config import get_settings

settings = get_settings()

# Redis client instance
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


class RedisCache:
    """Redis cache utility for metrics"""
    
    @staticmethod
    def set_metric(key: str, value: Any, expire: int = 300) -> bool:
        """Set a metric value in Redis with expiration"""
        try:
            return redis_client.setex(key, expire, json.dumps(value))
        except Exception:
            return False
    
    @staticmethod
    def get_metric(key: str) -> Optional[Any]:
        """Get a metric value from Redis"""
        try:
            value = redis_client.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None
    
    @staticmethod
    def publish_alert(channel: str, alert_data: dict) -> bool:
        """Publish alert to Redis channel"""
        try:
            redis_client.publish(channel, json.dumps(alert_data))
            return True
        except Exception:
            return False
    
    @staticmethod
    def set_system_health(hostname: str, health_data: dict, expire: int = 120) -> bool:
        """Store system health data in Redis"""
        key = f"health:{hostname}"
        try:
            return redis_client.setex(key, expire, json.dumps(health_data))
        except Exception:
            return False
    
    @staticmethod
    def get_system_health(hostname: str) -> Optional[dict]:
        """Get system health data from Redis"""
        key = f"health:{hostname}"
        try:
            value = redis_client.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None
    
    @staticmethod
    def get_all_system_health() -> dict:
        """Get health data for all systems"""
        try:
            keys = redis_client.keys("health:*")
            health_data = {}
            for key in keys:
                hostname = key.replace("health:", "")
                value = redis_client.get(key)
                if value:
                    health_data[hostname] = json.loads(value)
            return health_data
        except Exception:
            return {}