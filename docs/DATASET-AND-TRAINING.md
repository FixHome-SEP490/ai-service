# Dataset và huấn luyện detector

Tài liệu này ghi lại nguồn dữ liệu, quy trình dựng dataset và cách thuê máy để train. Mục đích là
lần sau thuê máy chỉ mất vài phút kéo image về chạy, không phải dựng lại môi trường từ đầu.

## 1. Nguồn dữ liệu

Detector có 15 lớp. Thứ tự ưu tiên theo công sức bỏ ra: dataset đã có sẵn bounding box đứng trước,
vì gán nhãn mới là phần tốn thời gian nhất chứ không phải tải ảnh.

### Open Images V7

Phủ 14 trên 15 lớp, bounding box do người vẽ tay, license CC-BY. Đây là nguồn chính và gần như không
tốn công nào. Tên lớp tương ứng ghi sẵn trong trường `open_images_class` của `app/data/device_catalog.json`.

Không có lớp máy lạnh, máy nước nóng, nồi cơm điện, cây nước.

### Roboflow Universe

Bù đúng chỗ Open Images thiếu, đều đã có box sẵn và đều CC BY 4.0. Danh sách đầy đủ kèm
số liệu ở bảng dưới, và được khai báo trong `tools/roboflow_sources.py` để tải bằng script.

Tải xuống cần API key Roboflow (miễn phí):

```bash
set ROBOFLOW_API_KEY=...
.venv-tools/Scripts/python tools/fetch_roboflow.py list
.venv-tools/Scripts/python tools/fetch_roboflow.py download --all
```

Gộp nhiều nguồn thì phải đổi tên lớp về đúng `device_type` trong catalog. Mỗi người đặt tên
một kiểu (`ac`, `air`, `Air-conditioner`), để nguyên là dataset có mấy lớp cùng nghĩa và mô hình
học lẫn lộn. Script đã làm sẵn việc đổi tên này.

### Kho dữ liệu đã khảo sát

Bảng này ghi lại những gì đã tìm được, để không phải đi tìm lại và để trích dẫn trong báo cáo.

| Nguồn | Ảnh | Lớp dùng được | Ghi chú |
| --- | --- | --- | --- |
| Open Images V7 | ~400/lớp lấy về | 14 lớp | box vẽ tay, CC-BY, nguồn chính |
| `hcmus-38m1y/air-conditioner-dr0fw` | 2314 | máy lạnh | nhóm Việt Nam |
| `leeji9689-gmail-com/ac-08nlv` | 888 | máy lạnh | |
| `yolo-uv06o/air-conditioning-dataset` | 164 | máy lạnh | |
| `bassam-xhjea/air-conditioner` | 86 | máy lạnh | |
| `rattapon-san-gmail-com/air-conditioner` | 20 | máy lạnh | quá nhỏ, chỉ gộp thêm |
| `house-hold-electronics/household-electronics-alry3` | — | ac, fan, light | |
| `evesyalari/household-appliances-3zh8e-e9y5g` | 3695 | máy nước nóng, lò vi sóng, ấm đun | 16 lớp, 13 lớp còn lại để dành future scope |
| `yolov5-dtypd/plug-socket-detect` | 318 | ổ cắm | phần cứng phương Tây |

Tất cả dataset Roboflow trên đều CC BY 4.0.

**Hai kết luận rút ra từ bảng này.**

Máy lạnh không còn là vấn đề. Cộng các nguồn lại được hơn 3400 ảnh có box sẵn, nhiều hơn mức cần. Ảnh cào thêm chỉ còn vai trò thu hẹp domain gap chứ không phải để đủ số lượng.

Ổ cắm điện thì ngược lại, và đây là lớp đáng lo nhất. Ngoài Open Images ra chỉ tìm được một dataset 318 ảnh, mà cả hai đều là phần cứng phương Tây. Vừa ít vừa lệch. Toàn bộ phần ổ cắm kiểu Việt Nam phải tự cào và tự chụp, nên mục tiêu 600 ảnh cho lớp này là có lý do chứ không phải tùy tiện.

### Dự kiến độ chính xác

Những con số dưới đây là **ước lượng để biết khi nào nên lo**, không phải kết quả đo được. Số thật chỉ có sau khi train và đo trên test split.

Với YOLOv8n, 15 lớp, khoảng 300-500 ảnh mỗi lớp:

