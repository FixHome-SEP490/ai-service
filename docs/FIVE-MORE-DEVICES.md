# Năm thiết bị bổ sung cho bộ nhận diện

Chốt ngày 17/09/2026. Backend có dịch vụ cho năm thiết bị mà detector chưa nhận ra được, nên khách gửi ảnh chúng lên thì hệ thống phải hỏi lại thiết bị nào, dù bên vận hành nhận sửa.

| thư mục | thiết bị | dịch vụ đã có trong Backend |
| :--- | :--- | :--- |
| `induction_hob` | Bếp từ | `SUA_BEP_TU` |
| `dishwasher` | Máy rửa bát | `SUA_MAY_RUA_CHEN` |
| `clothes_dryer` | Máy sấy quần áo | `VE_SINH_MAY_SAY` |
| `water_purifier` | Máy lọc nước | `LAP_MAY_LOC_NUOC` |
| `smart_lock` | Khoá cửa thông minh | `SUA_KHOA_THONG_MINH`, `MO_KHOA_KHAN_CAP` |

## Đã làm

Tạo năm thư mục trong `D:\anh-fixhome` kèm `_HUONG_DAN.md` theo đúng khuôn của mười bảy thư mục cũ: bỏ ảnh gì vào, không bỏ gì vào, và hay bị nhầm với cái gì.

Mục "hay bị nhầm" quan trọng hơn vẻ ngoài của nó. Bếp từ nhầm với bếp gas, máy rửa bát nhầm với máy giặt, máy sấy cũng nhầm với máy giặt, máy lọc nước nhầm với cây nước nóng lạnh, khoá thông minh nhầm với chuông cửa có hình. Năm cặp này là nơi bộ nhận diện sẽ sai nếu dữ liệu không tách bạch, và ba trong năm cặp liên quan tới thiết bị đã có sẵn trong bộ cũ — tức là thêm lớp mới có thể làm lớp cũ tệ đi nếu ảnh lẫn nhau.

Thêm năm hạng mục vào `PLAN` của `_tai_anh.py`, mỗi hạng mục mười ba tới mười bốn từ khoá bám theo mục "bỏ ảnh gì vào đây" và né mục "không bỏ vào đây".

## Còn phải làm

Gán nhãn. Ảnh tải về chưa có hộp bao, và `tools/autolabel.py` dùng YOLO-World gán nhãn theo mô tả bằng chữ — đây là lý do `yolov8s-worldv2.pt` và CLIP được giữ lại khi dọn thư mục trọng số.

Rà tay phần gán nhãn của năm cặp dễ nhầm ở trên. Máy gán nhãn không phân biệt được máy giặt với máy sấy tốt hơn con người.

Train lại toàn bộ hai mươi hai lớp, không phải train thêm năm lớp lên mô hình cũ. Thêm lớp vào một mô hình đã train là việc phải làm lại từ đầu với tập dữ liệu gộp.

Đo lại theo từng lớp như `DETECTOR-ACCURACY.md`, và so với con số cũ. Điều cần nhìn không phải là năm lớp mới đạt bao nhiêu, mà là **mười bảy lớp cũ có tụt không** — đặc biệt máy giặt, bếp gas và ấm siêu tốc, ba lớp có hàng xóm mới ở ngay cạnh.

Viết tri thức cho năm thiết bị mới: bệnh, triệu chứng theo lời khách, giá. Không có phần này thì detector nhận ra bếp từ rồi hệ thống vẫn không biết nói gì về nó.

## Một điều nên cân nhắc trước khi bỏ công

Bộ nhận diện hiện đạt 74% trên mười bảy lớp, và bốn lớp yếu nhất — bóng đèn 42%, bồn rửa 55%, vòi nước 60%, ống nước 60% — đều đang kéo con số ấy xuống. Thêm năm lớp nữa mà không chữa bốn lớp cũ thì bộ dữ liệu to hơn và mô hình vẫn yếu ở đúng chỗ nó đang yếu.

Nếu chỉ chọn được một việc, chữa bốn lớp cũ đáng giá hơn, vì chúng nằm trong luồng khách dùng hằng ngày còn năm lớp mới là mở rộng phạm vi.
