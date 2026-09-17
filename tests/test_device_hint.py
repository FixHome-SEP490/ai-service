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
    # Not the washing machine any more: a front-load washer and a front-load
    # dryer are the same photograph, so that pair now has a question of its own.
    assert device_hint.confusion_question("refrigerator", "không lạnh", KB) is None


def test_nothing_is_asked_without_a_detection():
    assert device_hint.confusion_question(None, "hỏng rồi", KB) is None


@pytest.mark.parametrize("device", sorted(KB.device_types))
def test_confusion_is_symmetric(device):
    """One direction asking and the other staying silent would be a bug.

    Every device in the catalogue, not a list written by hand. The hand-written
    list named four, was written before five more devices were added, and so
    never looked at any of them: the induction hob pointed at the gas stove and
    the gas stove pointed at nothing, which meant a photograph read as a gas
    stove never asked — and an induction hob got advice about gas valves and a
    leaking bottle.
    """
    for sibling in KB.confusable_with(device):
        assert device in KB.confusable_with(sibling), f"{sibling} does not point back"


@pytest.mark.parametrize("device", sorted(KB.device_types))
def test_a_device_that_asks_can_understand_the_answer(device):
    """Never ask a question whose answer cannot be read.

    `confusion_question` falls back to a generated "is it A or B" whenever no
    written question covers the device, but `resolve_confusion_answer` gives up
    immediately when there is no written question — so the dishwasher asked,
    the customer answered, and every reply resolved to None. A turn spent to
    learn nothing, and no way for the customer to see why.
    """
    if not KB.confusable_with(device):
        return
    written = KB.confusion_question(device)
    assert written is not None, f"{device} asks a question it cannot resolve"
    assert device in written.devices


@pytest.mark.parametrize("device", sorted(KB.device_types))
def test_a_device_understands_the_name_it_is_shown_under(device):
    """Whatever the answer prints, a customer can type back.

    The clarifying questions offer devices by their display name, so a reply
    that repeats the words the question just used has to land. "Quạt điện" was
    the name shown and not a name understood, which meant the fan question
    could be answered correctly in the customer's own words and still resolve
    to nothing.
    """
    name = KB.device_name_vi(device)
    got = [h.device_type for h in device_hint.devices_named_in(name, KB)]
    assert got[:1] == [device], f"{name!r} -> {got}"


@pytest.mark.parametrize("device", sorted(KB.device_types))
def test_every_sibling_can_be_reached_by_naming_it(device):
    """Saying the name of any offered device settles the question.

    This is the path a three-way question depends on entirely, since a bare yes
    or no cannot choose between three.
    """
    written = KB.confusion_question(device)
    if written is None:
        return
    for other in written.devices:
        name = KB.device_name_vi(other) or other
        got = device_hint.resolve_confusion_answer(name, device, KB)
        assert got == other, f"{device} asked, {name!r} answered, got {got}"


@pytest.mark.parametrize(
    "device,reply,expected",
    [
        ("ceiling_fan", "không phải trần đâu ạ", "electric_fan"),
        ("ceiling_fan", "nhà em không gắn trần", "electric_fan"),
        ("sink", "không phải chậu ạ", "faucet"),
        ("power_outlet", "không phải ổ cắm", "light_bulb"),
        ("induction_hob", "nhà em không dùng bình gas", "induction_hob"),
        ("gas_stove", "không có bình gas ạ", "induction_hob"),
    ],
)
def test_a_denial_answers_in_the_opposite_direction(device, reply, expected):
    """The reply mentions the thing asked about, to rule it out.

    Matching the word alone read every one of these as a confirmation, so the
    three commonest pairs in the catalogue — the fan, the sink and the socket —
    each resolved to exactly the wrong one of the two.
    """
    assert device_hint.resolve_confusion_answer(reply, device, KB) == expected


@pytest.mark.parametrize(
    "reply",
    ["em không rõ, chắc là quạt trần", "không biết nữa, hình như gắn trên trần"],
)
def test_not_being_sure_is_still_not_a_denial(reply):
    """"Không rõ" carries the same word a denial does and means the opposite.

    The customer is guessing, and the guess is the most informative thing in
    the sentence. Reading the "không" as a denial would have thrown it away and
    answered with the other device.
    """
    assert device_hint.resolve_confusion_answer(reply, "ceiling_fan", KB) == (
        "ceiling_fan"
    )


@pytest.mark.parametrize(
    "text,expected",
    [
        ("máy sấy quần áo nhà em không nóng", ["clothes_dryer"]),
        ("tủ sấy quần áo nhà em không nóng", []),
        ("máy sấy quần áo hỏng, máy sấy tóc thì vẫn chạy", ["clothes_dryer"]),
    ],
)
def test_a_disqualifier_wins_only_when_it_is_the_same_phrase(text, expected):
    """Length was the wrong signal for this and had to be replaced.

    "Tủ sấy quần áo" is a drying cabinet, and its alias match "sấy quần áo" is
    three words while the disqualifier "tủ sấy" is two — so the longer, more
    specific-looking phrase was the wrong one. What separates the cases is
    whether the two are built from the same words: in the cabinet they share
    "sấy", and in a sentence that mentions a hair dryer afterwards they do not.
    """
    got = [h.device_type for h in device_hint.devices_named_in(text, KB)]
    assert got == expected


def test_not_knowing_is_not_a_no():
    """"Em không rõ lắm" carries a negative word and is not a negative answer.

    Reading it as one settles the appliance from an answer the customer never
    gave, and they would never see where it went wrong.
    """
    for reply in ["em không rõ lắm", "không biết nữa ạ", "em chưa rõ"]:
        assert device_hint.resolve_confusion_answer(reply, "oven", KB) is None, reply
