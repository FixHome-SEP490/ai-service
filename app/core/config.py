# app/core/config.py
"""Application settings loaded from environment variables."""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Engine selection: "local" runs the self-hosted pipeline, "mock" is for CI.
    AI_ENGINE: str = "local"

    # Detector stage (YOLO11s). Empty weights path falls back to the stub.
    YOLO_WEIGHTS_PATH: str = ""
    DETECTOR_CONFIDENCE_THRESHOLD: float = 0.45

    # Vision-language stage (Qwen2.5-VL via vLLM). Empty URL falls back to the stub.
    VLM_BASE_URL: str = ""
    VLM_MODEL_NAME: str = "Qwen/Qwen2.5-VL-3B-Instruct-AWQ"
    VLM_TIMEOUT_SECONDS: float = 8.0

    VLM_API_KEY: str = ""

    VLM_REPORT_VISIBLE_CONDITIONS: bool = False
    """Whether the damage the model claims to see is shown to the customer.

    Off, because it is not true yet. Shown a clean stock photograph of a
    refrigerator the model reported a crack, rust and a water leak; on a clean
    air conditioner, a crack and rust. Asked in the other direction — "có vết
    cháy đen không?" — it answered no, and asked to describe instead it said
    "một hình tròn màu đen", seeing the mark without naming it as damage.

    A wrong fault code is a wrong guess about something nobody can see. Telling
    a customer their refrigerator is cracked when the photo they just took shows
    it is not is a different kind of wrong: they can check, and they will.

    The fault codes are unaffected — they come from the customer's words against
    a retrieved shortlist, and those are reported as before. Turn this on once
    there are photographs of real damage to measure against."""
    """Only needed if the vLLM endpoint was started with --api-key."""

    # Retrieval
    RETRIEVAL_TOP_K: int = 5

    VLM_SHORTLIST_SIZE: int = 3
    """How many faults the model may choose between.

    Five let it reach past better answers. Shown a photograph of a television
    and "cái này bị sọc màn hình", it wrote in its own reason field "hình
    nghiêng về tấm nền hỏng" — the panel — and then chose the backlight and the
    remote control. The remote was ranked fourth at 0.25, behind the panel at
    0.46.

    Three costs nothing. Across the whole case suite the expected fault is at
    rank one in fifty-five cases and rank two in one; nothing correct has ever
    been at rank three, four or five, so the lower ranks were only ever a
    supply of wrong answers within reach.
    """
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

    CORPUS_TOP_K: int = 3
    """Written passages handed over per turn.

    Each is a `##` section, median 726 characters. Three of them is roughly two
    thousand characters of prose on top of the shortlist, the price rows and the
    conversation — enough to explain a mechanism or give the safety steps,
    without pushing the candidate faults out of a 3B model's attention."""

    CORPUS_MIN_SCORE: float = 0.80
    """BM25 score, over the question's own weight, that a passage needs.

    Not comparable to POLICY_MIN_SCORE: this one runs roughly 0 to 2.5 rather
    than 0 to 1, because BM25's term saturation lets a short dense section score
    above full coverage. Plain overlap does not work on this corpus at all — a
    726-character section of Vietnamese prose contains most common words, so
    every question scored 1.00 against every section of the right appliance and
    the ordering fell back to alphabetical.

    Measured on real questions, passages worth handing over sit between 1.0 and
    2.6. The floor is set below that band on purpose: it is there to catch
    genuine noise, not to decide relevance. Relevance is decided by requiring a
    non-empty fault shortlist, because no floor separated an off-topic question
    from a real one — see `Retriever.corpus_passages`."""

    # Advisory behavior
    PRICE_MIN_SCORE: float = 0.40
    """Overlap a price row needs before it counts as matching the question.

    Lower than the policy floor because a row is one short line rather than a
    paragraph, so a question shares much less of it. At the policy threshold
    every row scored below and "dây điện thay bên mình tính giá sao" came back
    as out of scope with the answer sitting in a loaded file."""

    RETRIEVAL_DECISIVE_SCORE: float = 0.9
    """Retrieval score above which the description already settles it.

    A score this high means the customer's own words matched the symptoms the
    team wrote for one fault almost exactly. Asking anything after that is
    asking them to repeat themselves."""

    GREETING_MESSAGE_VI: str = (
        "Dạ em chào anh/chị ạ. Nhà mình đang có thiết bị nào trục trặc không ạ? "
        "Anh/chị tả giúp em hiện tượng, có ảnh thì gửi kèm luôn ạ."
    )

    OUT_OF_SCOPE_MESSAGE_VI: str = (
        "Dạ em là trợ lý sửa chữa thiết bị gia dụng của FixHome nên chỉ hỗ trợ "
        "được các vấn đề về điện, nước và đồ gia dụng trong nhà thôi ạ. Nhà "
        "mình có thiết bị nào đang trục trặc không ạ?"
    )

    DEVICE_FROM_RETRIEVAL_SCORE: float = 0.5
    """Retrieval score at which the top match may name the appliance.

    Only used when nothing else knows it. Below this the ranking is noise and
    adopting its top entry would lock the conversation onto a device the
    customer never mentioned."""

    DECISIVE_MIN_WORDS: int = 3
    """Meaningful words the customer must have written before a high retrieval
    score counts as settling anything. "Hư rồi" is one."""

    MAX_CLARIFYING_TURNS: int = 2
    """How many turns may come back as questions before the service commits.

    Two, decided by the project owner. A third round is not diligence: the
    customer has told us what they can, and an estimate they can act on beats a
    fourth question they cannot answer. The technician settles it on site in
    either case."""

    AI_CONFIDENCE_THRESHOLD: float = 0.6
    AI_DISCLAIMER_VI: str = (
        "Đây là gợi ý sơ bộ, kết luận cuối cùng thuộc về kỹ thuật viên kiểm tra trực tiếp."
    )
    NO_GROUNDING_MESSAGE_VI: str = (
        "Dạ cái này bên em chưa có sẵn thông tin để trả lời chính xác cho anh/chị ạ. "
        "Anh/chị đặt lịch thì thợ sẽ gọi trước khi sang, mình hỏi thợ trực tiếp là rõ "
        "nhất. Hoặc nhà mình đang có thiết bị nào trục trặc thì tả giúp em nhé."
    )
    """Said when the question is inside the trade but nothing answers it.

    It used to read "vui lòng liên hệ bộ phận hỗ trợ của FixHome" — the
    assistant of a repair company handing its own customer to somebody else,
    for a question as ordinary as whether the technician wears a mask. There is
    no support desk at the other end of that sentence.

    What replaced it does the two things that are true: say plainly that this
    is not written down, and give the customer somewhere to go — the technician
    who will ring before the visit, or a description of whatever is broken."""
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
