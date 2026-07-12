"""Request ID middleware for distributed tracing."""

import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders
import logging


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to all requests for tracing."""
    
    async def dispatch(self, request: Request, call_next):
        # Get request ID from header or generate new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Store in request state for access in handlers
        request.state.request_id = request_id
        request.state.client_host = request.client.host if request.client else "unknown"
        
        # Create response
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        # Log request details
        logger = logging.getLogger("request")
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'ip': request.state.client_host
            }
        )
        
        return response
