# Kết quả detector v2

Train ngày 18/09/2026. yolo11s, 70 epoch, 3,3 giờ trên một RTX 3090 thuê ở
vast.ai, hết 0,72 đô. Weights nằm ở `phamductoan3883/fixhome-detector`, thư
mục `detector-v2-yolo11s`.

Dữ liệu: 23.678 ảnh, 18.091 train, 2.808 val, 2.779 test, **22 lớp**. v1 biết
17 lớp; năm lớp thêm vào là bếp từ, máy rửa bát, máy sấy quần áo, máy lọc nước
và khoá cửa thông minh.

## Ba con số, và đừng lẫn chúng

**mAP50: 0,820. mAP50-95: 0,715.** Đo trên tập val ở epoch 70, là thước đo của
bài toán nhận diện: chấm cả gọi đúng tên lẫn khoanh đúng khung. v1 ghi 0,756 và
0,623, nhưng **hai cặp số đó đo trên hai tập khác nhau** — v1 trên tập test cũ
của nó — nên đừng trừ chúng cho nhau.

**Tỉ lệ gọi đúng tên thiết bị: 85,7%.** Đây là thước đo của sản phẩm.
Khách chụp cái máy hỏng và muốn biết hệ thống có nhận ra nó không; không ai
kiểm tra khung có sát mép máy hay không. Chấm trên 2.251 trong 2.779 ảnh
test — số còn lại có nhiều hơn một vật trong nhãn nên không chấm được thành một
câu trả lời duy nhất.

## So với v1, và vì sao phải tách làm hai bảng

v1 không có tên cho năm thiết bị mới nên **không thể chấm điểm trên chúng**. So
v2 với v1 trên cả 22 lớp là chấm v1 một bài nó chưa từng được giao. Bảng so
sánh thật nằm ở 17 lớp cả hai đều biết, trên đúng những tấm ảnh đó.

| | v1 | v2 | đổi | ảnh |
|---|---|---|---|---|
| 17 lớp cả hai đều biết | 83,9% | **86,2%** | +2,3% | 1.879 |
| 5 lớp mới | không đo được | **82,8%** | — | 372 |
| toàn bộ 22 lớp | — | **85,7%** | — | 2.251 |

Đo lại bất cứ lúc nào bằng:

    python tools/eval_detector.py --weights <best.pt> --split test --out docs/detector-v2-on-22class-test.json
    python tools/compare_detectors.py docs/detector-v1-on-22class-test.json docs/detector-v2-on-22class-test.json

## Từng lớp, 17 lớp cũ

| Lớp | Số ảnh | v1 | v2 | Đổi |
|---|---|---|---|---|
| faucet | 86 | 75,6% | 90,7% | +15,1% |
| water_pipe | 87 | 63,2% | 78,2% | +14,9% |
| sink | 112 | 83,0% | 92,0% | +8,9% |
| oven | 68 | 73,5% | 80,9% | +7,4% |
| light_bulb | 94 | 66,0% | 72,3% | +6,4% |
| toilet | 82 | 76,8% | 82,9% | +6,1% |
| power_outlet | 128 | 76,6% | 82,0% | +5,5% |
| refrigerator | 72 | 84,7% | 88,9% | +4,2% |
| gas_stove | 97 | 83,5% | 87,6% | +4,1% |
| ceiling_fan | 73 | 87,7% | 87,7% | +0,0% |
| electric_fan | 111 | 84,7% | 84,7% | +0,0% |
| microwave_oven | 78 | 76,9% | 76,9% | +0,0% |
| television | 90 | 87,8% | 87,8% | +0,0% |
| water_heater | 53 | 77,4% | 77,4% | +0,0% |
| air_conditioner | 461 | 97,0% | 94,4% | −2,6% |
| kettle | 112 | 87,5% | 83,0% | −4,5% |
| washing_machine | 75 | 88,0% | 80,0% | −8,0% |

## Năm lớp mới

| Lớp | Số ảnh | Đúng | Không thấy gì | Gọi sai | Tỉ lệ đúng |
|---|---|---|---|---|---|
| smart_lock | 96 | 86 | 2 | 8 | 89,6% |
| dishwasher | 72 | 62 | 2 | 8 | 86,1% |
| induction_hob | 78 | 66 | 1 | 11 | 84,6% |
| water_purifier | 45 | 38 | 0 | 7 | 84,4% |
| clothes_dryer | 81 | 56 | 2 | 23 | 69,1% |

