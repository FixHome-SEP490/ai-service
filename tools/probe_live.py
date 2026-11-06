"""Conversations from the live run of 07/11 on fixhome.sbs, for probe_chat2.py --live.

Not held out: these were read, the failures fixed, and they stay as a regression set.
First run (image 3a50c16): #1 the fridge carried the air conditioner's water, #13 and
#14 answered from an unrelated quote, #15 "làm gì trước" offered no fault section.
"""

from probe_chat2 import T

LIVE = [
    ("l-switch", "live", None, [
        T("máy lạnh chảy nước", branch="conclude", device="air_conditioner"),
        T("còn cái tủ lạnh nhà em kêu to lắm", branch="conclude", device="refrigerator", hasnt=["thoat nuoc"]),
    ]),
    ("l-switch2", "live", None, [
        T("tủ lạnh nhà mình không lạnh", branch="conclude", device="refrigerator"),
        T("à mà máy giặt cũng không xả nước luôn", branch="conclude", device="washing_machine", service=("WM-01",)),
    ]),
    ("l-danger", "live", None, [
        T("bình nóng lạnh nhà em nước ra ấm ấm thôi không nóng", branch="conclude", device="water_heater"),
        T("có nguy hiểm không em", branch="answer", hasnt=["nhom trieu chung"]),
    ]),
    ("l-when", "live", None, [T("khi nào thợ tới được", branch="answer", hasnt=["xac nhan da toi"])]),
    ("l-credit", "live", None, [T("anh không có tiền, có trả góp không", branch="answer", hasnt=["ky quy"])]),
    ("l-first", "live", None, [
        T("máy giặt cửa trước bị rỉ nước ở cửa khi giặt", branch="conclude", device="washing_machine"),
        T("giờ em phải làm gì trước", branch="answer"),
    ]),
    ("l-frost", "live", None, [
        T("tủ lạnh bị đóng tuyết dày ngăn đá", branch="conclude", device="refrigerator"),
        T("ngăn dưới thì không lạnh", branch="conclude", device="refrigerator"),
    ]),
    ("l-warranty", "live", None, [
        T("máy lạnh mới vệ sinh tuần trước mà giờ lại chảy nước", branch="conclude", device="air_conditioner", has=["bao hanh"]),
    ]),
    ("l-spark", "live", None, [T("ổ điện chỗ bếp cắm nồi cơm vào là có tia lửa", branch="conclude", device="power_outlet", has=["cau dao"])]),
]
