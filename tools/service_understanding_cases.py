"""What a customer types for every service Backend has open, and the service it means.

PO 01/11/2026: the catalogue sells "Vệ sinh, bảo dưỡng tủ lạnh" and the
assistant booked "Sửa tủ lạnh" for a customer who asked for exactly that
cleaning. Measured the same day: 12 of the 37 open services were reached by no
fault at all, so no wording could book them. These sentences are team-written,
two or more per service: the work said outright, and the way people actually
ask (no accents, "lắp mới", the thing that smells). Each names the one service
a person reading it would book. Pinned in tests/test_service_understanding.py,
so a service opened later and missing here is caught there too.
"""

# (customer text, expected service code)
CASES = [
    # Điều hòa
    ("máy lạnh không mát, chạy mà không ra hơi lạnh", "AC-01"),
    ("sửa máy lạnh giúp em", "AC-01"),
    ("vệ sinh máy lạnh", "AC-02"),
    ("lâu rồi chưa vệ sinh điều hòa, muốn làm sạch dàn lạnh", "AC-02"),
    ("ve sinh may lanh", "AC-02"),
    ("lắp máy lạnh mới mua", "AC-03"),
    ("cần lắp đặt điều hòa cho phòng ngủ", "AC-03"),
    ("tháo máy lạnh chuyển sang nhà mới", "AC-04"),
    ("di dời điều hòa sang phòng khác", "AC-04"),
    # Điện
    ("ổ cắm bị chập, cắm vào là nhảy cầu dao", "EL-01"),
    ("lắp thêm ổ cắm điện", "EL-02"),
    # Tủ lạnh
    ("tủ lạnh không lạnh", "FR-01"),
    ("sửa tủ lạnh", "FR-01"),
    ("vệ sinh tủ lạnh", "FR-02"),
    ("tủ lạnh có mùi hôi khó chịu, muốn vệ sinh bảo dưỡng", "FR-02"),
    ("bảo dưỡng tủ lạnh định kỳ", "FR-02"),
    ("ve sinh tu lanh", "FR-02"),
    ("tủ lạnh có mùi hôi", "FR-02"),
    ("mở tủ lạnh ra là bốc mùi tanh", "FR-02"),
    # Bếp
    ("bếp từ không nhận nồi", "KT-01"),
    ("vệ sinh máy hút mùi", "KT-02"),
    ("máy hút mùi bám dầu mỡ, cần làm sạch", "KT-02"),
    ("máy hút mùi không chạy", "KT-03"),
    ("sửa máy hút mùi hút yếu", "KT-03"),
    ("lắp bếp từ âm bàn", "KT-06"),
    ("lắp đặt bếp điện mới", "KT-06"),
    ("bếp gas bật không lên lửa", "KT-07"),
    ("lò nướng không nóng", "KT-08"),
    ("ấm siêu tốc cắm không chạy", "KT-09"),
    # Đèn, quạt
    ("lắp đèn trần phòng khách", "LF-01"),
    ("lắp quạt trần", "LF-02"),
    ("quạt điện quay chậm", "LF-03"),
    # Khóa
    ("khóa vân tay không nhận vân tay", "LK-02"),
    ("lắp khóa thông minh cho cửa chính", "LK-03"),
    ("lap khoa van tay", "LK-03"),
    # Nước
    ("ống nước bị rò rỉ", "PI-01"),
    ("máy lọc nước không ra nước", "RO-01"),
    ("thay lõi lọc nước", "RO-02"),
    ("bảo dưỡng máy lọc nước", "RO-02"),
    ("lắp máy lọc nước", "RO-03"),
    ("lắp đặt máy lọc nước RO mới mua", "RO-03"),
    # Thiết bị vệ sinh
    ("vòi nước bị rỉ nước liên tục", "SA-02"),  # bảng V3 nhóm chốt 19/10: rỉ vòi là thay vòi
    ("bồn cầu xả nước yếu", "SA-01"),
    ("thay bồn cầu mới", "SA-02"),
    ("lắp lavabo mới", "SA-02"),
    ("bồn cầu bị tắc", "SA-03"),
    ("thông tắc chậu rửa", "SA-03"),
    # Tivi
    ("lắp tivi lên tường", "TV-01"),
    ("treo tivi", "TV-01"),
    # Bình nóng lạnh
    ("vệ sinh bình nóng lạnh", "WH-01"),
    ("bình nóng lạnh không nóng", "WH-02"),
    ("lắp bình nóng lạnh mới", "WH-03"),
    # Máy giặt, máy sấy
    ("máy giặt không vắt", "WM-01"),
    ("vệ sinh máy giặt", "WM-02"),
    ("máy giặt hôi, cần vệ sinh lồng giặt", "WM-02"),
    ("lắp máy giặt mới", "WM-03"),
    ("lắp đặt máy giặt cửa ngang", "WM-03"),
    ("máy sấy không nóng", "WM-04"),
    ("vệ sinh máy sấy", "WM-05"),
    ("lắp máy sấy quần áo", "WM-06"),
]
