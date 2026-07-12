from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Annotated

try:
    from app.auth.core.validators import validate_secret_key
except ModuleNotFoundError:
    from core.validators import validate_secret_key


class Settings(BaseSettings):
    # Database Configuration
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    SQLALCHEMY_POOL_SIZE: int = 20
    SQLALCHEMY_MAX_OVERFLOW: int = 40
    SQLALCHEMY_POOL_PRE_PING: bool = True

    # JWT Configuration
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access tokens
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # Longer-lived refresh tokens
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_POOL_SIZE: int = 10

    # SMTP Configuration
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    EMAIL_FROM_ADDRESS: str
    EMAIL_FROM_NAME: str = "Auth Service"

    # Outlook SMTP (for routing emails to @outlook.com, @hotmail.com, @live.com, @msn.com)
    OUTLOOK_SMTP_HOST: str = "smtp-mail.outlook.com"
    OUTLOOK_SMTP_PORT: int = 587
    OUTLOOK_SMTP_USERNAME: str
    OUTLOOK_SMTP_PASSWORD: str
    OUTLOOK_EMAIL_FROM_ADDRESS: str
    OUTLOOK_EMAIL_FROM_NAME: str = "Auth Service"

    # Frontend/Backend URLs - MUST use HTTPS in production
    FRONTEND_URL: str
    BACKEND_URL: str
    
    # Security Settings
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    REQUIRE_HTTPS: bool = True
    
    # Rate Limiting
    RATE_LIMIT_LOGIN_ATTEMPTS: int = 3
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 900  # 15 minutes
    RATE_LIMIT_REGISTER_ATTEMPTS: int = 5
    RATE_LIMIT_REGISTER_WINDOW_SECONDS: int = 3600  # 1 hour
    RATE_LIMIT_PASSWORD_RESET_ATTEMPTS: int = 3
    RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS: int = 3600
    RATE_LIMIT_EMAIL_VERIFY_ATTEMPTS: int = 10
    RATE_LIMIT_EMAIL_VERIFY_WINDOW_SECONDS: int = 600  # 10 minutes
    
    # Account Security
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = True
    
    # Request Validation
    MAX_REQUEST_SIZE_MB: int = 10

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key_field(cls, v: str) -> str:
        """Validate SECRET_KEY has sufficient cryptographic strength."""
        return validate_secret_key(v)
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def validate_cors_origins(cls, v):
        """Ensure CORS origins are never wildcards in production."""
        if isinstance(v, str):
            v = [v]
        if "*" in v:
            raise ValueError("CORS wildcard '*' not allowed. Specify exact origins.")
        return v
    
    @field_validator('FRONTEND_URL', 'BACKEND_URL')
    @classmethod
    def validate_urls(cls, v: str, info) -> str:
        """Enforce HTTPS in production."""
        if info.data.get('ENVIRONMENT') == 'production':
            if not v.startswith('https://'):
                raise ValueError(f"{info.field_name} must use HTTPS in production")
        return v

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL from components."""
        password = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()