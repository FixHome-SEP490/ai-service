"""The same bug, four times, so this checks for it mechanically.

Diacritics come off before matching. Once they do, a short keyword hides inside
an ordinary word of the trade, and a list that reads as obviously correct stops
being correct: "giặt" folds to "giat", which contains "gia", so every question
about a washing machine was read as a question about price and answered with
the cost of a door glass.

That is the fourth time this has happened here. Three of them were found by a
customer or by reading an answer that looked wrong. This finds them by looking,
and it looks at the lists rather than at the answers, so it fails on the commit
that adds the keyword rather than a week later.
"""

import pytest

from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import (
    _BUSINESS_WORDS,
    _MONEY_WORDS,
    _asks_about_money,
    _fold_vi,
)

KB = get_knowledge_base()

LISTS = {
    "_MONEY_WORDS": _MONEY_WORDS,
    "_BUSINESS_WORDS": _BUSINESS_WORDS,
}


def _alias_texts():
    """Every alias of every device, folded, plus the displayed names."""
    for device in KB.device_types:
        for alias in KB.aliases_vi(device):
            yield device, alias, _fold_vi(alias)
        name = KB.device_name_vi(device)
        if name:
            yield device, name, _fold_vi(name)


def _buried_keywords():
    """Every place a single keyword hides inside an alias without being a word.

    Derived from the catalogue rather than listed, so it grows by itself when a
    device or an alias is added. `gia` inside `giat` is the whole bug; `re`
    inside `cua tren` and `treo tuong` is the same bug, found before it cost
    anything.
    """
    for name, words in sorted(LISTS.items()):
        for keyword in words:
            if " " in keyword:
                continue  # a phrase cannot hide inside one word
            for device, alias, folded in _alias_texts():
                if keyword in folded and keyword not in folded.split():
                    yield name, keyword, device, alias


def test_the_catalogue_still_contains_words_these_keywords_hide_inside():
    """If this fails the test below is no longer testing anything.

    It exists so that removing the last collision from the catalogue cannot
    quietly turn the real check into a check of nothing.
    """
    assert list(_buried_keywords()), "no buried keywords left; the guard below is idle"


@pytest.mark.parametrize(
    "keyword,alias", sorted({(k, a) for _n, k, _d, a in _buried_keywords()})
)
def test_a_keyword_buried_in_an_alias_does_not_fire_on_that_alias(keyword, alias):
    """Naming the appliance must not read as asking the keyword's question.

    The keyword lists are allowed to hold a word that hides inside another —
    "giá" is a real word and so is "giặt". What is not allowed is matching it
    that way, and that is what this pins: the matcher is whole-word, and it is
    whole-word for both lists rather than for whichever one was fixed first.
    """
    from app.services.pipeline.local_pipeline import _asks_about_the_business

    assert not _asks_about_money(alias), f"{alias!r} reads as a price question"
    assert not _asks_about_the_business(alias), f"{alias!r} reads as a business question"


@pytest.mark.parametrize(
    "question",
    [
        "máy giặt nhà em không vắt được",
        "máy giặt kêu to khi vắt",
        "lồng giặt bị rung",
        "bột giặt không tan hết",
        "máy giặt cửa trên không chạy",
        "remote không ăn",
        "điều khiển tivi không nhận",
        "quạt treo tường kêu to",
    ],
)
def test_a_fault_report_is_not_a_question_about_price(question):
    """These read as money questions and were answered as ones.

    The price row is added to the front of what the model reads, and the model
    answers from the first relevant passage, so "máy giặt nhà em không vắt
    được" came back as "Kính cửa máy giặt: 500.000đ tới 1.200.000đ một cái."
    """
    assert not _asks_about_money(question), question


@pytest.mark.parametrize(
    "question",
    [
        "giá sửa máy lạnh bao nhiêu",
        "chi phí thay aptomat",
        "hết bao nhiêu tiền",
        "có rẻ hơn không",
        "mắc quá em ơi",
        "sửa máy giặt giá bao nhiêu",
        "thay bo mạch máy giặt hết bao nhiêu",
        "vệ sinh máy lạnh bao nhiêu tiền",
    ],
)
def test_a_real_question_about_price_is_still_recognised(question):
    """Whole-word matching must not have thrown the feature away.

    The last two matter most: they name a washing machine and ask about money
    in the same sentence, which is the case a fix aimed only at "giặt" would
    have broken.
    """
    assert _asks_about_money(question), question