| Đo trên | mAP50 | Top-1 loại thiết bị |
| --- | --- | --- |
| Ảnh cùng nguồn với tập train | 0.75 – 0.90 | 0.85 – 0.95 |
| Ảnh khách hàng chụp thật | 0.55 – 0.75 | 0.70 – 0.85 |

Chên lệch giữa hai dòng chính là domain gap. Nếu số trên test set tự chụp tụt quá 15 điểm so với val thì vấn đề nằm ở dữ liệu chứ không phải ở mô hình, và cách sửa là bổ sung ảnh thật chứ không phải tăng epoch.

Top-1 luôn cao hơn mAP vì pipeline chỉ cần biết đó là thiết bị gì, không cần khung thật khít. Box hơi lệch vẫn crop ra đúng thiết bị cho Qwen đọc.

Dự đoán theo từng lớp:

Lên cao nhất là tủ lạnh, máy giặt, bồn cầu, tivi, máy lạnh. Vật to, hình dạng đặc trưng, khó nhầm với thứ khác.

Thấp hơn là ổ cắm, bóng đèn, vòi nước. Vật nhỏ, chiếm ít pixel, hình dạng đa dạng.

Các cặp dễ nhầm cần theo dõi riêng trên confusion matrix: lò nướng với lò vi sóng là cặp nặng nhất, sau đó là bồn rửa với vòi nước (thường nằm chung một khung hình), quạt trần với quạt cây.

Ba cách hạ rủi ro đã có sẵn trong hệ thống. Nhầm trong cùng một nhóm dịch vụ thì hậu quả nhẹ, ví dụ nhầm bồn rửa thành vòi nước vẫn ra thợ nước. Ngưỡng tin cậy thấp thì trả `needs_clarification` chứ không đoán bừa. Và mô tả của khách vẫn dẫn được tới đúng bệnh ngay cả khi detector nhầm, vì truy xuất triệu chứng không phụ thuộc vào ảnh.

### Vì sao không cào ảnh từ công cụ tìm kiếm

Đã thử và đã bỏ. Công cụ cào dựng trên `icrawler` chạy trơn tru, báo thành công, và trả về ảnh
không liên quan. Truy vấn "ổ cắm điện Panasonic" cho ra poster đồ án kiến trúc nhà máy ô tô và một
đĩa gà rán. Truy vấn đối chứng bằng tiếng Anh "electrical wall socket" cho ra hộp mô hình máy bay
ném bom Thế chiến II.

Nguyên nhân không nằm ở tiếng Việt. Kiểm tra trực tiếp cho thấy trình phân tích trang của Google
không còn đọc được kết quả nào, còn Bing thì trả nội dung không liên quan cho client không phải
trình duyệt. Tiêu đề trang Bing trả về vẫn đúng tiếng Việt, nghĩa là truy vấn tới nơi, nhưng nội
dung thì không phải thứ đã hỏi.

Điều nguy hiểm là **không có lỗi nào được báo**. Script chạy hết, đếm ra hàng trăm ảnh, ghi vào
thư mục. Chỉ khi mở ảnh ra xem mới biết. Một công cụ cào âm thầm trả sai dữ liệu còn tệ hơn là
không có, vì sai lầm chỉ lộ ra sau khi đã train xong.

Còn lại hai đường, và đường thứ nhất mới là đường nên đi.

`tools/collect_images.py import` nạp ảnh tự chụp từ một thư mục. Với các lớp đang thiếu thì đây
không phải phương án chữa cháy mà là dữ liệu tốt hơn: một cái ổ cắm chụp trong hành lang thật dưới
ánh sáng thật chính là miền dữ liệu mà detector sẽ phải làm việc, còn ảnh catalogue của đúng cái ổ
cắm đó thì không.

`tools/collect_images.py fetch` dùng API tìm kiếm trả phí, thứ này trả kết quả thật. Tuỳ chọn, tốn
tiền, và thứ nó trả về vẫn là ảnh sản phẩm. Cần biến môi trường `SERPER_API_KEY`. Phần này **chưa
được kiểm chứng** trong repo vì không có khoá.

### Ảnh tự chụp

