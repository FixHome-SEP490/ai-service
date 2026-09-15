# app/core/exceptions.py
"""Service exceptions and the handler that converts them to safe responses.

Two rules shape this module. Clients get a stable error code they can branch on,
never provider text, stack traces or configuration detail. And every failure
still states that manual booking may proceed, because an AI outage must not
block a customer.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.schemas.diagnosis import AIErrorCode, DiagnosisErrorResponse


class AIServiceException(Exception):
    """Base exception carrying a stable code and a safe public message."""

    code: AIErrorCode = AIErrorCode.AI_UNAVAILABLE
    status_code: int = 503
    public_message: str = "Dịch vụ AI tạm thời không khả dụng."

    def __init__(self, internal_detail: str | None = None) -> None:
        self.internal_detail = internal_detail
        super().__init__(internal_detail or self.public_message)


class DetectorException(AIServiceException):
    code = AIErrorCode.DETECTOR_ERROR
    status_code = 503
    public_message = "Không phân tích được hình ảnh thiết bị."


class VlmException(AIServiceException):
    code = AIErrorCode.VLM_ERROR
    status_code = 503
    public_message = "Không hoàn tất được phân tích chẩn đoán."


class AITimeoutException(AIServiceException):
    code = AIErrorCode.AI_TIMEOUT
    status_code = 504
    public_message = "Phân tích AI vượt quá thời gian chờ."


class InvalidImageException(AIServiceException):
    code = AIErrorCode.INVALID_IMAGE
    status_code = 422
    public_message = "Ảnh không hợp lệ hoặc không thể sử dụng."


class UnsupportedImageException(AIServiceException):
    code = AIErrorCode.UNSUPPORTED_IMAGE
    status_code = 422
    public_message = "Định dạng ảnh không được hỗ trợ."


class ImageFetchException(AIServiceException):
    code = AIErrorCode.IMAGE_FETCH_FAILED
    status_code = 422
    public_message = "Không tải được ảnh từ địa chỉ đã cung cấp."


class KnowledgeBaseException(AIServiceException):
    code = AIErrorCode.KNOWLEDGE_BASE_ERROR
    status_code = 503
    public_message = "Không truy cập được bảng tri thức."


async def ai_exception_handler(request: Request, exc: AIServiceException) -> JSONResponse:
    """Render an AIServiceException without leaking internal detail.

    `exc.internal_detail` is intentionally dropped here; it belongs in logs.
    """
    body = DiagnosisErrorResponse(
        code=exc.code,
        message=exc.public_message,
        fallback_allowed=True,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(by_alias=True),
    )
