import redis
import threading
from app.core.config import settings


class RedisManager:
    _instance = None
    _lock = threading.Lock()  # Thread-safe olmasını sağlamak için lock mekanizması

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Çift kontrol (Double-checked locking pattern)
                if cls._instance is None:
                    cls._instance = super(RedisManager, cls).__new__(cls)
                    cls._instance.client = redis.from_url(
                        settings.REDIS_URL,
                        decode_responses=True,
                        # Production için en iyi pratikler:
                        max_connections=20,
                        socket_timeout=5.0,
                    )
        return cls._instance

    @property
    def redis(self):
        return self.client


# Dosya import edildiğinde tek bir instance hazır olur
redis_manager = RedisManager()
