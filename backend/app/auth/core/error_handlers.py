"""Custom error handlers and exceptions."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging


logger = logging.getLogger(__name__)


class AuthAPIException(Exception):
    """Base exception for authentication API."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def register_error_handlers(app: FastAPI) -> None:
    """Register global error handlers."""
    
    @app.exception_handler(AuthAPIException)
    async def auth_exception_handler(request: Request, exc: AuthAPIException):
        """Handle custom auth exceptions."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        logger.error(
            f"AuthAPI error: {exc.message}",
            extra={'request_id': request_id, 'status_code': exc.status_code}
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.message,
                "request_id": request_id,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Format validation errors
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in error["loc"][1:]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(
            f"Validation error on {request.url.path}",
            extra={'request_id': request_id, 'errors': errors}
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": errors,
                "request_id": request_id
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected errors."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        logger.error(
            f"Unexpected error: {str(exc)}",
            extra={'request_id': request_id},
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "request_id": request_id
            }
        )
