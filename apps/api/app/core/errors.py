"""표준 오류 응답 (LON-XXXX)."""
from fastapi import Request
from fastapi.responses import JSONResponse


class LonError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: dict | None = None):
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}
        super().__init__(message)


async def lon_exception_handler(_req: Request, exc: LonError):
    return JSONResponse(
        status_code=exc.status,
        content={
            "data": None,
            "error": {"code": exc.code, "message": exc.message, "details": exc.details},
            "traceId": "",
        },
    )
