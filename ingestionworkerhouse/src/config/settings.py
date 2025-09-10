"""Configuration management for the House PTR Ingestion Worker."""

import os
from typing import List, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application configuration settings."""
    
    # Discovery settings
    HOUSE_YEAR_WINDOW: str = os.getenv("HOUSE_YEAR_WINDOW", "2023-2025")
    SCAN_INTERVAL_MIN: int = int(os.getenv("SCAN_INTERVAL_MIN", "15"))
    
    # Performance settings
    MAX_CONCURRENCY: int = int(os.getenv("MAX_CONCURRENCY", "5"))
    THROTTLE_MS: int = int(os.getenv("THROTTLE_MS", "1000"))
    
    # Database connection
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Storage settings
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "ptr-archive")
    
    # Request settings
    USER_AGENT: str = os.getenv("USER_AGENT", "TradeSpotter-PTR-Worker/1.0")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Retry settings
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_BACKOFF_FACTOR: float = float(os.getenv("RETRY_BACKOFF_FACTOR", "2"))
    
    # Health check
    HEALTH_CHECK_PORT: int = int(os.getenv("HEALTH_CHECK_PORT", "8080"))
    
    @classmethod
    def get_year_range(cls) -> Tuple[int, int]:
        """Parse year window into start and end years."""
        try:
            start_year, end_year = cls.HOUSE_YEAR_WINDOW.split("-")
            return int(start_year), int(end_year)
        except (ValueError, AttributeError):
            # Default to current year if parsing fails
            from datetime import datetime
            current_year = datetime.now().year
            return current_year, current_year
    
    @classmethod
    def validate_required_settings(cls) -> List[str]:
        """Validate that required settings are present."""
        missing = []
        
        if not cls.SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not cls.SUPABASE_SERVICE_ROLE_KEY:
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
            
        return missing


# Global settings instance
settings = Settings()
