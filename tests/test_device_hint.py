"""Device-from-text tests.

Two rules decide almost everything here. Believe the customer when they name
the device, because a sentence is unambiguous where a photograph is not. And
never ask about something already said, because that is what makes a support
bot feel like it is not listening.
"""

import pytest

from app.services.pipeline import device_hint
from app.services.pipeline.knowledge_base import get_knowledge_base

KB = get_knowledge_base()


# ------------------------------------------------------- reading the text

@pytest.mark.parametrize(
    "description,expected",
    [
        ("lò vi sóng nhà em không nóng", "microwave_oven"),
        ("cái lò nướng bị cháy đồ ăn", "oven"),
        ("máy lạnh không mát", "air_conditioner"),
        ("điều hoà chảy nước", "air_conditioner"),
        ("ổ cắm bị cháy khét", "power_outlet"),
        ("bóng đèn nhấp nháy", "light_bulb"),
        ("bình nóng lạnh không nóng", "water_heater"),
        ("quạt trần kêu to", "ceiling_fan"),
    ],
)
def test_a_named_device_is_recognised(description, expected):
    hits = device_hint.devices_named_in(description, KB)

    assert hits
    assert hits[0].device_type == expected


def test_recognised_without_diacritics():
    """Customers type without tone marks constantly."""
    hits = device_hint.devices_named_in("may giat khong vat", KB)

    assert hits
    assert hits[0].device_type == "washing_machine"


def test_nothing_named_returns_nothing():
    assert device_hint.devices_named_in("cái này hỏng rồi", KB) == []


def test_the_more_specific_alias_is_reported():
    """"máy giặt cửa trên" contains "máy giặt"; the longer match explains why."""
    hits = device_hint.devices_named_in("máy giặt cửa trên không vắt", KB)

    assert hits[0].matched_alias == "máy giặt cửa trên"


# ------------------------------------------------------- resolving

def test_text_and_photo_agreeing_keeps_the_device():
    device, hint = device_hint.resolve("lò vi sóng không nóng", "microwave_oven", KB)

    assert device == "microwave_oven"
    assert hint is not None


def test_text_wins_over_the_photo_for_a_confusable_pair():
    """The pair this exists for: a photo cannot settle microwave versus oven."""
    device, hint = device_hint.resolve("lò vi sóng không nóng", "oven", KB)

    assert device == "microwave_oven"
    assert hint is not None


def test_text_does_not_override_an_unrelated_detection():
    """A sentence mentioning a fridge in passing must not rewrite a socket photo."""
    device, hint = device_hint.resolve(
        "ổ cắm cạnh tủ lạnh bị cháy", "power_outlet", KB
    )

    assert device == "power_outlet"


def test_text_supplies_the_device_when_there_is_no_photo():
    device, hint = device_hint.resolve("bếp gas không lên lửa", None, KB)

    assert device == "gas_stove"
    assert hint is not None


def test_nothing_named_and_nothing_detected():
    assert device_hint.resolve("hỏng rồi", None, KB) == (None, None)


# ------------------------------------------------------- asking, sparingly

def test_a_confusable_detection_asks_about_something_the_customer_can_see():
    """Not "is it a microwave or an oven?".

    Someone who could answer that would not have needed the photograph
    diagnosed. The question has to be about a turntable, a wall mount, a thing
    in front of them — otherwise it hands the hard part back to the person who
    came for help.
    """
    question = device_hint.confusion_question("oven", "nướng không chín", KB)

    assert question is not None
    assert "đĩa" in question, question
    assert "Lò vi sóng" not in question, "asks them to name the category again"


def test_the_answer_settles_the_device():
    resolve = device_hint.resolve_confusion_answer
    assert resolve("có ạ", "oven", KB) == "microwave_oven"
    assert resolve("không có", "oven", KB) == "oven"
    assert resolve("dạ không", "oven", KB) == "oven"


def test_naming_the_device_outright_wins_over_the_yes_or_no():
    """"không phải lò nướng, là lò vi sóng" starts with a no and means yes."""
    settled = device_hint.resolve_confusion_answer(
        "không phải lò nướng đâu, lò vi sóng ạ", "oven", KB
    )
    assert settled == "microwave_oven"


def test_an_answer_about_where_the_fan_is_mounted_settles_it():
    resolve = device_hint.resolve_confusion_answer
    assert resolve("quạt gắn trên trần ạ", "electric_fan", KB) == "ceiling_fan"
    assert resolve("quạt cây đứng dưới sàn", "ceiling_fan", KB) == "electric_fan"


def test_an_answer_that_settles_nothing_returns_nothing():
    """Guessing from an unrelated reply is worse than asking again."""
    assert device_hint.resolve_confusion_answer("em không rõ lắm", "oven", KB) is None


def test_nothing_is_asked_when_the_customer_already_said():
    """The whole point: do not ask what was just written."""
    assert (
        device_hint.confusion_question("oven", "lò vi sóng của em không nóng", KB)
        is None
    )


def test_nothing_is_asked_for_a_device_with_no_confusable_sibling():
    assert device_hint.confusion_question("washing_machine", "không vắt", KB) is None


def test_nothing_is_asked_without_a_detection():
    assert device_hint.confusion_question(None, "hỏng rồi", KB) is None


@pytest.mark.parametrize("device", ["microwave_oven", "oven", "sink", "faucet"])
def test_confusion_is_symmetric(device):
    """One direction asking and the other staying silent would be a bug."""
    for sibling in KB.confusable_with(device):
        assert device in KB.confusable_with(sibling)


def test_not_knowing_is_not_a_no():
    """"Em không rõ lắm" carries a negative word and is not a negative answer.

    Reading it as one settles the appliance from an answer the customer never
    gave, and they would never see where it went wrong.
    """
    for reply in ["em không rõ lắm", "không biết nữa ạ", "em chưa rõ"]:
        assert device_hint.resolve_confusion_answer(reply, "oven", KB) is None, reply
