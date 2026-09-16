<h1 align="center">FixHome — AI Service</h1>

<p align="center">
  <strong>Chẩn đoán sơ bộ thiết bị gia dụng từ ảnh và mô tả của khách</strong><br>
  <em>Tự host hoàn toàn. Không gọi API của bên thứ ba nào.</em>
</p>

---

## Ba phần, mỗi phần một việc

**YOLOv8n nhận ra vật.** Ảnh vào, nó nói đây là máy lạnh hay tủ lạnh, và cắt ra
vùng thiết bị. Đã train trên 22.745 ảnh, 17 loại thiết bị. Gọi đúng tên thiết bị
**85,3%** trên tập test — chi tiết từng lớp ở [docs/DETECTOR-V1.md](docs/DETECTOR-V1.md).

**RAG tra bảng bệnh.** Lời khách kể được đối chiếu với 621 cách diễn đạt triệu
chứng trong bảng 108 bệnh, rút ra một danh sách ngắn các bệnh khả nghi cho đúng
loại thiết bị đó.

**Qwen2.5-VL chọn trong danh sách.** Nó đọc ảnh cắt cộng lời khách rồi **chọn mã**
— không phải nghĩ ra bệnh, không phải viết câu cho khách. Nhiệt độ 0.

Rồi RAG dịch ngược mã sang tiếng Việt, ghép giá, việc nên làm, mức khẩn cấp.

**Mọi câu tiếng Việt khách đọc đều lấy từ bảng bệnh, không phải model tự viết.**
Đó là luật xuyên suốt: model được phép chọn, không được phép nói. Mã nào không
có trong danh sách bị loại trước khi tới khách.

## Vì sao chia việc như vậy

Đã đo: Qwen gọi ảnh máy lạnh là "đèn sưởi", và khi bắt nó phân biệt lò vi sóng
với lò nướng trên 12 ảnh thì nó trả lời **giống hệt nhau cả 12 lần**, đảo thứ tự
lựa chọn cũng không đổi. Nó không phân biệt được. YOLO làm việc đó tốt hơn hẳn.

Ngược lại YOLO không đọc được chữ và không hiểu câu "máy chạy cả ngày không mát".
Hai mô hình bù cho nhau đúng chỗ mỗi cái yếu.

## Khi không chắc thì hỏi, không đoán

Bốn cặp thiết bị mà **người nhìn ảnh cũng nhầm**: lò vi sóng với lò nướng, chậu
rửa với vòi nước, quạt trần với quạt điện, ổ cắm với bóng đèn.

Gặp một trong bốn cặp đó, AI hỏi lại khách **một câu về thứ họ nhìn thấy được**:

> Bên trong lò có đĩa thuỷ tinh tròn xoay khi chạy không ạ?

Chứ không hỏi "là lò vi sóng hay lò nướng" — đó chính là câu khách không trả lời
được nên mới phải nhờ AI.

Câu này hỏi **bất kể độ tin cậy cao hay thấp**, vì ca nguy hiểm là detector tự
tin mà sai. Hỏi đúng một lần mỗi phiên, không hỏi nếu khách đã tự nói, không hỏi
lại nếu câu trả lời không giải quyết được gì.

## Trí nhớ hội thoại

Gửi `sessionId` thì các lượt nối vào nhau. Phiên nhớ ba thứ: thiết bị đã nhận ra
từ ảnh, toàn bộ lời khách đã nói, và những câu đã hỏi rồi.

Không có nó thì mỗi tin nhắn là một người lạ — khách gửi ảnh, bị hỏi lại, trả lời
"mới vệ sinh tháng trước", và tin nhắn đó tới nơi với không ảnh và bốn chữ.

Lưu trong bộ nhớ tiến trình. Restart là mất, hai worker không dùng chung. Sai cho
production, đúng cho hiện tại — đổi sang Redis chỉ cần thay `ConversationStore`.

## API

| Endpoint | Việc |
|---|---|
| `POST /api/v1/diagnosis/analyze` | Chẩn đoán, ảnh gửi dạng base64 hoặc data URI |
| `POST /api/v1/diagnosis/analyze-upload` | Cùng pipeline, ảnh gửi dạng multipart |
| `POST /api/v1/chat/ask` | Hỏi đáp chính sách, chỉ trả lời từ tài liệu đã truy xuất |
| `GET /api/v1/meta/catalog` | Danh mục thiết bị, nhóm dịch vụ, mã dấu hiệu |
| `GET /health` | Sống hay chết |

Tên trường trên dây là **camelCase**, trong Python là snake_case.

**Ảnh nhận vào**: JPEG, PNG, WebP. Tối đa 8MB một ảnh, 3 ảnh một yêu cầu, tự thu
nhỏ về cạnh dài 1024. **Chưa nhận HEIC** — đó là định dạng mặc định của iPhone,
nên app phải chuyển sang JPEG trước khi gửi.

