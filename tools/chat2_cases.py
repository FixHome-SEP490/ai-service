"""Conversations the chat must get right, from what customers and the PO reported.

Each case is a transcript up to the turn being judged; the assistant turns are
written in, so every model under test answers the same question. Only the last
turn is scored. `expect` lists what is acceptable:

    decision   "ask" | "conclude" | "not_repair", or a tuple of them
    fault      fault code, "NONE", or a tuple of acceptable codes
    service    service code or a tuple of acceptable codes
    device     device_type passed in as if the detector had seen a photo
"""

from __future__ import annotations

from typing import Any, Dict, List

CASES: List[Dict[str, Any]] = [
    # PO 06/11, screenshots from fixhome.sbs
    {
        "id": "po-ac-dropped",
        "device": "air_conditioner",
        "turns": ["máy lạnh tôi bị rơt xuống đất"],
        "expect": {"decision": "conclude", "fault": "NONE", "service": ("AC-01", "AC-03")},
    },
    {
        "id": "po-ac-dropped-after-questions",
        "device": None,
        "turns": [
            "Điều hoà nhà tôi bị rơi xuống",
            "Dạ máy lạnh rơi từ trên tường xuống hẳn đất hay chỉ bị lệch khỏi giá ạ?",
            "Máy đã rơi hẳn xuống đất rồi",
        ],
        "expect": {"decision": "conclude", "fault": "NONE", "service": ("AC-01", "AC-03")},
    },
    {
        "id": "po-ac-foul-smell-dirty",
        "device": "air_conditioner",
        "turns": ["máy lạnh tôi có mùi hôi như thối tỏa ra , và tôi nhìn rất bẩn"],
        "expect": {"decision": "conclude", "fault": "AC_DIRTY_FILTER", "service": "AC-02"},
    },
    # BUG DETECTOR 52
    {
        "id": "bug52-fridge-clean",
        "device": None,
        "turns": ["tôi còn 1 tủ lạnh xuất hiện mùi hôi khó chịu cần thêm dịch vụ vệ sinh tủ lạnh"],
        "expect": {"decision": "conclude", "service": "FR-02"},
    },
    {
        "id": "fridge-smell-only",
        "device": "refrigerator",
        "turns": ["tủ lạnh nhà em có mùi hôi"],
        "expect": {"decision": "conclude", "service": "FR-02"},
    },
    # BUG DETECTOR 54: facts given earlier must survive short answers
    {
        "id": "bug54-turn2",
        "device": "air_conditioner",
        "turns": [
            "máy lạnh chảy nước và không lạnh",
            "Dạ máy lạnh nhà mình có được vệ sinh trong vòng ba tháng gần đây không ạ?",
            "Không.",
        ],
        "expect": {"decision": ("conclude", "ask"), "fault": ("AC_DIRTY_FILTER", "AC_DRAIN_BLOCKED", "AC_ICING")},
    },
    {
        "id": "bug54-turn4",
        "device": "air_conditioner",
        "turns": [
            "máy lạnh chảy nước và không lạnh",
            "Dạ máy lạnh nhà mình có được vệ sinh trong vòng ba tháng gần đây không ạ?",
            "Không.",
            "Dạ nước chảy ra ở chỗ nào của dàn lạnh ạ?",
            "Bên phải dàn lạnh.",
            "Dạ máy lạnh nhà mình khả năng bẩn dàn lạnh làm nghẹt đường thoát nước. Anh/chị nên đặt vệ sinh điều hòa ạ.",
            "Vậy giờ em thấy sao?",
        ],
        "expect": {"decision": "conclude", "fault": ("AC_DIRTY_FILTER", "AC_DRAIN_BLOCKED")},
    },
    # Short but enough: conclude at once
    {
        "id": "short-ac-leak",
        "device": "air_conditioner",
        "turns": ["máy lạnh chảy nước"],
        "expect": {"decision": "conclude", "fault": ("AC_DRAIN_BLOCKED", "AC_DIRTY_FILTER")},
    },
    {
        "id": "short-ac-burnt",
        "device": "air_conditioner",
        "turns": ["máy lạnh có mùi khét"],
        "expect": {"decision": "conclude", "fault": "AC_SMELL_BURNT"},
    },
    {
        "id": "short-wm-no-spin",
        "device": None,
        "turns": ["máy giặt không vắt được"],
        "expect": {"decision": "conclude", "service": "WM-01"},
    },
    {
        "id": "gas-smell",
        "device": None,
        "turns": ["bếp nhà em có mùi gas"],
        "expect": {"decision": "conclude", "service": "KT-07"},
    },
    # Vague: must ask, one question
    {
        "id": "vague-ac",
        "device": "air_conditioner",
        "turns": ["máy lạnh nhà em bị hư rồi"],
        "expect": {"decision": "ask"},
    },
    {
        "id": "vague-photo-only",
        "device": "washing_machine",
        "turns": ["em gửi ảnh, máy có vấn đề"],
        "expect": {"decision": "ask"},
    },
    # Asked twice already: must conclude
    {
        "id": "two-questions-then-conclude",
        "device": "air_conditioner",
        "turns": [
            "máy lạnh không mát",
            "Dạ cục nóng ngoài trời có chạy không ạ?",
            "có chạy",
            "Dạ máy lạnh có được vệ sinh trong vòng ba tháng gần đây không ạ?",
            "chưa rõ",
        ],
        "expect": {"decision": "conclude", "fault": ("AC_DIRTY_FILTER", "AC_LOW_REFRIGERANT")},
    },
    # Services asked for outright
    {
        "id": "svc-move-ac",
        "device": None,
        "turns": ["tháo máy lạnh chuyển sang nhà mới"],
        "expect": {"decision": "conclude", "service": "AC-04"},
    },
    {
        "id": "svc-tv-mount",
        "device": None,
        "turns": ["treo tivi lên tường giúp em"],
        "expect": {"decision": "conclude", "service": "TV-01"},
    },
    # Not a household repair
    {
        "id": "offtopic-weather",
        "device": None,
        "turns": ["hôm nay trời Sài Gòn có mưa không em"],
        "expect": {"decision": "not_repair"},
    },
]