Bắt buộc, nhưng số lượng ít. Ảnh công khai phần lớn là ảnh sản phẩm chụp studio nền trắng đủ sáng,
còn ảnh khách hàng thật thì tối, chụp nghiêng, chụp sát, nền lộn xộn. Khoảng cách này gọi là domain
gap và là nguyên nhân phổ biến nhất khiến mô hình đẹp trên giấy nhưng hỏng lúc demo.

Mỗi lớp 30-40 tấm chụp trong nhà thật. **Toàn bộ test set phải là ảnh tự chụp.** Trộn ảnh studio vào
test thì con số accuracy báo cáo là con số ảo, và người chấm có kinh nghiệm sẽ hỏi đúng câu đó.

## 2. Môi trường

**Phải dùng hai virtualenv riêng.** FiftyOne kéo theo `starlette` phiên bản mới hơn nhiều so
với phạm vi FastAPI cho phép, nên cài chung một chỗ là service hỏng ngay. Đây không phải
lỗi của ai cả, chỉ là hai thứ phụ thuộc vào cùng một thư viện ở hai mốc khác nhau.

```bash
# venv cua service, dung de chay va test
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt

# venv rieng cho tooling: fiftyone, gradio, icrawler
python -m venv .venv-tools
.venv-tools/Scripts/pip install -r requirements-tools.txt
```

Cả hai thư mục đều nằm trong `.gitignore`. Mọi lệnh ở mục dưới chạy bằng `.venv-tools`.

## 3. Quy trình dựng dataset

```bash

# 1. Xem lớp nào có sẵn, lớp nào phải tự thu
python tools/build_dataset.py report

# 2. Tải các lớp có trong Open Images, box có sẵn
python tools/build_dataset.py download --limit-per-class 400

# 3. Cào ảnh cho các lớp đặc thù Việt Nam
python tools/collect_images.py plan
python tools/collect_images.py import --device power_outlet --from <folder>
python tools/collect_images.py stats

# 4. Sinh box nháp cho ảnh cào, rồi sửa lại
python tools/autolabel.py run --all
python tools/autolabel.py review --device power_outlet
python tools/autolabel.py promote --device power_outlet

# 5. Xuất dataset YOLO với split cố định
python tools/build_dataset.py export --out datasets/fixhome --include-reviewed
```

### Vì sao có bước sinh box nháp

Vẽ tay 1400 box mất khoảng mười giờ bấm chuột liên tục. Một mô hình nhận diện theo từ khoá mở
(open-vocabulary) nhận prompt bằng chữ, không cần train, và vẽ sẵn phần lớn box đủ gần để việc còn
lại chỉ là sửa thay vì vẽ. Thời gian rút xuống còn tính bằng phút cho mỗi trăm ảnh.

Nhưng **không được bỏ bước duyệt lại**. Box tự sinh sai đủ thường xuyên, và cái sai của nó có hệ
thống chứ không ngẫu nhiên, nên không tự triệt tiêu nhau. Bỏ qua bước duyệt là dạy detector học
đúng những lỗi của mô hình kia.

Ngưỡng tin cậy để thấp có chủ đích. Một box thừa chỉ tốn một phím xoá, còn một box thiếu thì phải
tự mắt phát hiện, tốn hơn nhiều.

### Hai quy tắc script tự ép

Ảnh trùng hoặc gần trùng được gom theo hash nội dung và **luôn nằm cùng một split**. Nếu một ảnh
lọt sang cả train lẫn test thì accuracy báo cáo bị thổi phồng mà không ai nhìn ra.

Split được ghi ra `datasets/split.json` và dùng lại ở các lần sau. Nhờ vậy số đo giữa hai lần train
mới so sánh được với nhau. File này được commit, còn ảnh thì không.

## 4. Thuê máy và train

Ý tưởng: máy thuê là thứ dùng một lần. Nó xuất hiện, làm đúng một việc, rồi bị huỷ. Cho nên mọi thứ
tốn thời gian cài đặt nằm trong Docker image, còn dữ liệu và kết quả thì kéo vào lúc chạy và đẩy ra
lúc xong. Mất máy chỉ mất vài phút gần nhất.

### Chuẩn bị một lần duy nhất

**Image được build trên GitHub, không build trên máy cá nhân.** Ba lý do: image khoảng bảy
gigabyte vì nền CUDA, nên đẩy lên từ mạng nhà lâu hơn build rất nhiều; không ai cần cài Docker
để tạo ra nó; và kết quả tái lập được vì luôn build từ bản checkout sạch.