Service **không bao giờ tải ảnh từ URL**, khách phải gửi thẳng bytes. Đó là cách
đơn giản nhất để không dính lỗ hổng SSRF.

**`includeTrace: true`** trả về đường đi của gói tin qua từng chặng — dùng cho
trang giám sát, không dùng cho khách.

## Khi hỏng thì suy giảm, không chặn

Model chết, hết giờ, trả JSON hỏng, trả mã không có thật — mỗi thứ đều thành một
câu hỏi lại khách chứ không thành exception. Lỗi nào không cứu được thì trả
`fallbackAllowed: true`, nghĩa là Backend cứ cho khách chọn dịch vụ thủ công.

**AI hỏng không được chặn luồng đặt lịch.** Đó là luật trong tài liệu nghiệp vụ.

## Giá

Sàn là tiền công thợ, trần là tiền công cộng ước tính linh kiện. Lấy từ hai bảng
thật: 18 dịch vụ ở mục 8.3.1 và bảng 791 linh kiện. Chi tiết và các đánh đổi ở
[docs/PRICING-DESIGN.md](docs/PRICING-DESIGN.md).

Khoảng giá **chỉ để khách quyết định có nên đặt lịch hay không**, không phải để
khách biết sẽ trả bao nhiêu. Báo giá chính thức do thợ lập sau khi kiểm tra.

## Chạy

```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Không có weights và không có VLM thì service vẫn chạy bằng stub, tiện cho CI và
cho Backend ghép nối. Có đồ thật thì:

```bash
YOLO_WEIGHTS_PATH=weights/detector-v1/.../best.pt
VLM_BASE_URL=http://<host>:<port>          # có hay không có /v1 đều được
```

Trang test và giám sát:

```bash
python tools/demo_app.py      # http://127.0.0.1:7860
```

Ba tab: chẩn đoán nhiều lượt giữ phiên, đường đi gói tin qua từng chặng, và hỏi
đáp chính sách.

## Hai môi trường ảo

`.venv` chạy service. `.venv-tools` chạy công cụ — FiftyOne kéo về một bản
starlette mới hơn FastAPI cho phép, nên gộp chung là hỏng service.

```bash
pip install -r requirements-tools.txt   # vào .venv-tools
pip install -r requirements-model.txt   # ultralytics + torch, khi cần weights thật
```

## Công cụ

| Lệnh | Việc |
|---|---|
| `tools/rent_gpu.py` | Thuê máy vast.ai, train, phục vụ Qwen, huỷ máy |
| `tools/hub.py` | Đẩy dataset, kéo weights qua HuggingFace |
| `tools/build_dataset.py` | Dựng dataset YOLO từ ảnh đã gom |
| `tools/eval_detector.py` | Đo tỉ lệ gọi đúng tên thiết bị, từng lớp |
| `tools/price_faults.py` | Tính khoảng giá cho 108 bệnh từ hai bảng |
| `tools/demo_app.py` | Trang test và giám sát |

## Dữ liệu

| File | Nội dung |
|---|---|
| `fault_knowledge_base.json` | 108 bệnh, 621 triệu chứng, 22 chính sách, 55 câu hỏi phân biệt |
| `device_catalog.json` | 17 thiết bị, tên tiếng Việt, cặp dễ lẫn, câu hỏi tách cặp |
| `labour_catalog.json` | 18 dịch vụ tiền công từ mục 8.3.1 |
| `parts_catalog.json` | 791 linh kiện kèm khoảng giá |
| `fault_pricing_map.json` | Mỗi bệnh trỏ tới mã tiền công và linh kiện đại diện |
| `service_mapping.json` | **Rỗng** cho tới khi Backend chốt mã dịch vụ |

Sửa bảng bệnh là sửa cách AI trả lời. Không cần train lại gì cả.

## Đang tắt, và vì sao

`VLM_REPORT_VISIBLE_CONDITIONS=false`. Đưa ảnh tủ lạnh mới tinh, Qwen báo thấy
nứt vỡ, rỉ sét, rò nước. Đưa mô tả **không kèm ảnh nào**, nó vẫn tả "bề mặt có
vết nứt và trầy xước".

Đoán sai mã bệnh là đoán sai về thứ không ai nhìn thấy. Bảo khách tủ lạnh nhà họ
bị nứt trong khi ảnh họ vừa chụp cho thấy nó lành là loại sai khác hẳn — **khách
kiểm tra được, và họ sẽ kiểm tra.**

Bật lại khi có ảnh hư hỏng thật để đo.

## Chưa làm

Nối bệnh sang mã dịch vụ — chờ Backend chốt catalog.

Nhận dạng hư hỏng qua ảnh — chờ ảnh thật.

Đọc thông số trên nhãn thiết bị, hướng dẫn thao tác qua ảnh chụp màn hình — xem
[docs/FUTURE-SCOPE.md](docs/FUTURE-SCOPE.md).
