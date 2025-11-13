"""
Application Settings and Configuration
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import List, Optional
import json


class Settings(BaseSettings):
    """Application settings"""
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # MongoDB settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "company_profiles_db"
    
    # CORS settings - stored as string, converted to list
    CORS_ORIGINS: Optional[str] = None
    
    # API settings
    API_V1_PREFIX: str = "/api/v1"
    
    # File settings
    UPLOAD_DIR: str = "../"
    ALLOWED_EXTENSIONS: List[str] = [".json"]
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # API Keys
    POLYGON_API_KEY: Optional[str] = None
    FINNHUB_API_KEY: Optional[str] = None
    
    # Proxy settings for rate limiting
    PROXY_SERVER: Optional[str] = None  # Single proxy (backward compatible)
    PROXY_SERVERS: Optional[str] = None  # Comma-separated list of proxies for rotation
    
    @model_validator(mode='after')
    def parse_cors_origins(self):
        """Parse CORS_ORIGINS from string to list"""
        if self.CORS_ORIGINS is None:
            # Default values
            self.CORS_ORIGINS = [
                "http://localhost:5173",
                "http://localhost:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:3000"
            ]
        elif isinstance(self.CORS_ORIGINS, str):
            # Try JSON first
            try:
                parsed = json.loads(self.CORS_ORIGINS)
                if isinstance(parsed, list):
                    self.CORS_ORIGINS = parsed
                else:
                    # If not a list, treat as comma-separated
                    self.CORS_ORIGINS = [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]
            except (json.JSONDecodeError, ValueError):
                # If not JSON, treat as comma-separated string
                self.CORS_ORIGINS = [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]
        # If it's already a list, keep it as is
        return self
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        return []
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
