"""A third held-out set for probe_chat2.py --holdout3, written 07/11 before the follow-up branch was measured.

Aimed at what the live run of 07/11 showed: what the customer says after a
conclusion (asks for it again, answers yes or no to nothing, adds a symptom,
asks something specific, switches appliance), and short replies to a question.
Run once, reported as it came out: 20/23 on 07/11, the three misses were this file expecting
"answer" where the conclusion said again is right; those turns now also accept "recap".
"""

from probe_chat2 import T

HOLDOUT3 = [
    ("h3-f1", "followup", None, [
        T("tủ lạnh ngăn mát không lạnh mà ngăn đá vẫn đông", branch="conclude", device="refrigerator", service=("FR-01",)),
        T("vậy là bị gì em", branch=("recap", "answer", "conclude"), has=["kha nang", "tu lanh"], hasnt=["000"]),
    ]),
    ("h3-f2", "followup", None, [
        T("máy giặt vắt cái là rung lắc dữ dội, nhảy cả máy", branch="conclude", device="washing_machine", service=("WM-01",)),
        T("ừ", branch=("recap", "answer", "conclude"), hasnt=["000"]),
    ]),
    ("h3-f3", "followup", None, [
        T("bình nóng lạnh bật đèn đỏ rồi mà nước vẫn lạnh ngắt", branch="conclude", device="water_heater"),
        T("giờ phải làm sao em", branch=("recap", "answer", "conclude"), has=["dat tho", "tho"]),
    ]),
    ("h3-f4", "followup", None, [
        T("máy lạnh chạy kêu ro ro to lắm", branch="conclude", device="air_conditioner"),
        T("à mà nó còn có mùi khét nữa", branch="conclude", device="air_conditioner"),
    ]),
    ("h3-f5", "followup", None, [
        T("tủ lạnh có mùi hôi", branch="conclude", service=("FR-02",)),
        T("đúng rồi", branch=("recap", "answer", "conclude"), hasnt=["000"]),
        T("ok đặt luôn", branch=("answer", "book"), has=["dat tho"]),
    ]),
    ("h3-f6", "followup", None, [
        T("bếp từ nấu được một lúc thì tự tắt", branch="conclude", device="induction_hob"),
        T("có phải do nồi không em", branch=("answer", "conclude")),
    ]),
    ("h3-f7", "followup", None, [
        T("máy lạnh chảy nước xuống tường", branch="conclude", service=("AC-01", "AC-02")),
        T("sửa xong bảo hành bao lâu", branch="answer", hasnt=["6 thang", "sau thang"]),
    ]),
    ("h3-s1", "switch", None, [
        T("máy lọc nước chảy ra chậm rì", branch="conclude", device="water_purifier"),
        T("còn cái quạt trần phòng khách quay yếu hẳn", branch="conclude", device="ceiling_fan"),
    ]),
    ("h3-s2", "switch", None, [
        T("vòi nước bồn rửa bị rỉ nhỏ giọt cả đêm", branch="conclude"),
        T("tiện cho hỏi vệ sinh máy lạnh bao nhiêu", branch="answer", has=["000"]),
    ]),
    ("h3-s3", "switch", "washing_machine", [
        T("máy không xả nước", branch="conclude", device="washing_machine", service=("WM-01",)),
        T("thôi khỏi, máy sấy mới là cái hư, không nóng", branch="conclude", device="clothes_dryer", service=("WM-04",)),
    ]),
    ("h3-a1", "answer", None, [
        T("máy giặt nhà em có vấn đề", branch="ask"),
        T("không vắt", branch="conclude", device="washing_machine", service=("WM-01",)),
    ]),
    ("h3-a2", "answer", None, [
        T("tủ lạnh hư rồi em ơi", branch="ask"),
        T("Không", branch=("ask", "conclude"), device="refrigerator"),
    ]),
    ("h3-a3", "answer", None, [
        T("cái bếp gas nhà mình", branch="ask"),
        T("bật không lên lửa, chỉ nghe tạch tạch", branch="conclude", device="gas_stove", service=("KT-07",)),
    ]),
    ("h3-p1", "platform", None, [T("thợ bên em có mặc đồng phục không", branch="answer")]),
    ("h3-p2", "platform", None, [T("đặt rồi muốn đổi giờ thì làm sao", branch="answer")]),
    ("h3-p3", "platform", None, [T("thợ làm hư thêm đồ nhà mình thì ai chịu", branch="answer")]),
    ("h3-d1", "diagnosis", None, [T("khóa vân tay nhà mình quẹt mãi không nhận", branch="conclude", device="smart_lock", service=("LK-02",))]),
    ("h3-d2", "diagnosis", None, [T("bồn cầu xả xong nước cứ chảy rỉ rả hoài", branch="conclude", device="toilet")]),
    ("h3-d3", "diagnosis", None, [T("máy hút mùi chạy mà khói vẫn bay đầy bếp", branch="conclude", device="range_hood")]),
    ("h3-d4", "diagnosis", None, [T("tivi có tiếng mà màn hình đen thui", branch="conclude", device="television", service=("TV-01",))]),
    ("h3-x1", "edge", None, [T("😡😡 máy lạnh nóng như lò!!! không lạnh gì hết", branch="conclude", device="air_conditioner")]),
    ("h3-x2", "edge", None, [T("may lanh ko lanh, chay nuoc", branch="conclude", device="air_conditioner")]),
    ("h3-x3", "edge", None, [T("anh muốn hỏi giá vàng hôm nay", branch=("not_repair", "answer"))]),
]
