# app/core/config.py
"""Application settings loaded from environment variables."""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Engine selection: "local" runs the self-hosted pipeline, "mock" is for CI.
    AI_ENGINE: str = "local"

    # Detector stage (YOLOv8n). Empty weights path falls back to the stub.
    YOLO_WEIGHTS_PATH: str = ""
    DETECTOR_CONFIDENCE_THRESHOLD: float = 0.45

    # Vision-language stage (Qwen2.5-VL via vLLM). Empty URL falls back to the stub.
    VLM_BASE_URL: str = ""
    VLM_MODEL_NAME: str = "Qwen/Qwen2.5-VL-3B-Instruct-AWQ"
    VLM_TIMEOUT_SECONDS: float = 8.0
    VLM_API_KEY: str = ""
    """Only needed if the vLLM endpoint was started with --api-key."""

    # Retrieval
    RETRIEVAL_TOP_K: int = 5
    POLICY_MIN_SCORE: float = 0.55
    """Below this a passage is treated as not covering the question.

    Lexical overlap gives every question some score, so without a floor the
    chatbot has retrieved 'evidence' for anything at all and the only thing
    standing between a customer and an invented answer is the model choosing to
    decline. Measured on the fixed question set, out-of-scope questions peak at
    0.50 and answerable ones sit at 0.43 and above, so 0.55 refuses all ten
    out-of-scope questions at the cost of two answerable ones. That trade is
    deliberate: a missing answer is a gap, a confident wrong one is a defect.
    """

    # Advisory behavior
    AI_CONFIDENCE_THRESHOLD: float = 0.6
    AI_DISCLAIMER_VI: str = (
        "Đây là gợi ý sơ bộ, kết luận cuối cùng thuộc về kỹ thuật viên kiểm tra trực tiếp."
    )
    NO_GROUNDING_MESSAGE_VI: str = (
        "Câu hỏi này nằm ngoài phạm vi tài liệu hiện có. "
        "Vui lòng liên hệ bộ phận hỗ trợ của FixHome."
    )
    CLARIFICATION_QUESTIONS_VI: List[str] = [
        "Thiết bị gặp sự cố là loại nào?",
        "Hiện tượng bắt đầu từ khi nào và xảy ra liên tục hay thỉnh thoảng?",
        "Thiết bị có phát ra tiếng động, mùi lạ hoặc rò rỉ gì không?",
    ]

    # Image intake. Images arrive inline from the client; the service never
    # fetches a URL on a caller's behalf, so there is no SSRF surface.
    IMAGE_MAX_BYTES: int = 8 * 1024 * 1024
    IMAGE_MAX_EDGE: int = 1024
    IMAGE_ALLOWED_MIME: List[str] = ["image/jpeg", "image/png", "image/webp"]
    MAX_IMAGES_PER_REQUEST: int = 3

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "info"

    # CORS: Backend is the only approved caller in deployment.
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
