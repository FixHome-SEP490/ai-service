# Kết quả detector v1

Train ngày 16/09/2026. YOLOv8n, 100 epoch, 3,715 giờ trên một RTX 3090 thuê ở
vast.ai, hết khoảng 0,8 đô. Weights nằm ở `phamductoan3883/fixhome-detector`,
thư mục `detector-v1`.

Dữ liệu: 22.745 ảnh, 18.201 train, 2.297 val, 2.247 test. Không ảnh nào hỏng.
Tập test tách ra từ đầu bằng băm nội dung nên không lẫn với tập train.

## Hai con số, và đừng lẫn chúng

**mAP50 trên tập test: 0.756. mAP50-95: 0.623.** Đây là thước đo của bài toán
nhận diện: chấm cả việc gọi đúng tên lẫn khoanh đúng khung, ở mười ngưỡng
khắt khe dần.

**Tỉ lệ gọi đúng tên thiết bị: 85,3%.** Đây mới là thước đo của sản phẩm. Khách
chụp cái máy hỏng và muốn biết hệ thống có nhận ra nó không; không ai kiểm tra
khung có sát mép máy hay không.

Con số thứ hai luôn cao hơn con số thứ nhất, và đó là lý do phải nói rõ đang
trích con nào. Đo lại bất cứ lúc nào bằng:

    python tools/eval_detector.py --weights <best.pt> --out docs/detector-v1-accuracy.json

Chấm trên 1.719 trong 2.247 ảnh test. Số còn lại có nhiều hơn một vật trong
nhãn nên không chấm được thành một câu trả lời duy nhất.

## Từng lớp

| Lớp | Số ảnh | Đúng | Không thấy gì | Gọi sai | Tỉ lệ đúng |
|---|---|---|---|---|---|
| air_conditioner | 461 | 447 | 6 | 8 | 97,0% |
| washing_machine | 75 | 66 | 0 | 9 | 88,0% |
| television | 90 | 79 | 3 | 8 | 87,8% |
| ceiling_fan | 73 | 64 | 2 | 7 | 87,7% |
| kettle | 112 | 98 | 2 | 12 | 87,5% |
| electric_fan | 111 | 94 | 6 | 11 | 84,7% |
| refrigerator | 72 | 61 | 6 | 5 | 84,7% |
| gas_stove | 97 | 81 | 4 | 12 | 83,5% |
| faucet | 43 | 35 | 2 | 6 | 81,4% |
| water_heater | 53 | 41 | 1 | 11 | 77,4% |
| microwave_oven | 78 | 60 | 3 | 15 | 76,9% |
| toilet | 82 | 63 | 5 | 14 | 76,8% |
| power_outlet | 128 | 98 | 8 | 22 | 76,6% |
| sink | 59 | 45 | 2 | 12 | 76,3% |
| oven | 68 | 50 | 3 | 15 | 73,5% |
| water_pipe | 51 | 37 | 2 | 12 | 72,5% |
| light_bulb | 66 | 47 | 2 | 17 | 71,2% |

Cột "không thấy gì" tách riêng khỏi "gọi sai" vì hai lỗi đó dẫn tới hai hành vi
khác nhau. Không thấy gì thì hỏi khách chụp lại tấm khác. Gọi sai thì đẩy khách
sang nhầm dịch vụ mà vẫn tự tin.

## Lớp yếu và chúng nhầm sang đâu

**light_bulb, 71,2%** — nhầm sang television, toilet, ceiling_fan. Bóng đèn
trong ảnh thật thường nhỏ, gắn trên trần, ngược sáng, và cái model học được là
một vùng sáng chứ không phải một vật thể.

**water_pipe, 72,5%** — nhầm sang water_heater và faucet. Đường ống hiếm khi
đứng một mình trong khung hình; nó luôn nối vào một cái gì đó, và cái đó mới là
vật rõ ràng hơn.

**oven, 73,5%** — bảy lần nhầm thành microwave_oven. Đây là cặp đã biết trước và
đã ghi trong `device_catalog.json` là `confusable_with`. Một cái lò cửa kính đen
chụp chính diện thì thợ cũng phải đoán.

**power_outlet, 76,6%** — 22 lần gọi sai dù có tới 2.423 ảnh train, nhiều thứ
nhì. Số lượng không cứu được lớp này, vì ổ cắm nhỏ và chìm vào tường.

## Nên hiểu thế nào

Nhóm thiết bị lớn, hình dáng riêng biệt — máy lạnh, máy giặt, TV, tủ lạnh, quạt
— đều từ 84% trở lên, và máy lạnh đạt 97%. Đó là nhóm khách chụp nhiều nhất.

Nhóm vật nhỏ hoặc chìm vào nền — bóng đèn, đường ống, ổ cắm, chậu rửa — nằm
quanh 71–77%. Thêm ảnh sẽ giúp nhưng không giải quyết hết, vì giới hạn nằm ở
chính tấm ảnh.

Với các cặp dễ lẫn, cách rẻ nhất không phải là train tiếp mà là **hỏi khách một
câu**. "Cái này có đĩa xoay bên trong không?" tách lò vi sóng khỏi lò nướng
trong một lượt, chính xác hơn mọi thứ model làm được.

## Cảnh báo về chính những con số này

Tập test lấy từ cùng nguồn với tập train: ảnh sản phẩm chụp studio, nền sạch,
đủ sáng, chụp chính diện. Ảnh khách chụp trong nhà thật thì tối hơn, xiên hơn,
lẫn đồ đạc, có khi chỉ thấy một góc thiết bị.

**85,3% là trần, không phải kỳ vọng.** Con số thật trên ảnh khách sẽ thấp hơn,
và chưa ai biết thấp hơn bao nhiêu cho tới khi có bộ ảnh chụp tại nhà thật để đo.
