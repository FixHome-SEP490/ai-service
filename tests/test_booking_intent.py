"""A customer who asks to book must always be able to book.

This is the one path with no acceptable failure rate. Everything else in the
service can be wrong in a way that costs an unhelpful answer; being wrong here
costs the customer their reason for opening the app. The PO's instruction was
that when someone says plainly they want a technician or a service, the reply is
the service and the button, and no diagnosis.

Measured before these tests existed: 13 of 38 natural phrasings were recognised,
and of the 11 driven end to end, 5 ended with nothing to press.
"""

import base64
import io

import pytest
from PIL import Image

from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import (
    LocalPipeline,
    _is_not_household,
    _wants_to_book,
)
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm

KB = get_knowledge_base()


class _NoDetector:
    async def detect(self, image):
        return []


def _pipeline() -> LocalPipeline:
    return LocalPipeline(
        detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(KB), kb=KB
    )


def _png() -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), (110, 110, 110)).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


# Someone who has stopped describing and started buying. Grouped by the shape
# of the request, because each group failed for its own reason.
ASKING_TO_BOOK = [
    # the plain forms
    "muốn đặt lịch",
    "cho mình đặt lịch",
    "em muốn đặt thợ",
    "đặt thợ sửa máy lạnh",
    "book thợ",
    "cho tôi đặt dịch vụ vệ sinh máy lạnh",
    "đăng ký dịch vụ",
    "hẹn thợ",
    "gọi thợ",
    "bây giờ anh muốn đặt lịch vệ sinh máy lạnh",
    # asking for a person without the word "đặt"
    "tôi cần thợ tới sửa máy giặt",
    "cần người tới sửa máy lạnh",
    "nhà em cần thợ điện",
    "cho em một bạn thợ tới xem máy giặt",
    "kêu thợ tới giúp em với",
    "yêu cầu thợ tới nhà",
    "xin một thợ sửa bếp từ",
    # hiring
    "mình muốn thuê thợ",
    "thuê người sửa điều hoà",
    "thuê thợ vệ sinh máy lạnh",
    # asking whether the service exists, which is a buying question
    "bên mình có nhận vệ sinh máy lạnh không",
    "bên em có sửa máy rửa bát không",
    "có nhận thông tắc bồn cầu không",
    # short and colloquial
    "đặt luôn đi",
    "chốt đơn luôn",
    "cho anh đặt",
    "muốn book",
    "book giúp em",
    "đặt vệ sinh máy lạnh",
    "làm sao để đặt lịch",
    "giờ đặt như nào",
    "đặt cho tôi một thợ điện",
    # without diacritics, which is how a large share of messages arrive
    "muon dat lich",
    "can tho toi sua may giat",
    "cho minh dat tho",
    "thue tho ve sinh may lanh",
    "dat ve sinh may lanh",
    "ben minh co nhan sua may giat khong",
]

NOT_ASKING_TO_BOOK = [
    # symptoms that merely contain the letters
    "đặt nồi lên bếp mà bếp không nóng",
    "máy giặt đặt ở ban công có sao không",
    "đặt nồi lên thì bếp kêu bíp bíp",
    "máy lạnh nhà em không mát",
    # a booking that already exists. Offering a booking button to someone whose
    # complaint is that their booking produced nobody is the one useless reply.
    "tôi đã đặt lịch rồi mà thợ chưa tới",
    "lịch đặt hôm qua của tôi bị huỷ à",
    "thợ đặt máy sai vị trí rồi",
    # questions about the business, answered from the business documents
    "bảo hành bao lâu",
    "giá vệ sinh máy lạnh bao nhiêu",
]


@pytest.mark.parametrize("text", ASKING_TO_BOOK)
def test_a_request_to_book_is_recognised(text):
    assert _wants_to_book(text), text


@pytest.mark.parametrize("text", NOT_ASKING_TO_BOOK)
def test_a_message_that_is_not_a_request_to_book_is_not_read_as_one(text):
    assert not _wants_to_book(text), text


