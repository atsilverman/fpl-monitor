"""
FPL Monitor Backend Configuration
Production-ready configuration management
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Database Configuration
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    
    # FPL API Configuration
    fpl_api_url: str = "https://fantasy.premierleague.com/api"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Monitoring Configuration
    status_check_interval: int = 3600  # 1 hour
    price_check_interval: int = 300    # 5 minutes
    bonus_check_interval: int = 300    # 5 minutes
    
    # Push Notifications
    apns_bundle_id: str = os.getenv("APNS_BUNDLE_ID", "")
    apns_key_id: str = os.getenv("APNS_KEY_ID", "")
    apns_team_id: str = os.getenv("APNS_TEAM_ID", "")
    apns_key_path: str = os.getenv("APNS_KEY_PATH", "")
    
    # CORS Configuration
    allowed_origins: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
