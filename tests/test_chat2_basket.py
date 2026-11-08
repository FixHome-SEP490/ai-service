"""Several appliances in one chat are booked together (PO 08/11/2026).

The customer concluded the fridge, then said the air conditioner is broken too:
the bar offered only the air conditioner, as if the fridge had been swapped.
Another appliance adds to the visit; only words that mean "instead" replace."""

from app.services.chat2.brain import Verdict, _inspect
from app.services.chat2.provider import Session, _fill_basket, _services, _visit, wants_instead


def _concluded(device, fault, service):
    return Verdict(device, "repair", "conclude", fault, service, f"{device} ok", need_vi="hư")


def test_a_second_appliance_is_added_not_swapped():
    session = Session("s")
    fridge = _concluded("refrigerator", "FRIDGE_LOW_GAS", "FR-01")
    _fill_basket(session, fridge, "tủ lạnh không lạnh")
    ac = _concluded("air_conditioner", "AC_PCB_FAULT", "AC-01")
    _fill_basket(session, ac, "còn máy lạnh nhà em cũng không chạy")
    assert [b["device_type"] for b in session.basket] == ["refrigerator", "air_conditioner"]
    # This turn's appliance leads; the fridge stays in the visit.
    assert [v.device_type for v in _visit(ac, session)] == ["air_conditioner", "refrigerator"]
    assert [s.service_code for s in _services(ac, session)] == ["AC-01", "FR-01"]


def test_words_that_mean_instead_replace():
    session = Session("s")
    _fill_basket(session, _concluded("refrigerator", None, "FR-01"), "tủ lạnh hư")
    _fill_basket(session, _concluded("air_conditioner", None, "AC-01"), "à nhầm, không phải tủ lạnh, là máy lạnh")
    assert [b["device_type"] for b in session.basket] == ["air_conditioner"]
    assert wants_instead("thôi khỏi sửa tủ lạnh, đổi sang máy giặt")
    assert wants_instead("cái đó để sau")
    assert not wants_instead("đặt thêm máy giặt nữa nhé")
    assert not wants_instead("còn máy lạnh cũng hư")


def test_the_same_appliance_concluded_again_is_updated_in_place():
    session = Session("s")
    _fill_basket(session, _concluded("refrigerator", "FRIDGE_LOW_GAS", "FR-01"), "tủ lạnh không lạnh")
    _fill_basket(session, _concluded("air_conditioner", None, "AC-01"), "máy lạnh cũng hư")
    _fill_basket(session, _concluded("refrigerator", "FRIDGE_DIRTY_ODOR", "FR-02"), "tủ lạnh còn hôi nữa")
    assert [(b["device_type"], b["service_code"]) for b in session.basket] == [("air_conditioner", "AC-01"), ("refrigerator", "FR-02")]


def test_the_basket_travels_in_the_state():
    from app.services.chat2.provider import Sessions

    session = Session("s")
    _fill_basket(session, _concluded("refrigerator", None, "FR-01"), "tủ lạnh hư")
    _fill_basket(session, _concluded("air_conditioner", None, "AC-01"), "máy lạnh hư")
    back = Sessions().get("s", session.export(), [])
    assert [b["device_type"] for b in back.basket] == ["refrigerator", "air_conditioner"]


def test_an_appliance_named_without_a_symptom_among_several_is_booked_for_inspection():
    asked = Verdict("washing_machine", "repair", "ask", None, None, "Máy giặt bị sao ạ?", question_vi="Máy giặt bị sao ạ?")
    booked = _inspect(asked)
    assert booked.decision == "conclude" and booked.service_code and booked.fault_code is None
    assert "kiểm tra" in booked.reply_vi


def test_a_question_alone_keeps_the_last_reply():
    session = Session("s")
    asking = Verdict("refrigerator", "repair", "ask", None, None, "Tủ lạnh bị sao ạ?")
    assert [v.device_type for v in _visit(asking, session)] == ["refrigerator"]
