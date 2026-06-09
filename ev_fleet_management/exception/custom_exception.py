from fastapi import HTTPException, status

class EVFleetException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class AuthenticationError(EVFleetException):
    def __init__(self, detail: str = "Invalid credentials or unauthorized access"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED if hasattr(status, 'HTTP_401_UNAUTHORIZED') else 401,
            detail=detail
        )

class EntityNotFoundError(EVFleetException):
    def __init__(self, detail: str = "Requested entity not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND if hasattr(status, 'HTTP_404_NOT_FOUND') else 404,
            detail=detail
        )

class ValidationError(EVFleetException):
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST if hasattr(status, 'HTTP_400_BAD_REQUEST') else 400,
            detail=detail
        )
