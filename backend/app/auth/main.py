from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import logging

try:
    from app.auth.database.db import engine, health_check
    from app.auth import models, schemas
    from app.auth.routers import auth
    from app.auth.core.config import settings
    from app.auth.core.logging_config import setup_logging
    from app.auth.core.security_headers import SecurityHeadersMiddleware
    from app.auth.core.request_id_middleware import RequestIDMiddleware
    from app.auth.core.error_handlers import register_error_handlers
except ModuleNotFoundError:
    from database.db import engine, health_check
    import models
    import schemas
    from routers import auth
    from core.config import settings
    from core.logging_config import setup_logging
    from core.security_headers import SecurityHeadersMiddleware
    from core.request_id_middleware import RequestIDMiddleware
    from core.error_handlers import register_error_handlers

# Setup logging
setup_logging(level=settings.LOG_LEVEL, json_format=settings.LOG_JSON_FORMAT)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("=== Application Starting ===")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug: {settings.DEBUG}")
    
    # Startup: Create tables
    models.Base.metadata.create_all(engine)
    logger.info("Database tables created/verified")
    
    # Check database connectivity
    if not health_check():
        logger.error("Cannot connect to database!")
        raise RuntimeError("Database connection failed at startup")
    logger.info("Database connection verified")
    
    yield
    
    # Shutdown
    logger.info("=== Application Shutting Down ===")
    logger.info("Closing database connections...")


# Initialize FastAPI app with lifespan
# In production, hide docs for security; in development, show at /docs
is_production = settings.ENVIRONMENT == "production"
app = FastAPI(
    title="Auth Service",
    description="Production-ready authentication API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if is_production else "/docs",
    openapi_url=None if is_production else "/openapi.json",
)

# Register error handlers
register_error_handlers(app)

# Add middleware (order matters - add from bottom to top)

# Security Headers (should be last - applied first in response)
app.add_middleware(SecurityHeadersMiddleware)

# Request ID middleware for tracing
app.add_middleware(RequestIDMiddleware)

# GZIP compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS with strict configuration
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
        max_age=3600,  # Cache preflight for 1 hour
    )
    logger.info(f"CORS enabled for: {settings.CORS_ORIGINS}")
else:
    logger.warning("⚠️ CORS disabled - no origins configured")


# Health check endpoint
@app.get("/health", response_model=schemas.HealthCheckResponse, tags=["health"])
async def health_check_endpoint(request: Request):
    """Health check endpoint for Kubernetes/load balancers."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    # Check database
    db_healthy = health_check()
    
    if not db_healthy:
        logger.error("Health check failed: Database unavailable")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    return schemas.HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
    )


# Ready endpoint (more thorough health check)
@app.get("/ready", response_model=schemas.HealthCheckResponse, tags=["health"])
async def readiness_endpoint(request: Request):
    """Readiness endpoint - checks if service is ready for traffic."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    # Check database
    if not health_check():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    return schemas.HealthCheckResponse(
        status="ready",
        timestamp=datetime.utcnow().isoformat(),
    )


# Include routers
app.include_router(auth.router)

# Root endpoint
@app.get("/", tags=["info"])
async def root():
    """API information endpoint."""
    return {
        "name": "Auth Service",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "auth": "/auth",
            "health": "/health",
            "ready": "/ready",
            "docs": "/auth/docs" if not settings.DEBUG else "/docs",
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run with production settings
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
        server_header=False,  # Don't expose server info
    )
