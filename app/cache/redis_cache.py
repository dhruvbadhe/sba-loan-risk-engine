import logging
from typing import Optional
import redis
from app.core.config import settings

logger = logging.getLogger("app")

class RedisCache:
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.connect()
    
    def connect(self):
        try:
            self.client = redis.from_url(settings.REDIS_URL, socket_connect_timeout = 2.0)
            self.client.ping()
            self.is_connected = True
            logger.info("Successfully connected to Redis cache")
        except Exception as e:
            self.client = None
            self.is_connected = False
            logger.warning("Redis is unavailable: {e}, Falling back yo no-cache mode.")

    def get(self, key: str) -> Optional[str]:
        if not self.is_connected or not self.client:
            return None

        try:
            val = self.client.get(key)
            return val.decode("utf-8") if val else None
        except Exception as e:
            logger.error(f"Error reading from redis: {e}")
            return None
    
    def set(self, key:str, value:str, expire_seconds: int = 3600) -> bool:
        if not self.is_connected or not self.client:
            return False
        
        try:
            self.client.set(key,value, ex = expire_seconds)
            return True
        except Exception as e:
            logger.error(f"Error writing to Redis: {e}")
            return False
    

cache = RedisCache()