## Ba chỗ tụt, nói thẳng

**washing_machine: 88,0% xuống 80,0%.** Nhầm thành clothes_dryer 5, light_bulb 2, induction_hob 2.

**kettle: 87,5% xuống 83,0%.** Nhầm thành light_bulb 2, oven 2, toilet 2.

**air_conditioner: 97,0% xuống 94,4%.** Nhầm thành water_heater 4, water_purifier 3, dishwasher 3.

Cái tụt của máy giặt không ngẫu nhiên. Nó bị nhầm thành máy sấy quần áo, tức
thêm một lớp nhìn giống thì lớp cũ mất điểm — và chiều ngược lại còn rõ hơn,
máy sấy quần áo là lớp yếu nhất của v2 và nhầm thành máy giặt nhiều nhất.

Một cái máy giặt cửa ngang và một cái máy sấy cửa ngang trong ảnh là **cùng
một vật**: một hộp trắng có cửa tròn. Không có số epoch nào sửa được điều đó.
Chỗ này được xử lý ở tầng hội thoại chứ không phải ở detector: khi ảnh ra một
trong ba thiết bị máy giặt, máy sấy quần áo, máy rửa bát thì bot hỏi lại một
câu — máy nhà mình dùng để làm gì — và chỉ chẩn đoán sau khi khách trả lời.
Xem `app/data/knowledge/system/thiet-bi-de-nhin-nham.md`.

Máy lạnh tụt 2,6 điểm là cái giá đã lường trước của việc giới hạn 2.500 khung
cho lớp đó. Trước khi giới hạn, máy lạnh chiếm phần lớn dữ liệu và kéo trung
bình lên bằng cách lấn át các lớp khác.

## Theo nguồn ảnh

Cùng một bộ weights, chấm riêng trên từng nguồn. Khoảng cách giữa ảnh sản phẩm
trên sàn thương mại điện tử và ảnh chụp trong phòng thật là thứ không nhìn ra
được từ một con số tổng.

| Nguồn | mAP50 | mAP50-95 |
|---|---|---|
| roboflow | 0,904 | 0,738 |
| collected | 0,842 | 0,788 |
| open_images | 0,677 | 0,476 |

Nhóm `collected` là ảnh tự thu thập, khung do máy vẽ. Nó nằm **giữa** hai nhóm
kia: thấp hơn roboflow và cao hơn open_images. Nên chưa thấy bằng chứng rằng
ảnh tự thu thập là phần kéo mô hình xuống.

Đừng đọc bảng này thành ba mức độ khó của thực tế. Ba nhóm có thành phần lớp
khác hẳn nhau, nên chênh lệch giữa chúng lẫn cả chuyện nhóm nào chứa nhiều lớp
khó. Điều duy nhất kết luận được: chưa có lý do để đổ cho ảnh tự thu thập, và
cũng chưa đủ căn cứ để nói việc chụp ảnh thật đã xong.

v1 không đo được theo cách này: nó có 17 lớp còn nhãn trên đĩa đánh số tới 21,
nên Ultralytics dừng với `index 19 is out of bounds`. Phép đo so sánh được giữa
hai phiên bản là tỉ lệ gọi đúng tên ở bảng trên, vì nó chấm theo tên và bỏ qua
nhãn mà mô hình không có tên tương ứng.

## Còn lại gì

Máy sấy quần áo ở 69,1% là lớp đáng làm tiếp nhất, và cách làm là thêm ảnh chứ
không phải thêm epoch: lớp này chỉ có 81 ảnh test, ít nhất trong nhóm mới sau
máy lọc nước.

Đường cong đã phẳng. Mười epoch cuối chỉ thêm 0,0072 mAP50, và phần lớn trong
đó đến từ việc YOLO tự tắt mosaic ở mười vòng chót chứ không phải từ việc học
thêm; đoạn epoch 50 tới 60, khi mosaic còn bật, chỉ thêm 0,0049. Train thêm 30
vòng sẽ tốn thêm khoảng 1,5 giờ và 0,35 đô để đổi lấy chừng một phần nghìn.
Nếu vẫn muốn thì `tools/rent_gpu.py train --resume-from` chạy tiếp từ weights đã
publish, không phải train lại từ đầu.
