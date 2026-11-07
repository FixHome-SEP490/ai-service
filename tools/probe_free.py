"""Unruly conversations of 07/11 afternoon, for probe_chat2.py --free.

Not held out: 50 conversations with no rule to them (no accents, slang, emoji,
English, insults, long stories, outside the catalogue) were read, and the
failures fixed at their layer; these are the ones that failed, kept as a
regression set. First run (main 8afb77d): the gas smell was asked whether it
smelled of gas, a chewed cord was called an impact, the faucet lost to the
sink, an answer said yes to female technicians and to buying copper pipe, and
appliances outside the catalogue were mapped onto the nearest one.
"""

from probe_chat2 import T

FREE = [
    (
        "f-gas-switch",
        "free",
        None,
        [
            T("máy lạnh không mát", branch="conclude", device="air_conditioner"),
            T(
                "à thôi cái đó để sau, giờ bếp gas nhà em có mùi gas",
                branch="conclude",
                device="gas_stove",
                has=["khoa van"],
            ),
        ],
    ),
    (
        "f-gas",
        "free",
        None,
        [T("bếp gas nhà em có mùi gas", branch="conclude", device="gas_stove", has=["khoa van"])],
    ),
    (
        "f-cord",
        "free",
        None,
        [
            T(
                "dây điện tủ lạnh bị chuột cắn đứt vỏ, thấy cả lõi đồng",
                branch="conclude",
                device="refrigerator",
                has=["rut phich"],
                hasnt=["va dap"],
            ),
        ],
    ),
    (
        "f-faucet",
        "free",
        None,
        [
            T(
                "vòi nước bồn rửa chén nhỏ giọt cả đêm tốn nước quá",
                branch="conclude",
                device="faucet",
            )
        ],
    ),
    (
        "f-female",
        "free",
        None,
        [
            T(
                "có thợ nữ không em, nhà chỉ có mình chị",
                branch="answer",
                hasnt=["co, ", "chon tho nu"],
            )
        ],
    ),
    (
        "f-pipe",
        "free",
        None,
        [
            T(
                "anh mới mua máy lạnh, lắp có cần mua thêm ống đồng không",
                branch="answer",
                hasnt=["can mua"],
            )
        ],
    ),
    (
        "f-tools",
        "free",
        None,
        [
            T(
                "thợ có mang đồ nghề không hay nhà mình phải chuẩn bị gì",
                branch="answer",
                hasnt=["day du do nghe"],
            )
        ],
    ),
    (
        "f-advice",
        "free",
        None,
        [
            T(
                "em ơi tư vấn anh nên mua máy lạnh hãng nào tốt",
                branch="answer",
                hasnt=["cho em biet", "de em tu van"],
            )
        ],
    ),
    (
        "f-danang",
        "free",
        None,
        [
            T(
                "nhà mình ở Đà Nẵng có thợ không",
                branch="answer",
                has=["ha noi", "ho chi minh", "chua nhan"],
            )
        ],
    ),
    (
        "f-explode",
        "free",
        None,
        [
            T(
                "mẹ em bảo bình nóng lạnh kêu lụp bụp như nước sôi",
                branch="conclude",
                device="water_heater",
            ),
            T("có nổ không em, sợ quá", branch="answer", hasnt=["chua co thong tin"]),
        ],
    ),
    (
        "f-rice",
        "free",
        None,
        [T("nồi cơm điện nấu cơm bị sống", branch="not_repair", has=["noi com"])],
    ),
    (
        "f-hairdryer",
        "free",
        None,
        [T("máy sấy tóc bị cháy", branch="not_repair", has=["may say toc"])],
    ),
    (
        "f-purifier",
        "free",
        None,
        [T("máy lọc không khí kêu to", branch="not_repair", has=["may loc khong khi"])],
    ),
    (
        "f-tv-mount",
        "free",
        None,
        [
            T(
                "anh muốn treo tivi lên tường",
                branch="conclude",
                device="television",
                hasnt=["em chuyen"],
            )
        ],
    ),
    (
        "f-weather",
        "free",
        None,
        [T("hôm nay trời đẹp nhỉ", branch=("not_repair", "ask"), hasnt=["viec nay"])],
    ),
]
