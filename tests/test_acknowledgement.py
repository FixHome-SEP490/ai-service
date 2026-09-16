"""The line said before there is an answer.

Three things are worth holding still here. Safety instructions must beat
pleasantries, because a customer reads the first line while the appliance is
still plugged in. Lines must not repeat inside one session, because a fixed
sentence on every turn is how a customer learns nobody is reading. And missing
tone marks must not disarm the safety cues, because that is how people type.
"""

import random

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.pipeline.acknowledgement import (
    Acknowledgements,
    get_acknowledgements,
)


@pytest.fixture
def acks() -> Acknowledgements:
    return Acknowledgements()


# -- safety beats politeness ---------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "máy lạnh có mùi khét",
        "may lanh co mui khet",
        "bật lên là nhảy aptomat",
        "bat len la nhay aptomat",
        "tủ lạnh bốc khói",
        "sờ vào vỏ máy thấy tê tay",
        "so vao vo may thay te tay",
    ],
)
def test_electrical_cues_get_the_instruction_not_a_pleasantry(acks, text):
    line = acks.pick(text=text)
    assert line in acks.all_lines()["safetyFirst"]["electrical"]


@pytest.mark.parametrize(
    "text",
    ["ngửi thấy mùi gas ở bếp", "ngui thay mui gas o bep", "hình như bị rò gas"],
)
def test_gas_cues_get_the_gas_instruction(acks, text):
    line = acks.pick(text=text)
    assert line in acks.all_lines()["safetyFirst"]["gas"]


def test_safety_wins_even_when_the_customer_is_also_angry(acks):
    # Upset would normally take priority over everything but safety. It must
    # not here: the appliance is still energised while they read the reply.
    line = acks.pick(text="bực quá, máy lạnh có mùi khét mà thợ không tới")
    assert line in acks.all_lines()["safetyFirst"]["electrical"]


def test_ordinary_message_gets_no_safety_line(acks):
    assert acks.safety_kind("máy lạnh không lạnh, gió vẫn mạnh") is None


# -- the right bucket -----------------------------------------------------


def test_photo_on_a_new_session_is_a_photo_line(acks):
    assert acks.situation(has_image=True) == "first_photo"


def test_photo_later_in_a_thread_is_a_follow_up(acks):
    assert acks.situation(has_image=True, is_follow_up=True) == "follow_up"


def test_price_question_is_not_answered_with_em_kiem_tra(acks):
    assert acks.situation(text="vệ sinh máy lạnh bao nhiêu tiền") == "price_question"


def test_price_question_without_diacritics_still_routes(acks):
    assert acks.situation(text="ve sinh may lanh bao nhieu tien") == "price_question"


def test_an_upset_customer_is_recognised_before_their_price_question(acks):
    # Answering the price briskly reads as not having noticed they are angry.
    assert (
        acks.situation(text="lần thứ mấy rồi, sửa hết bao nhiêu tiền nữa đây")
        == "customer_upset"
    )


def test_urgency_is_recognised(acks):
    assert acks.situation(text="cần thợ gấp trong hôm nay") == "urgent_mentioned"


def test_plain_description_is_a_first_text(acks):
    assert acks.situation(text="máy lạnh nhà em không lạnh") == "first_text"


# -- variety --------------------------------------------------------------


def test_a_session_does_not_hear_the_same_line_twice_in_a_row(acks):
    seen = [
        acks.pick(session_id="s1", text="máy lạnh không lạnh")
        for _ in range(len(acks.all_lines()["situations"]["first_text"]))
    ]
    assert len(set(seen)) == len(seen)


def test_the_list_wraps_instead_of_falling_back_to_one_fixed_line(acks):
    size = len(acks.all_lines()["situations"]["first_text"])
    seen = [acks.pick(session_id="s2", text="máy lạnh hư") for _ in range(size * 2)]
    # Going round twice is far less noticeable than the same sentence forever.
    assert len(set(seen)) == size


def test_two_sessions_do_not_share_a_memory(acks):
    first = acks.pick(session_id="a", text="máy lạnh hư", rng=random.Random(0))
    second = acks.pick(session_id="b", text="máy lạnh hư", rng=random.Random(0))
    assert first == second


def test_forget_clears_a_session(acks):
    acks.pick(session_id="c", text="máy lạnh hư")
    acks.forget("c")
    assert "c" not in acks._seen


# -- what the client gets -------------------------------------------------


def test_every_bucket_has_more_than_one_line():
    # One line per bucket would defeat the whole point of the module.
    lines = get_acknowledgements().all_lines()
    for name, bucket in lines["situations"].items():
        assert len(bucket) > 1, name


def test_asking_back_and_long_wait_are_shipped_to_the_client():
    lines = get_acknowledgements().all_lines()["situations"]
    assert lines["before_asking_back"]
    assert lines["long_wait"]


def test_endpoint_serves_the_set_in_camel_case():
    client = TestClient(app)
    body = client.get("/api/v1/chat/acknowledgements").json()
    assert body["situations"]["first_text"]
    assert body["safetyFirst"]["electrical"]
