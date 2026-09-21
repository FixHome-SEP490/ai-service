"""Every way a customer names, or changes, the trade they want.

The booking button is pinned to the bottom of the chat, so the sentence that
changes it is the sentence that decides what gets ordered. That makes this the
widest surface in the service and the one with the least room to be wrong.

Every case here is run twice, once as written and once with the diacritics
stripped, because a phone keyboard set to English is the ordinary way Vietnamese
gets typed. That costs nothing to assert and doubles what the file covers: the
pipeline folds diacritics before matching, so the two should never disagree, and
a case where they do is a real defect rather than a typo in a fixture.

What has already gone wrong here, and is pinned below so it cannot return:

    the remembered appliance beat the sentence that replaced it, so every way
    of asking to switch came back with the service being moved away from

    refusals were read as always coming second - "A thay vì B" - so the half
    that put them first, "bỏ máy lạnh đi, đặt tủ lạnh", changed nothing

    the appliance after a refusal was resolved by reading the whole rest of the
    sentence, which named two appliances and therefore gave up

    adding `quạt` to both fans made "quạt trần" match two and resolve to
    nothing: breadth bought one phrase and cost several that worked

    `cống` folds to `cong` and collides with `công tắc`; `đèn` folds to `den`
    and collides with `đến`. Both are multi-word here for that reason, and this
    is the fifth and sixth time that family of bug has been found in this repo.
"""

import unicodedata

import pytest

from app.services.pipeline import local_pipeline as lp
from app.services.pipeline.knowledge_base import get_knowledge_base


@pytest.fixture(scope="module")
def kb():
    return get_knowledge_base()


