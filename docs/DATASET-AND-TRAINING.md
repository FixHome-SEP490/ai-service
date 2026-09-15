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

Bù đúng chỗ Open Images thiếu, đều đã có box sẵn và đều CC BY 4.0:

| Dataset | Ảnh | Lớp dùng được |
| --- | --- | --- |
| `hcmus-38m1y/air-conditioner-dr0fw` | 2314 | máy lạnh |
| `house-hold-electronics/household-electronics-alry3` | — | `ac`, `fan`, `light` |
| `evesyalari/household-appliances-3zh8e-e9y5g` | 3695 | `hot water shower machine` (máy nước nóng), `microwave oven`, `super kettle` |

Dataset `evesyalari` đáng chú ý vì lớp `hot water shower machine` lấp được máy nước nóng, lớp duy
nhất trước đó không có nguồn nào. Nó còn 13 lớp khác nằm ngoài phạm vi hiện tại, giữ lại cho
future scope khi mở rộng lên 20-30 lớp.

Gộp nhiều nguồn thì phải đổi tên lớp về đúng `device_type` trong catalog. Mỗi người đặt tên một
kiểu, để nguyên là dataset có hai lớp cùng nghĩa và mô hình học lẫn lộn.

### Ảnh tự cào

Chỉ cào những lớp mà ảnh công khai lệch hẳn so với thực tế Việt Nam. Ổ cắm là ví dụ rõ nhất: ảnh
quốc tế phần lớn là ổ chân dẹt kiểu Mỹ và ổ tròn kiểu châu Âu, trong khi nhà ở Việt Nam dùng ổ đa
năng hai chấu. Mô hình train bằng ảnh kia sẽ nhận sai ngay lần đầu gặp ổ thật.

Danh sách và số lượng nằm trong `tools/crawl_images.py`, xem bằng `python tools/crawl_images.py plan`.
Từ khoá tìm kiếm để tiếng Việt, vì tìm bằng tiếng Anh sẽ ra đúng loại phần cứng không nên học.

### Ảnh tự chụp

Bắt buộc, nhưng số lượng ít. Ảnh công khai phần lớn là ảnh sản phẩm chụp studio nền trắng đủ sáng,
còn ảnh khách hàng thật thì tối, chụp nghiêng, chụp sát, nền lộn xộn. Khoảng cách này gọi là domain
gap và là nguyên nhân phổ biến nhất khiến mô hình đẹp trên giấy nhưng hỏng lúc demo.

Mỗi lớp 30-40 tấm chụp trong nhà thật. **Toàn bộ test set phải là ảnh tự chụp.** Trộn ảnh studio vào
test thì con số accuracy báo cáo là con số ảo, và người chấm có kinh nghiệm sẽ hỏi đúng câu đó.

## 2. Quy trình dựng dataset

```bash
pip install -r requirements-tools.txt -r requirements-model.txt

# 1. Xem lớp nào có sẵn, lớp nào phải tự thu
python tools/build_dataset.py report

# 2. Tải các lớp có trong Open Images, box có sẵn
python tools/build_dataset.py download --limit-per-class 400

# 3. Cào ảnh cho các lớp đặc thù Việt Nam
python tools/crawl_images.py plan
python tools/crawl_images.py fetch --all
python tools/crawl_images.py stats

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

## 3. Thuê máy và train

Ý tưởng: máy thuê là thứ dùng một lần. Nó xuất hiện, làm đúng một việc, rồi bị huỷ. Cho nên mọi thứ
tốn thời gian cài đặt nằm trong Docker image, còn dữ liệu và kết quả thì kéo vào lúc chạy và đẩy ra
lúc xong. Mất máy chỉ mất vài phút gần nhất.

### Chuẩn bị một lần duy nhất

```bash
docker build -f docker/train/Dockerfile -t <user>/fixhome-trainer:1.0 .
docker push <user>/fixhome-trainer:1.0

# Dataset để trên HuggingFace Hub, miễn phí, kéo về bằng một lệnh
huggingface-cli upload <user>/fixhome-devices datasets/fixhome --repo-type dataset
```

### Mỗi lần thuê máy

Thuê máy trên vast.ai, chọn image `<user>/fixhome-trainer:1.0`, rồi:

```bash
docker run --gpus all --rm \
  -e HF_TOKEN=... \
  -e HF_DATASET_REPO=<user>/fixhome-devices \
  -e HF_WEIGHTS_REPO=<user>/fixhome-detector \
  -e EPOCHS=100 -e BATCH=16 \
  <user>/fixhome-trainer:1.0 train
```

Container tự kéo dataset, train, đánh giá trên test split, rồi đẩy weights và biểu đồ lên
HuggingFace. Xong thì huỷ máy, không cần giữ lại gì.

Nếu quên đặt `HF_WEIGHTS_REPO`, script báo rõ là weights chỉ nằm trong máy và phải tự copy ra trước
khi huỷ.

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

## 4. Báo cáo kết quả

Luôn chạy baseline YOLOv8n chưa fine-tune trước để có mốc so sánh. Nếu bản train không hơn baseline
thì đừng deploy, và bản thân kết quả đó cũng đáng viết vào báo cáo.

Số đo chính là mAP50-95 và accuracy trên test split, kèm confusion matrix. Confusion matrix chỉ ra
cặp nào hay nhầm để biết cần bổ sung ảnh ở đâu. Cặp lò nướng với lò vi sóng gần như chắc chắn dính.

Test split chỉ dùng để báo cáo, không bao giờ dùng để chọn checkpoint. Chọn bằng val.
