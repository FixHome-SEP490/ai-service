# Cách dựng khoảng giá gợi ý

## Quy tắc

Khi AI nhận ra bệnh, nó gợi ý dịch vụ nên đặt, kèm một khoảng giá.

**Sàn là tiền công thợ.** Thợ vẫn phải di chuyển và làm việc dù cuối cùng có thay
linh kiện hay không, nên không có ca nào rẻ hơn mức đó.

**Trần là tiền công cộng ước tính linh kiện** cần thay hoặc sửa.

Khoảng được phép rộng, vì rộng mà đúng thì tốt hơn hẹp mà sai. Nhưng **không
được đội quá cao**, vì con số lớn làm khách ngộp rồi bỏ luôn ý định đặt lịch —
và một khách bỏ đi vì sợ giá là mất mát lớn hơn nhiều so với việc báo hụt vài
trăm nghìn rồi kỹ thuật viên điều chỉnh khi tới nơi.

## Hai bảng giá

**Tiền công** lấy từ mục 8.3.1 tài liệu nghiệp vụ. Mười tám dịch vụ, mỗi dịch vụ
một giá cố định do Admin quản lý và được snapshot lúc khách đặt lịch. Thấp nhất
100.000đ, cao nhất 650.000đ. Nằm ở `app/data/labour_catalog.json`.

**Linh kiện** lấy từ bảng 500 dòng do nhóm dev khác cung cấp. Mỗi dòng là một
khoảng vì giá thật phụ thuộc model. Từ 300đ tới 15 triệu. Nằm ở
`app/data/parts_catalog.json`.

## Vì sao không lấy thẳng trần của linh kiện

Block máy nén Inverter 24.000 BTU có giá 4.5 tới 7.5 triệu. Cộng tiền công thành
gần 8 triệu. Con số đó đúng về mặt kỹ thuật và sai về mặt sản phẩm: khách đọc
xong đóng ứng dụng.

Ba cách xử lý, dùng kết hợp.

**Chọn linh kiện đại diện chứ không chọn đắt nhất.** Một bệnh thường ứng với
nhiều mã linh kiện khác nhau theo công suất. Lấy mã phổ biến nhất chứ không lấy
mã cao cấp nhất.

**Trần lấy mức giữa của khoảng linh kiện, không lấy đỉnh.** Khoảng của mỗi linh
kiện đã tính tới hàng cao cấp; cộng dồn đỉnh của nhiều linh kiện ra một con số
gần như không bao giờ xảy ra.

**Với bệnh mà chi phí có thể rất lớn, nói rõ là cần kiểm tra.** Máy nén hỏng
không nên hiện "8 triệu" mà nên hiện khoảng thấp kèm ghi chú rằng hạng mục này
cần kỹ thuật viên xác định tại chỗ. Báo giá chính thức vốn dĩ chỉ lập sau khi
kiểm tra, nên nói vậy vừa đúng quy trình vừa đỡ dọa khách.

## Khi thiếu dữ liệu

Hai bảng không phủ hết mười bảy lớp.

Thiếu bảng công: tủ lạnh, lò vi sóng, lò nướng, bếp gas, ấm đun, bồn cầu, ống
nước.

Thiếu bảng linh kiện: bồn rửa, vòi nước, bồn cầu, ống nước — toàn bộ nhóm nước
không có dòng nào.

Thiếu cả hai: bồn cầu và ống nước.

Khi thiếu, sàn lùi về phí kiểm tra tại nhà 100.000đ và trần để trống kèm ghi chú
cần kiểm tra. Trung thực, nhưng không giúp khách quyết định được nhiều, nên hai
nhóm này đáng được bổ sung bảng giá trước khi vận hành thật.

## Quan hệ với báo giá chính thức

Khoảng giá này **chỉ là tham khảo** và không ràng buộc ai. Báo giá chính thức do
kỹ thuật viên lập sau khi kiểm tra trực tiếp, và chỉ có hiệu lực khi khách duyệt.
Điều đó đã nằm trong chính sách và AI luôn kèm câu miễn trừ.

Nói cách khác, khoảng giá tồn tại để khách quyết định **có nên đặt lịch hay
không**, không phải để khách biết mình sẽ trả bao nhiêu. Thiết kế nó theo đúng
mục đích đó thì mới chọn được các đánh đổi ở trên.
