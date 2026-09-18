"""What counts as being in the trade, and the letter that was being deleted.

The scope gate decides whether a message is answered at all. It had its own copy
of the folding used everywhere else, and the copy normalised and stripped
combining marks but never mapped đ to d — while the tokeniser after it keeps only
[a-z0-9]. Every đ was therefore deleted rather than folded: "bị rò điện" arrived
as "bi ro ien" and "bóng đèn" as "bong en". A message about electricity or
lighting, two of the four things FixHome repairs, matched no trade word at all
and was refused as off-topic whenever it did not also name an appliance.

Found while working through the seven cases the 564-case suite reported as
wrongly refused.
"""

import pytest

from app.services.pipeline import device_hint
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm

KB = get_knowledge_base()


class _NoDetector:
    async def detect(self, image):
        return []


PIPELINE = LocalPipeline(
    detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(KB), kb=KB
)


@pytest.mark.parametrize(
    "text",
    [
        # Every one of these lost its đ and stopped matching anything.
        "bị rò điện",
        "nhà em mất điện",
        "bị điện giật nhẹ khi chạm vào",
        "đèn nhà em không sáng",
        "cần lắp đặt thêm ổ điện",
        "đường ống bị vỡ",
        "có vấn đề",
        "cho mình đặt lịch",
        "đặt thợ",
    ],
)
def test_electricity_and_lighting_are_in_the_trade(text):
    assert PIPELINE._is_in_the_trade(text), text


@pytest.mark.parametrize(
    "text",
    [
        "2 cộng 2 bằng mấy",
        "trời đẹp không",
        "thời tiết hôm nay thế nào",
        "giá bitcoin hôm nay",
        "kể chuyện cười đi em",
    ],
)
def test_what_is_off_topic_is_still_off_topic(text):
    """Widening the gate must not open it.

    The three comments in the source name the collisions that got through when
    this was substring-matched: "2 cộng 2 bằng mấy" on "ong ", "trời đẹp không"
    on "hong", "thời tiết" on "tho".
    """
    assert not PIPELINE._is_in_the_trade(text), text


@pytest.mark.parametrize(
    "text,expected",
    [
        # The smart lock had no alias for the way customers name it, so three
        # cases in the suite reached neither a device nor the trade.
        ("khoá cửa đặt tay mãi không mở được", "smart_lock"),
        ("khoá nhận vân rồi mà cửa vẫn không bật ra", "smart_lock"),
        ("khoá vân tay không nhận", "smart_lock"),
        # And the additions must not outrank a device named outright.
        ("máy giặt đèn báo lỗi", "washing_machine"),
    ],
)
def test_the_appliance_is_recognised_from_what_customers_call_it(text, expected):
    named = [hint.device_type for hint in device_hint.devices_named_in(text, KB)]
    assert named[:1] == [expected], (text, named)