def without_diacritics(text: str) -> str:
    """What the same sentence looks like typed on an English keyboard."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return stripped.replace("đ", "d").replace("Đ", "D")


def both_spellings(cases):
    """Each case as written and again with the tone marks gone."""
    for sentence, expected in cases:
        yield pytest.param(sentence, expected, id=f"co-dau: {sentence}")
        yield pytest.param(
            without_diacritics(sentence), expected, id=f"khong-dau: {sentence}"
        )


# ---------------------------------------------------------------------------
# Naming the trade in the first place
# ---------------------------------------------------------------------------

NAMING_A_TRADE = [
    # the plain imperative
    ("đặt cho tôi thợ sửa ống nước", "water_pipe"),
    ("đặt cho anh thợ điện", "power_outlet"),
    ("đặt thợ sửa bếp ga", "gas_stove"),
    ("đặt thợ sửa tivi", "television"),
    ("đặt thợ sửa khóa cửa", "smart_lock"),
    ("đặt thợ sửa máy sấy quần áo", "clothes_dryer"),
    ("đặt thợ vệ sinh máy lạnh", "air_conditioner"),
    ("đặt thợ sửa lò nướng", "oven"),
    # asking rather than telling
    ("anh muốn đặt thợ sửa điều hòa", "air_conditioner"),
    ("anh muốn thợ sửa lò vi sóng", "microwave_oven"),
    ("tôi muốn thợ sửa ổ cắm", "power_outlet"),
    ("em muốn đặt thợ sửa máy lọc nước", "water_purifier"),
    ("mình muốn đặt thợ sửa ấm siêu tốc", "kettle"),
    # "cho tôi", which carries no verb of ordering at all
    ("cho tôi thợ sửa máy giặt", "washing_machine"),
    ("cho em thợ sửa máy lọc nước", "water_purifier"),
    ("cho tôi thợ sửa máy rửa chén", "dishwasher"),
    ("cho em xin thợ sửa bồn rửa", "sink"),
    # asking someone to find one
    ("gọi giúp tôi thợ sửa tủ lạnh", "refrigerator"),
    ("tìm giúp tôi thợ lắp đèn", "light_bulb"),
    ("kiếm cho em thợ sửa máy nước nóng", "water_heater"),
    ("lấy cho tôi thợ sửa bình nóng lạnh", "water_heater"),
    ("nhờ em tìm thợ sửa vòi nước", "faucet"),
    # the loanword, which needs no object
    ("book thợ sửa quạt trần", "ceiling_fan"),
    ("book giúp em thợ sửa bếp từ", "induction_hob"),
    # stating a need
    ("tôi cần thợ thông cống", "water_pipe"),
    ("cần thợ thông tắc bồn cầu", "toilet"),
    ("cần thợ sửa bếp từ", "induction_hob"),
    ("nhà em cần thợ sửa quạt cây", "electric_fan"),
    # wording that starts by dismissing something else
    ("thôi đặt thợ sửa bồn cầu", "toilet"),
    ("thay công tắc điện", "power_outlet"),
]


@pytest.mark.parametrize("sentence,expected", list(both_spellings(NAMING_A_TRADE)))
def test_the_trade_the_customer_named_is_the_one_resolved(kb, sentence, expected):
    assert lp._device_asked_for_now(sentence, kb) == expected


# ---------------------------------------------------------------------------
# Changing their mind, which is the case the pinned button exists for
# ---------------------------------------------------------------------------

# All of these are said by somebody whose session already has an air
# conditioner in it, and all of them mean the fridge.
CHANGING_TO_A_FRIDGE = [
    # naming the new one after an explicit switch
    ("đổi sang thợ sửa tủ lạnh", "refrigerator"),
    ("chuyển sang thợ sửa tủ lạnh", "refrigerator"),
    ("đổi qua tủ lạnh giúp em", "refrigerator"),
    ("chuyển qua tủ lạnh đi", "refrigerator"),
    ("đổi thành thợ tủ lạnh", "refrigerator"),
    ("cho em đổi sang tủ lạnh", "refrigerator"),
    ("đổi lại thành tủ lạnh", "refrigerator"),
    # switching without the word "đổi"
    ("thôi đổi tủ lạnh nhé", "refrigerator"),
    ("em muốn đổi tủ lạnh", "refrigerator"),
    ("thay vào đó đặt thợ tủ lạnh", "refrigerator"),
    ("cho em xin thợ tủ lạnh", "refrigerator"),
    # refusing the old one first, then naming the new one
    ("thôi không máy lạnh nữa, tủ lạnh đi", "refrigerator"),
    ("bỏ máy lạnh đi, đặt tủ lạnh", "refrigerator"),
    ("không phải máy lạnh đâu, tủ lạnh", "refrigerator"),
    ("huỷ máy lạnh, đặt tủ lạnh giúp em", "refrigerator"),
    ("không lấy máy lạnh nữa, lấy tủ lạnh", "refrigerator"),
    ("không cần máy lạnh, cần tủ lạnh", "refrigerator"),
    ("đừng đặt máy lạnh, đặt tủ lạnh nhé", "refrigerator"),
    # naming the new one first, then refusing the old
    ("sửa tủ lạnh chứ không phải máy lạnh", "refrigerator"),
    ("thợ tủ lạnh thay vì thợ máy lạnh", "refrigerator"),
    ("đặt thợ tủ lạnh thay cho thợ máy lạnh", "refrigerator"),
    # correcting themselves
    ("em nhầm rồi, là tủ lạnh", "refrigerator"),
    ("xin lỗi em nhầm, tủ lạnh ạ", "refrigerator"),
    ("à không, tủ lạnh", "refrigerator"),
    ("ý em là tủ lạnh", "refrigerator"),
    ("em nói nhầm, tủ lạnh mới đúng", "refrigerator"),
]


@pytest.mark.parametrize(
    "sentence,expected", list(both_spellings(CHANGING_TO_A_FRIDGE))
)
def test_changing_their_mind_moves_the_booking(kb, sentence, expected):
    assert lp._device_asked_for_now(sentence, kb) == expected


# The same shapes pointed at other trades, so the rule is not fitted to fridges.
CHANGING_TO_SOMETHING_ELSE = [
    ("thôi em muốn đặt thợ điện nước thay vì thợ máy lạnh", "power_outlet"),
    ("em đổi ý, đặt thợ sửa ống nước nhé", "water_pipe"),
    ("đổi sang thợ thông cống", "water_pipe"),
    ("bỏ máy giặt đi, đặt thợ sửa bếp từ", "induction_hob"),
    ("không phải máy giặt, là máy sấy quần áo", "clothes_dryer"),
    ("chuyển sang thợ sửa khóa cửa giúp em", "smart_lock"),
    ("đổi qua thợ lắp đèn", "light_bulb"),
    ("thay vì tủ lạnh thì cho em thợ sửa tivi", "television"),
]


@pytest.mark.parametrize(
    "sentence,expected", list(both_spellings(CHANGING_TO_SOMETHING_ELSE))
)
def test_the_rule_is_not_fitted_to_one_appliance(kb, sentence, expected):
    assert lp._device_asked_for_now(sentence, kb) == expected


# ---------------------------------------------------------------------------
# Sentences that must change nothing
# ---------------------------------------------------------------------------

NAMES_NOTHING = [
    # adding detail, which is what a session is for
    "còn kêu to nữa",
    "mới dùng được 2 năm thôi",
    "nó kêu từ tuần trước",
    "vâng ạ",
    "dạ đúng rồi",
    # asking about the service rather than the machine
    "bao lâu thợ tới",
    "thợ tới nhà lúc nào",
    "giá bao nhiêu vậy em",
    "có bảo hành không",
    "thợ đến nhà chưa",
    "khi nào thợ đến",
    # already booking, with no appliance named
    "đặt giúp em luôn",
    "ok đặt đi",
]


@pytest.mark.parametrize("sentence", [s for s in NAMES_NOTHING] + [
    without_diacritics(s) for s in NAMES_NOTHING
])
def test_a_sentence_naming_no_appliance_leaves_the_session_alone(kb, sentence):
    assert lp._device_asked_for_now(sentence, kb) is None


class TestAmbiguityIsNotGuessedAt:
    """Two appliances and no marker is a question, not a decision."""

    def test_two_appliances_mentioned_together_change_nothing(self, kb):
        assert (
            lp._device_asked_for_now("máy lạnh với tủ lạnh nhà em đều cũ rồi", kb)
            is None
        )

    def test_an_unqualified_fan_is_still_ambiguous_and_says_so(self, kb):
        # "Sửa quạt" genuinely does not say which. Resolving it would be
        # guessing; the clarifier asks whether it is on the ceiling.
        assert lp._device_asked_for_now("cần thợ sửa quạt", kb) is None


class TestTheCollisionsThatHaveBittenBefore:
    def test_a_ceiling_fan_is_not_also_a_floor_fan(self, kb):
        assert lp._device_asked_for_now("book thợ sửa quạt trần", kb) == "ceiling_fan"
        assert lp._device_asked_for_now("đặt thợ sửa quạt cây", kb) == "electric_fan"

    def test_unblocking_a_toilet_is_not_unblocking_a_pipe(self, kb):
        assert lp._device_asked_for_now("cần thợ thông tắc bồn cầu", kb) == "toilet"

    def test_a_technician_arriving_is_not_a_light_bulb(self, kb):
        # `đèn` folds to `den`, and so does `đến`.
        assert lp._device_asked_for_now("thợ đến nhà chưa", kb) is None
        assert lp._device_asked_for_now("khi nào thợ đến", kb) is None

    def test_a_switch_is_not_a_drain(self, kb):
        # `cống` folds to `cong`, and so does `công`.
        assert lp._device_asked_for_now("thay công tắc điện", kb) == "power_outlet"
