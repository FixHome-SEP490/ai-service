"""Questions a customer-care assistant is asked, for probe_chat2.py --guides.

Written 07/11 evening before the documents they draw on (trust, how to use the
app, how often to clean each appliance) existed, from what a customer would
ask and what any true answer must contain, so the first run is a held-out
score. Several are typed the way customers type: no accents, short forms.
"""

from probe_chat2 import T

A = "answer"
NO_INFO = ["chua co thong tin"]

GUIDES = [
    # ---------- trust ----------
    ("g-trust-1", "trust", None, [T("fixhome có uy tín không", branch=A, has=["xac minh", "can cuoc", "danh gia", "bao hanh"], hasnt=NO_INFO)]),
    ("g-trust-2", "trust", None, [T("fixhome uy tin ko vay, co lua dao ko", branch=A, has=["xac minh", "can cuoc", "danh gia", "bao gia"], hasnt=NO_INFO)]),
    ("g-trust-3", "trust", None, [T("cho thợ lạ vào nhà có an toàn không em", branch=A, has=["xac minh", "can cuoc", "khuon mat", "danh gia"], hasnt=NO_INFO)]),
    ("g-trust-4", "trust", None, [T("lỡ thợ tới rồi đòi thêm tiền thì sao", branch=A, has=["duyet", "dong y", "phat sinh"], hasnt=NO_INFO)]),
    ("g-trust-5", "trust", None, [T("sửa xong vài hôm lại hỏng thì ai chịu", branch=A, has=["bao hanh"], hasnt=NO_INFO)]),
    ("g-trust-6", "trust", None, [T("thông tin cá nhân với ảnh nhà tôi có bị lộ ra ngoài không", branch=A, has=["du lieu", "thong tin", "anh"])]),
    # ---------- using the app ----------
    ("g-app-1", "app", None, [T("đặt thợ trên app thế nào em", branch=A, has=["dich vu", "dia chi", "khung gio", "thoi gian"], hasnt=NO_INFO)]),
    ("g-app-2", "app", None, [T("huỷ đơn ở đâu", branch=A, has=["huy"], hasnt=NO_INFO)]),
    ("g-app-3", "app", None, [T("làm sao đánh giá thợ sau khi sửa xong", branch=A, has=["danh gia", "sao"], hasnt=NO_INFO)]),
    ("g-app-4", "app", None, [T("muốn yêu cầu bảo hành thì bấm ở đâu", branch=A, has=["bao hanh"], hasnt=NO_INFO)]),
    ("g-app-5", "app", None, [T("dat xong roi thi bao gio co tho nhan", branch=A, has=["nhan", "tho"], hasnt=NO_INFO)]),
    ("g-app-6", "app", None, [T("tôi muốn đổi địa chỉ nhà trong tài khoản", branch=A, has=["dia chi", "ho so", "tai khoan"], hasnt=NO_INFO)]),
    # ---------- how often to clean, how to use ----------
    ("g-clean-ac", "care", None, [T("máy lạnh bao lâu vệ sinh một lần", branch=A, has=["thang"], hasnt=NO_INFO)]),
    ("g-clean-ac2", "care", None, [T("ml bao lau rua luoi loc 1 lan", branch=A, has=["tuan", "thang"], hasnt=NO_INFO)]),
    ("g-clean-fridge", "care", None, [T("tủ lạnh có cần vệ sinh định kỳ không, bao lâu một lần", branch=A, has=["thang"], hasnt=NO_INFO)]),
    ("g-clean-wm", "care", None, [T("lồng máy giặt bao lâu thì nên vệ sinh", branch=A, has=["thang", "tuan"], hasnt=NO_INFO)]),
    ("g-filter-ro", "care", None, [T("lõi lọc máy lọc nước RO bao lâu thay", branch=A, has=["thang", "nam"], hasnt=NO_INFO)]),
    ("g-heater-on", "care", None, [T("bình nóng lạnh có nên bật cả ngày không", branch=A, has=["tat", "khong nen", "ngat"], hasnt=NO_INFO)]),
    ("g-heater-rod", "care", None, [T("thanh magie bình nóng lạnh bao lâu thay", branch=A, has=["nam", "thang"], hasnt=NO_INFO)]),
    ("g-hob", "care", None, [T("dùng bếp từ thế nào cho bền", branch=A, has=["noi", "day", "mat kinh"], hasnt=NO_INFO)]),
    ("g-gas-hose", "care", None, [T("dây dẫn gas bếp gas bao lâu phải thay", branch=A, has=["nam", "thang"], hasnt=NO_INFO)]),
    ("g-lock", "care", None, [T("khoá vân tay bao lâu thay pin", branch=A, has=["pin"], hasnt=NO_INFO)]),
    ("g-ceilfan", "care", None, [T("quạt trần có cần bảo dưỡng gì không", branch=A, has=["bui", "canh", "dau", "oc"], hasnt=NO_INFO)]),
    ("g-dishwasher", "care", None, [T("hướng dẫn dùng máy rửa bát cho đúng", branch=A, has=["loc", "muoi", "bat", "chen"], hasnt=NO_INFO)]),
    ("g-microwave", "care", None, [T("lò vi sóng cho bát inox vào được không", branch=A, has=["khong", "kim loai"], hasnt=NO_INFO)]),
]
