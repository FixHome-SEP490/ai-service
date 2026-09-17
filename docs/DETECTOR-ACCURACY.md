# Bộ nhận diện ảnh: đo được gì

Đo ngày 17/09/2026 trên `weights/detector-v1`, 40 ảnh mỗi thiết bị, tổng 680 ảnh lấy từ `datasets/collected`. Chạy CPU máy lập trình, không tốn GPU.

Cách chấm: lấy hộp có độ tin cậy cao nhất, so với thư mục chứa ảnh. Không có hộp nào vượt ngưỡng thì tính là **không nhận ra** — khác hẳn với **nhận nhầm**, và khác nhau ở chỗ quan trọng nhất.

## Theo thiết bị, ở ngưỡng đang chạy là 0.45

| thiết bị | đúng | nhầm | không ra | tỷ lệ |
| :--- | ---: | ---: | ---: | ---: |
| máy lạnh | 37 | 0 | 3 | 92% |
| ấm siêu tốc | 36 | 2 | 2 | 90% |
| tivi | 36 | 0 | 4 | 90% |
| quạt bàn | 33 | 0 | 7 | 82% |
| bếp gas | 33 | 4 | 3 | 82% |
| tủ lạnh | 33 | 2 | 5 | 82% |
| quạt trần | 32 | 2 | 6 | 80% |
| lò vi sóng | 32 | 3 | 5 | 80% |
| lò nướng | 31 | 1 | 8 | 78% |
| máy giặt | 31 | 4 | 5 | 78% |
| bình nóng lạnh | 28 | 5 | 7 | 70% |
| ổ cắm | 27 | 3 | 10 | 68% |
| bồn cầu | 26 | 4 | 10 | 65% |
| vòi nước | 24 | 3 | 13 | 60% |
| ống nước | 24 | 7 | 9 | 60% |
| bồn rửa | 22 | 2 | 16 | 55% |
| bóng đèn | 17 | 7 | 16 | 42% |
| **tổng** | **502** | | | **74%** |

## Hạ ngưỡng không phải câu trả lời

| ngưỡng | đúng | nhầm | không ra |
| :--- | ---: | ---: | ---: |
| 0.45 (đang dùng) | 74% | **7%** | 19% |
| 0.35 | 77% | 10% | 13% |
| 0.25 | 80% | 12% | 8% |
| 0.15 | 81% | 15% | 4% |

Xuống 0.25 thì đổi 11 điểm "không nhận ra" lấy 5 điểm "nhận nhầm". Đó là một vụ đổi chác tồi cho sản phẩm này.

Khi detector không ra gì, hệ thống hỏi khách dùng thiết bị nào — khách gõ thêm một dòng. Khi detector nhận nhầm, khách nhận nguyên một chẩn đoán, một khoảng giá và một lời mời đặt thợ, tất cả về một cái máy khác. Nguyên tắc của cả hệ thống này là thiếu một câu trả lời thì chỉ là thiếu, còn một câu trả lời sai mà tự tin là một lỗi.

**Giữ 0.45.**

## Vậy có cần train lại không

Có, nếu muốn nhận diện tốt hơn. Ngưỡng không mua được độ chính xác mà không trả bằng câu trả lời sai, nên phần còn lại phải đến từ dữ liệu.

Bốn lớp yếu nhất — bóng đèn 42%, bồn rửa 55%, vòi nước 60%, ống nước 60% — đều là vật nhỏ, thường lẫn vào nền, và hay xuất hiện cùng nhau trong một tấm ảnh nhà tắm. Phần lớn cái mất là **không nhận ra**, không phải nhầm lớp: bóng đèn có 16/40 ảnh không ra hộp nào. Bộ nhận diện không lẫn lộn các lớp với nhau, nó chỉ không đủ tự tin.

Điều đó nói rằng cần thêm ảnh cho bốn lớp đó chứ không cần đổi kiến trúc.

## Nhưng cân nhắc trước khi bỏ tiền

Ảnh không phải đường duy nhất vào hệ thống. Khách gõ "bóng đèn nhà em cháy rồi" thì không cần detector, và bộ 403 hội thoại cho thấy đường chữ mới là đường chính. Detector là thứ giúp khách đỡ phải gõ, không phải thứ hệ thống dựa vào để chẩn đoán.

Nên nếu phải chọn giữa train lại detector và làm nốt những việc trong `WHAT-REMAINS.md`, em chọn việc kia trước.