Workflow `.github/workflows/trainer-image.yml` tự chạy khi `docker/train/` hoặc danh sách thư
viện thay đổi, và có thể bấm chạy tay từ tab Actions. Nó đẩy image vào GHCR bằng token
GitHub cấp sẵn cho job, nên **không cần lưu credential của registry ở bất kỳ đâu**, và cũng
không cần tài khoản Docker Hub.

Sau lần build đầu, vào phần Packages của repository để đặt package thành public một lần.
Máy thuê sau đó kéo về được mà không phải đăng nhập.

Dataset đưa lên Hugging Face Hub, một lần:

```bash
.venv-tools/Scripts/python tools/hub.py whoami
.venv-tools/Scripts/python tools/hub.py push-dataset --repo <user>/fixhome-devices
```

GitHub không dùng được cho dataset: chặn file trên 100 MB, khuyến nghị repo dưới một
gigabyte, và Git LFS bản miễn phí chỉ có một gigabyte lưu trữ cùng một gigabyte băng thông mỗi
tháng, một lần clone là hết. Hub sinh ra cho việc này và miễn phí.

### Mỗi lần thuê máy

Thuê máy trên vast.ai, chọn image `ghcr.io/fixhome-sep490/fixhome-trainer:latest`, rồi:

```bash
docker run --gpus all --rm \
  -e HF_TOKEN=... \
  -e HF_DATASET_REPO=<user>/fixhome-devices \
  -e HF_WEIGHTS_REPO=<user>/fixhome-detector \
  -e EPOCHS=100 -e BATCH=16 \
  ghcr.io/fixhome-sep490/fixhome-trainer:latest train
```

Container tự kéo dataset, train, đánh giá trên test split, rồi đẩy weights và biểu đồ lên
Hugging Face. Xong thì huỷ máy, không cần giữ lại gì.

Nếu quên đặt `HF_WEIGHTS_REPO`, script báo rõ là weights chỉ nằm trong máy và phải tự
copy ra trước khi huỷ.

Kéo weights về máy mình sau khi train:

```bash
.venv-tools/Scripts/python tools/hub.py list-runs --repo <user>/fixhome-detector
.venv-tools/Scripts/python tools/hub.py pull-weights --repo <user>/fixhome-detector --run <ten-run>
```

### Cấu hình nên thuê

| Việc | Card | Disk | RAM | Thời gian | Giá tham khảo |
| --- | --- | --- | --- | --- | --- |
| Train detector | RTX 3060 12GB | 60GB | 16GB | ~1 giờ | 0.08–0.12 USD/giờ |
| Serve cả pipeline | RTX 3060 12GB | 40GB | 16GB | theo nhu cầu | 0.06–0.10 USD/giờ |

Cả ba thành phần nằm chung một card 12GB được: Qwen2.5-VL-3B AWQ khoảng 5-6GB gồm KV cache, YOLOv8n
khoảng 1GB, embedding cho retrieval khoảng 1GB. Không cần load/unload luân phiên, vì làm vậy chỉ
thêm vài giây độ trễ mỗi lần đổi.

Card 24GB chỉ cần nếu về sau thực sự fine-tune Qwen. Hiện tại không có kế hoạch đó, vì YOLO đã lo
phần nhận diện và bảng tri thức lo phần ngôn từ, nên fine-tune VLM không còn đối tượng để dạy.

### Vì sao ghim phiên bản

Image ghim cứng torch, CUDA và ultralytics. Một image tự nâng cấp torch giữa hai lần thuê sẽ cho ra
số đo không so sánh được với lần trước, đúng thứ mà một thí nghiệm có thể tái lập phải tránh.

## 5. Báo cáo kết quả

Luôn chạy baseline YOLOv8n chưa fine-tune trước để có mốc so sánh. Nếu bản train không hơn baseline
thì đừng deploy, và bản thân kết quả đó cũng đáng viết vào báo cáo.

Số đo chính là mAP50-95 và accuracy trên test split, kèm confusion matrix. Confusion matrix chỉ ra
cặp nào hay nhầm để biết cần bổ sung ảnh ở đâu. Cặp lò nướng với lò vi sóng gần như chắc chắn dính.

Test split chỉ dùng để báo cáo, không bao giờ dùng để chọn checkpoint. Chọn bằng val.
