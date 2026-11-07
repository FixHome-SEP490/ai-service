"""Customer-care questions find the sections written for them (07/11 evening).

The documents: system/uy-tin-fixhome.md, system/huong-dan-su-dung-app.md and,
in every devices/*.md, "Vệ sinh định kỳ bao lâu một lần" and "Dùng đúng cách
cho bền và an toàn". The model picks from the shortlist; a section that does
not reach it cannot be quoted."""

import pytest

from app.services.chat2.answer import candidates, index, shortlist
from app.services.chat2.menu import devices

CARE = "Vệ sinh định kỳ bao lâu một lần"
USE = "Dùng đúng cách cho bền và an toàn"


@pytest.mark.parametrize(
    "question, device, section",
    [
        ("fixhome có uy tín không", None, "FixHome có uy tín không"),
        ("fixhome uy tin ko vay, co lua dao ko", None, "FixHome có uy tín không"),
        ("cho thợ lạ vào nhà có an toàn không em", None, "Thợ lạ vào nhà có an toàn không"),
        ("lỡ thợ tới rồi đòi thêm tiền thì sao", None, "Bị thợ đòi thêm tiền thì sao"),
        ("đặt thợ trên app thế nào em", None, "Đặt thợ trên FixHome thế nào"),
        ("huỷ đơn ở đâu", None, "Huỷ đơn ở đâu"),
        ("làm sao đánh giá thợ sau khi sửa xong", None, "Đánh giá thợ ở đâu"),
        ("tôi muốn đổi địa chỉ nhà trong tài khoản", None, "Sửa hồ sơ và sổ địa chỉ"),
        ("ml bao lau rua luoi loc 1 lan", "air_conditioner", CARE),
        ("lõi lọc máy lọc nước RO bao lâu thay", "water_purifier", CARE),
        ("bình nóng lạnh có nên bật cả ngày không", "water_heater", USE),
        ("khoá vân tay bao lâu thay pin", "smart_lock", CARE),
        ("lò vi sóng cho bát inox vào được không", "microwave_oven", USE),
    ],
)
def test_the_question_reaches_its_section(question, device, section):
    titles = [p.section_vi for p in shortlist(question, candidates(device, None), device)]
    assert section in titles


def test_every_appliance_has_its_care_and_use_sections():
    written = {d for d in devices() if d != "range_hood"}
    for heading in (CARE, USE):
        have = {p.scope.split(":", 1)[1] for p in index().values() if p.section_vi == heading and p.scope.startswith("device:")}
        assert written <= have, (heading, sorted(written - have))
