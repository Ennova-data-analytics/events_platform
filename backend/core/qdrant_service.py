from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from core.config import settings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class QdrantService:
    """Singleton service for Qdrant"""
    _instance = None 

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialise()
        return cls._instance
    
    def _initialise(self):
        """Initialise Qdrant Client"""
        try:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                port=settings.QDRANT_PORT,
                timeout=30
            )
            self._ensure_collection_exists()
        except Exception as e:
            logger.error(f"Error while instantiating the qdrant service: {e}")
    
    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if settings.QDRANT_COLLECTION_NAME not in collection_names:
                self.client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
                )
                logger.info(f"Created Qdrant Collection: {settings.QDRANT_COLLECTION_NAME}")
        
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
    
    def get_client(self) -> QdrantClient:
        """Get the Qdrant client instance"""
        return self.client 

@lru_cache()
def get_qdrant_service() -> QdrantService:
    """Get the Qdrant Service singleton"""
    return QdrantService()