def test_no_real_symptom_in_the_corpus_reads_as_a_request_to_book():
    """Derived from the corpus, so it grows as faults are written.

    Eight did, all for the same reason: the objects were matched as substrings,
    so "tho" was found inside "thôi", "thoát" and "thông minh". Three separate
    keyword lists in this file have now had that bug.
    """
    wrong = [
        (fault.fault_code, symptom)
        for device in KB.device_types
        for fault in KB.faults_for_device(device)
        for symptom in fault.symptoms_vi
        if _wants_to_book(symptom)
    ]
    assert not wrong, wrong[:10]


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ASKING_TO_BOOK)
async def test_a_request_to_book_always_ends_in_something_bookable(text):
    """The detector saying yes is not the guarantee.

    The guarantee is that the turn ends with a service the app can book and no
    diagnosis in the way. Five of these used to come back as a clarification
    with no service at all, because the service was derived from retrieved
    faults and a customer naming an appliance without a symptom retrieves none.
    """
    response = await _pipeline().diagnose(DiagnosisRequest(description=text))

    assert response.recommended_services, text
    assert not response.suspected_faults, (text, response.suspected_faults)


@pytest.mark.asyncio
async def test_naming_the_appliance_gets_that_appliance_service():
    pipeline = _pipeline()
    for text, expected in [
        ("cho mình đặt thợ sửa máy giặt", "SUA_MAY_GIAT"),
        ("tôi cần thợ tới sửa tủ lạnh", "SUA_TU_LANH"),
        ("bây giờ anh muốn đặt lịch vệ sinh máy lạnh", "VE_SINH"),
    ]:
        response = await pipeline.diagnose(DiagnosisRequest(description=text))
        codes = [s.service_code for s in response.recommended_services]
        assert any(expected in code for code in codes), (text, codes)


@pytest.mark.asyncio
async def test_not_naming_the_appliance_asks_but_still_offers():
    """"Cho mình đặt lịch" does not say what to book, so it has to ask.

    What it must not do is ask with nothing attached, which is what happened:
    the message carries no appliance and no symptom, so the ordinary
    clarification had nothing to offer either.
    """
    response = await _pipeline().diagnose(DiagnosisRequest(description="cho mình đặt lịch"))

    assert response.status.value == "needs_clarification"
    assert response.recommended_services


@pytest.mark.asyncio
async def test_a_photograph_still_gets_diagnosed():
    """Booking intent short-circuits the diagnosis; a photograph must not be.

    Someone who sends a picture has given evidence to read, and the gate is
    written to skip the short circuit when there is an image.
    """
    response = await _pipeline().diagnose(
        DiagnosisRequest(description="đặt thợ sửa cái này", images=[_png()])
    )

    assert response.recommended_services


# --------------------------------------------------------------- scope
# The refusal for things FixHome does not repair runs before every other
# branch, which makes a false positive here the most expensive one in the file:
# the customer is told their question is out of scope and the turn ends.

@pytest.mark.parametrize(
    "text",
    [
        "tôi cần thợ tới sửa tủ lạnh",
        "bao lâu thợ tới",
        "khi nào thợ tới nhà em",
        "kêu thợ tới xem bếp từ giúp em",
        "thợ tới rồi mà chưa làm",
    ],
)
def test_tho_toi_is_not_a_car(text):
    """"Ô tô" folds to "o to", which sits inside "thợ tới".

    Every message containing the commonest phrase in the trade was answered
    with a refusal explaining that FixHome does not repair cars.
    """
    assert not _is_not_household(text), text


@pytest.mark.parametrize(
    "text", ["kêu như máy bay", "lò kêu như máy bay", "quạt kêu như xe máy"]
)
def test_a_simile_is_not_a_report(text):
    """"Kêu như máy bay" is a noisy washing machine, not a question about aircraft."""
    assert not _is_not_household(text), text


@pytest.mark.parametrize(
    "text", ["đồng hồ nước bị rò", "đồng hồ điện quay nhanh bất thường"]
)
def test_a_meter_is_plumbing_and_electrics(text):
    """A water meter and an electricity meter are both "đồng hồ" — and in scope."""
    assert not _is_not_household(text), text


@pytest.mark.parametrize(
    "text",
    [
        "xe máy không nổ",
        "laptop không lên nguồn",
        "điều hoà xe hơi không mát",
        "ô tô nhà em hỏng",
        "điện thoại bị vỡ màn",
        "máy tính không lên",
        "đồng hồ hỏng pin",
    ],
)
def test_what_fixhome_does_not_repair_is_still_refused(text):
    """Widening the scope check must not have opened it."""
    assert _is_not_household(text), text


def test_no_real_symptom_in_the_corpus_is_refused_as_out_of_scope():
    """Derived from the corpus. Two were: both said "kêu như máy bay"."""
    wrong = [
        (fault.fault_code, symptom)
        for device in KB.device_types
        for fault in KB.faults_for_device(device)
        for symptom in fault.symptoms_vi
        if _is_not_household(symptom)
    ]
    assert not wrong, wrong[:10]
