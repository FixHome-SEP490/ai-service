"""What a conversation has to remember to be a conversation.

Each of these is a way the service forgot something and then asked the customer
to repeat it, which is the thing that makes a support chat feel like a form.
"""

import time

from app.services.pipeline.conversation import (
    Conversation,
    ConversationStore,
    MAX_TURNS,
)


def test_symptoms_spread_across_messages_are_retrieved_together():
    """Each message alone retrieves the wrong faults.

    "Máy không mát" on its own is half a dozen candidates; adding "nó còn kêu
    to" narrows it. Sent separately, the second message is three words with no
    subject.
    """
    chat = Conversation(session_id="s")
    chat.add("customer", "máy lạnh không mát")
    chat.add("assistant", "Máy có được vệ sinh gần đây không?")
    chat.add("customer", "à mà nó còn kêu to nữa")

    joined = chat.customer_text()
    assert "không mát" in joined
    assert "kêu to" in joined
    assert "vệ sinh gần đây" not in joined, "the assistant's own words are not a symptom"


def test_the_device_survives_a_message_with_no_photograph():
    """Nobody sends the same photo twice.

    The follow-up is text, and if the device is forgotten the answer to the
    question we just asked arrives with nothing to attach it to.
    """
    chat = Conversation(session_id="s")
    chat.remember_device("air_conditioner", 0.91, "image")
    chat.add("customer", "mới vệ sinh tháng trước rồi")
    assert chat.device_type == "air_conditioner"


def test_a_question_is_not_asked_twice():
    chat = Conversation(session_id="s")
    chat.remember_questions(["máy có được vệ sinh gần đây không", "cục nóng có chạy không"])
    chat.remember_questions(["máy có được vệ sinh gần đây không", "có mùi khét không"])
    assert chat.asked_symptoms == [
        "máy có được vệ sinh gần đây không",
        "cục nóng có chạy không",
        "có mùi khét không",
    ]


def test_history_is_bounded():
    """An unbounded list is a memory leak with extra steps."""
    chat = Conversation(session_id="s")
    for i in range(MAX_TURNS + 10):
        chat.add("customer", f"tin nhắn {i}")
    assert len(chat.turns) == MAX_TURNS
    assert chat.turns[-1].text_vi == f"tin nhắn {MAX_TURNS + 9}"


def test_an_unknown_session_id_starts_a_conversation_rather_than_failing():
    """A client whose session expired mid-chat should get an answer.

    Returning an error instead would turn an expiry the customer cannot see
    into a dead end they cannot act on.
    """
    store = ConversationStore()
    chat = store.get_or_create("expired-id")
    assert chat.turns == []


def test_a_session_id_the_store_did_not_issue_is_not_adopted():
    """Two clients that pick the same id must not share a conversation.

    The field takes any string of up to sixty-four characters, so "guest", "1"
    or an unauthenticated user id all arrive looking exactly like a real
    session. Adopting them handed one customer's appliance, symptoms and
    shortlist to another.
    """
    store = ConversationStore()
    mine = store.get_or_create("guest")
    mine.remember_device("air_conditioner", 0.9, "image")

    theirs = store.get_or_create("guest")

    assert theirs.session_id != "guest"
    assert theirs.session_id != mine.session_id
    assert theirs.device_type is None


def test_the_id_handed_back_is_the_one_that_works():
    """The client's job is to echo what the reply carried, so that must hold."""
    store = ConversationStore()
    first = store.get_or_create(None)
    first.remember_device("washing_machine", 0.8, "image")

    again = store.get_or_create(first.session_id)

    assert again is first
    assert again.device_type == "washing_machine"


def test_conversations_are_capped_so_the_store_cannot_grow_without_limit():
    """Turns were bounded and the dictionary holding conversations was not.

    Anything producing sessions faster than the hour-long expiry removes them
    grew until the box ran out of memory.
    """
    store = ConversationStore(max_sessions=10)
    for _ in range(50):
        store.get_or_create(None)
    assert len(store) == 10


def test_the_conversation_dropped_to_make_room_is_the_stalest_one():
    """Three fit, a fourth arrives, and the one nobody has touched goes.

    Read straight off the store rather than through get_or_create, because
    asking for a conversation that is no longer there creates one — which would
    both hide the eviction and cause another.
    """
    store = ConversationStore(max_sessions=3)
    stale = store.get_or_create(None)
    stale.updated_at = time.time() - 600
    live = [store.get_or_create(None) for _ in range(2)]

    assert len(store) == 3
    newcomer = store.get_or_create(None)

    surviving = set(store._sessions)
    assert stale.session_id not in surviving
    assert surviving == {c.session_id for c in live} | {newcomer.session_id}


def test_a_conversation_left_alone_is_evicted():
    store = ConversationStore(ttl_seconds=1)
    chat = store.get_or_create(None)
    chat.updated_at = time.time() - 5
    assert len(store) == 0


def test_two_conversations_do_not_see_each_other():
    store = ConversationStore()
    first = store.get_or_create("a")
    second = store.get_or_create("b")
    first.remember_device("air_conditioner", 0.9, "image")
    assert second.device_type is None


def test_a_device_from_words_is_remembered_but_not_announced_as_detected():
    """The pipeline has not looked at the appliance.

    Remembering it keeps retrieval on the right device across turns. Reporting
    it as detected would need a confidence, and there is no honest number for
    "the customer said so".
    """
    chat = Conversation(session_id="s")
    chat.remember_device("air_conditioner", 0.0, "description")
    assert chat.device_type == "air_conditioner"
    assert chat.device_source_vi == "description"
