# src/utils/errors.py

class AppError(Exception):
    """
    Base class for all domain errors.
    Carries an HTTP status code and a detail message.
    """
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail, status_code=404)


class AccessDeniedError(AppError):
    def __init__(self, detail: str = "Access denied"):
        super().__init__(detail, status_code=403)


class ValidationError(AppError):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(detail, status_code=422)
