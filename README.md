<h1 align="center">FixHome — AI Service</h1>

> Ngữ cảnh hiện hành của repo (luồng, hợp đồng, quyết định, việc đang dở) nằm ở [`docs/CONTEXT.md`](docs/CONTEXT.md); khi file này lệch với code hoặc với CONTEXT.md, CONTEXT.md và code là chuẩn.

<p align="center">
  <strong>Chẩn đoán sơ bộ thiết bị gia dụng từ ảnh và lời kể của khách, và trả lời câu hỏi về FixHome</strong><br>
  <em>Tự host hoàn toàn. Không gọi API AI của bên thứ ba nào. Chỉ gợi ý, không quyết định nghiệp vụ.</em>
</p>

<p align="center">
  <code>YOLO11s · 22 thiết bị</code> ·
  <code>Qwen3.5-9B chỉ chữ trên vLLM 0.33</code> ·
  <code>135 thẻ lỗi · 988 đoạn hỏi đáp</code> ·
  <code>một card 24GB (FP8) hoặc 16GB (AWQ)</code>
</p>

---

## Hai engine, một API

Engine chọn bằng `AI_ENGINE`; engine nào cũng nằm sau `app/services/ai_provider.py` nên Backend không thấy khác biệt.

| `AI_ENGINE` | Là gì | Dùng khi |
|---|---|---|
| `chat2` | **đường chính từ 06/11/2026** (PO chốt): YOLO11s nhận thiết bị, Qwen3.5-9B đọc cả cuộc trò chuyện cùng thẻ lỗi của đúng thiết bị, code quyết hỏi hay chốt | mặc định trong image serve |
| `local` | pipeline cũ dẫn bằng truy hồi chữ (`app/services/pipeline/`), Qwen2.5-VL-3B viết lời | giữ lại để so sánh, không còn là đường chính |
| `mock` | câu trả lời cố định | test giao diện, CI |

Chi tiết thiết kế, prompt, schema và toàn bộ số đo của chat2: [docs/CHAT-BRAIN-V2.md](docs/CHAT-BRAIN-V2.md).

## chat2: mỗi phần làm đúng một việc

| Phần | Làm gì | Không được làm |
|---|---|---|
| YOLO11s (`detector-v2-yolo11s`) | đọc ảnh, ra loại thiết bị | đặt tên bệnh |
| Router (`brain.py`) | mỗi tin: thiết bị khách nhắc (tối đa 3) và ý định `repair`, `service`, `question`, `book`, `greeting`, `offtopic` | chẩn đoán |
| Qwen3.5-9B (tắt ảnh, tắt suy nghĩ) | đọc cả cuộc chat cùng thẻ lỗi, điền nhu cầu, loại nhu cầu, mã lỗi, mã dịch vụ theo **JSON schema của vLLM** (enum đúng các mã của thiết bị đó) | xem ảnh, tự nghĩ ra mã, giá, tên dịch vụ |
| Code (`brain._decide`, `provider.py`) | quyết hỏi hay chốt: khách đã kể hiện tượng, hư hại hay xin việc thì chốt; chưa kể gì mới hỏi **một** câu kèm 2–4 nút (`clarification.answerOptionsVi`), tối đa 2 câu mỗi cuộc | |
| Hỏi đáp (`answer.py`) | câu không phải chẩn đoán: chọn mục trong 988 đoạn của `knowledge_index.json` theo mục lục, chép câu bằng chứng rồi mới trả lời, kiểm lại câu trả lời với tài liệu | khẳng định điều tài liệu không có |
| Câu bác (`pushback.py`, 12/11/2026) | "sai rồi", "không phải bệnh đó", "...chứ không phải" được đọc **bằng code**: lỗi bị bác ra khỏi danh sách chọn cho cả cuộc chat, lời khách nói sau câu bác dẫn lượt chọn kế tiếp, trả `customerDisagreed` kèm `restVi` (lời khách bỏ câu bác, Backend dùng làm mô tả cho thợ) | coi "không dùng được nữa", "chưa dùng lần nào" là câu bác |

Tên tiếng Việt, mã dịch vụ, giá và mức khẩn cấp lấy từ `app/data/` và danh mục của Backend (`BACKEND_CATALOG_URL`), không lấy từ chữ tự do của mô hình. Giá ước tính: thấp là giá dịch vụ đúng như form đặt lịch hiện, cao là giá dịch vụ cộng linh kiện lỗi đó hay phải thay theo giá bán FixHome (`GET /api/v1/parts/prices` của Backend). Câu trả lời 1–2 câu; tên dịch vụ và giá không nhắc lại trong câu vì web hiện trên thanh đặt lịch.

### Thẻ lỗi thay cho truy hồi khi chẩn đoán

Một thiết bị có tối đa 12 lỗi nên mô hình được xem **đủ** các lỗi của thiết bị đó, không phải một danh sách rút gọn bằng chữ trùng. Mỗi lỗi là một thẻ trong `app/data/fault_cards.json` (135 thẻ), sinh từ 168 tài liệu ở `app/data/knowledge/` bằng `tools/build_fault_cards.py`: khách hay tả thế nào, khi nào **không** phải lỗi này, câu hỏi quyết định, cách tách với lỗi dễ nhầm. Sửa tài liệu thì chạy lại công cụ; `tests/test_chat2.py` báo khi thẻ cũ hơn tài liệu.

### Luật an toàn và câu chữ do code viết

- Lỗi rủi ro cao (rò gas, chập điện...) có bước an toàn đặt **lên đầu** câu trả lời. Giật điện, tê tay luôn có bước ngắt aptomat; dây điện hở lõi, chuột cắn luôn có bước rút phích và không đoán bệnh máy.
- Câu khách cố lái trợ lý ("bỏ qua mọi hướng dẫn"...) nhận câu cố định, không hỏi mô hình.
- Câu chốt không được nói "em cử thợ", "em chuyển thông tin" vì trợ lý không đặt lịch thay khách. Câu mô hình nói ngược lời khách ("không mát" khi khách nói "vẫn mát") được code viết lại.
- Máy ngoài danh mục (máy sấy tóc, nồi cơm điện, máy lọc không khí...) được nói thẳng là FixHome chưa nhận.
- Đơn cũ của khách (`pastJobs`): đơn đã xong nói "đã sửa ngày…", đơn chưa làm nói "đang có lịch ngày…".

## Số đo hiện tại

**Chat2, 707 ca cố định** (`tools/eval_chat2.py`), RTX A6000, FP8, adapter `chat2-pick-v2` chỉ cho lượt chẩn đoán, mỗi ô một lần chạy:

| | Model gốc | Có adapter `chat2-pick-v2` |
|---|---|---|
| Clear (515): đúng / sai mà chắc | 89,5% / 9,5% | 91,1% / 8,5% |
| Vague hỏi lại (66) / service (60) | 98,5% / 98,3% | 100% / 100% |
| Scripted (17) / offtopic (49) | 17/17, 95,9% | 17/17, 95,9% |
| Khách giả lập (90 cuộc) | | 89/90 |
| Trễ p50 bộ 707 ca | 4,3 s | 4,4 s |

`clear` là câu đội viết, chưa phải câu khách thật; khách giả lập là chính model đang đo. Cách đo và các vòng trước: [docs/CHAT-BRAIN-V2.md](docs/CHAT-BRAIN-V2.md).

**Kiểm thật trên fixhome.sbs** (12/11/2026, GPU RTX 3090 thuê, bấm thật trên web bằng Playwright): 45/46 ca, gồm các lỗi BUG DETECTOR 19–23, 52–54, 63–66, 74 và các ca tương tự gõ có dấu, không dấu.

**Tải** (07/11, RTX 3090 FP8, `tools/load_test.py --mix`): 10 khách cùng lúc 0 lỗi, p95 8,9 s; 30 khách 0 lỗi, p95 21,9 s; 50 khách có 10/50 lượt quá 25 s. Một card phục vụ khoảng 30 cuộc chat cùng lúc.

**Detector-v2**: yolo11s, 22 lớp, 23.678 ảnh, 70 epoch trên RTX 3090 (3 giờ 20 phút, $0,72); gọi đúng tên thiết bị 85,7%, mAP50 / mAP50-95 (val) 0,820 / 0,715. Từng lớp, gồm ba lớp tụt: [docs/DETECTOR-V2.md](docs/DETECTOR-V2.md).

**Test**: `pytest` → **2.823 test** trong 57 file.

## Chạy tại máy, không cần GPU

Không có GPU thì detector và mô hình ngôn ngữ chạy bản giả, còn luật hỏi/chốt, câu bác, hỏi đáp chọn mục, giá và toàn bộ test vẫn chạy.

CI và ruff nhắm **Python 3.11** (`.python-version`); máy local chạy được trên 3.13.

```bash
py -3.13 -m venv .venv
.venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

Mở `http://127.0.0.1:8000/chat` để chat thử, `http://127.0.0.1:8000/health` để kiểm. Biến môi trường chỉ ghi tên ở `.env.example` và mục 5 của `docs/CONTEXT.md`.

Dịch vụ **từ chối khởi động nếu kho tri thức nạp về ít hơn 1.000 đoạn** (`app/main.py`), nên một lần triển khai thiếu dữ liệu không lặng lẽ chạy với bộ não rỗng.

Gate trước mỗi commit (giống CI):

```bash
ruff check app tests
pytest -q
python -m compileall -q app tests
```

## Chạy đầy đủ mô hình trên GPU thuê

Đọc **[docs/RENTING-A-GPU.md](docs/RENTING-A-GPU.md)** để biết máy nào và các cách máy thuê hỏng. Máy tính tiền theo giờ: **chỉ thuê khi PO cho phép, xong việc huỷ ngay và kiểm không còn máy nào**.

### 1. Image được build ở CI

| Image | Build khi | Nội dung |
|---|---|---|
| `ghcr.io/fixhome-sep490/fixhome-serve` | merge vào `main` đổi `app/**`, `docker/serve/**`, `requirements.txt`; hoặc chạy tay theo nhánh | vLLM 0.33 + Qwen3.5-9B + YOLO + API trong một container |
| `ghcr.io/fixhome-sep490/fixhome-trainer` | đổi `docker/train/**`, `requirements-*.txt` | môi trường train YOLO |

Image của `main` có tag `latest`. Muốn thử một nhánh chưa merge thì build image theo nhánh: `gh workflow run serving-image.yml --ref <nhánh>` (tag = tên nhánh, `/` thành `-`), chờ workflow xanh rồi mới thuê máy với tag đó; không thì máy chạy đúng code cũ. Chưa có workflow triển khai: dựng máy làm bằng công cụ ở bước 2.

### 2. Thuê và theo dõi

```bash
python tools/rent_gpu.py offers --min-cuda 13.0 --min-download 3000
python tools/rent_gpu.py serve --offer <id> [--image-tag <nhánh>]
python tools/rent_gpu.py address --instance <id>   # in ra AI_SERVICE_URL
python tools/watch_instance.py <id>                 # trạng thái vast.ai khi máy kẹt
python tools/rent_gpu.py logs --instance <id> --tail 80
python tools/rent_gpu.py status
```

- Card **từ 24GB** chạy `RedHatAI/Qwen3.5-9B-FP8-dynamic` và gắn adapter `chat2-pick-v2`; card **16GB** chạy `cyankiwi/Qwen3.5-9B-AWQ-4bit` (không adapter). Entrypoint tự chọn theo VRAM; đặt `VLM_MODEL_NAME` để ép một bản. FP8 đúng hơn rõ ở câu khách tả rõ (83,1% so với 75,9% ở lượt đo cùng code 06/11), nên ưu tiên card 24GB.
- `serve` tự từ chối máy CUDA dưới 13.0 (vLLM chết sau khi đã kéo image) và máy mạng dưới 3 Gb/s (image có một tầng lớn không resume được).
- Container tự kéo image, tải weights detector, Qwen và adapter từ Hugging Face, chạy vLLM ở loopback rồi mở API ở cổng 8000. Máy lên khi `/health` báo mô hình và detector đã gắn.
- Giá tham chiếu tháng 11/2026: RTX 3090 24GB khoảng $0,34–0,38/giờ; thường sẵn sàng sau 5–25 phút.

### 3. Đo, rồi huỷ

```bash
python tools/eval_chat2.py --base-url http://<máy>/v1 --model <tên> [--turn-model fixhome-fault] \
    --extra '{"chat_template_kwargs":{"enable_thinking":false}}'
python tools/rent_gpu.py destroy --instance <id>
python tools/rent_gpu.py status   # phải thấy: Nothing rented. No charges accruing.
```

> **Máy serve không tự huỷ** và không nên trông vào hẹn giờ tự tắt. Đo xong là `destroy`, rồi `status` để chắc không còn máy nào tính tiền.

## Train lại

- **Detector**: `python tools/rent_gpu.py train --offer <id 24GB> --epochs 70 --batch 48 --model yolo11s.pt --run-name <run>`. Máy train đẩy weights lên Hugging Face trước khi báo xong rồi tự huỷ; train tiếp từ weights cũ bằng `--resume-from`. Lấy weights về: `python tools/hub.py pull-weights --repo <repo> --run <run>`.
- **Adapter chat2**: `tools/chat2_lora/` (sinh dữ liệu bằng chính model đang chạy, train 1 epoch khoảng 50 phút trên A6000). So với model gốc cùng code bằng `eval_chat2.py --turn-model` trước khi đổi `SERVE_LORA_RUN`.

## API

Sáu endpoint, **chỉ Backend gọi**; web và mobile không gọi thẳng.

| | |
|---|---|
| `POST /api/v1/diagnosis/analyze` | lời kể + tối đa 3 ảnh base64 → chẩn đoán, `devices[]` (tối đa 3 máy), `recommendedServices`, `diagnosticState` |
| `POST /api/v1/diagnosis/analyze-upload` | như trên, multipart |
| `POST /api/v1/chat/ask` | câu hỏi tự do → trả lời có căn cứ, `ok` / `out_of_scope` / `general_knowledge` / `no_grounding` |
| `GET /api/v1/chat/acknowledgements` | câu chờ cho client hiện |
| `GET /api/v1/meta/catalog` | danh mục thiết bị và dịch vụ |
| `GET /health` | sống chưa, mô hình và detector đã gắn chưa |

Ngoài ra `GET /chat` là trang chat thử, không phải API. Tên trường camelCase, schema `extra="forbid"`. Giới hạn từng trường và các trường `diagnosticState`, `pastJobs`, `customerDisagreed`, `notesVi`: mục 5 của [docs/CONTEXT.md](docs/CONTEXT.md).

**Phiên chat**: id do server phát, client gửi rỗng lần đầu rồi gửi lại id trong phản hồi. Phiên giữ trong bộ nhớ tiến trình làm bộ đệm; bản chuẩn là `diagnosticState` Backend lưu và gửi lại mỗi lượt, nên restart không mất cuộc chat.

## Khi hỏng thì suy giảm, không chặn

Luật nghiệp vụ: **AI hỏng không được chặn luồng đặt lịch**.

- Mô hình quá `CHAT_TIMEOUT_SECONDS` hoặc lỗi → API trả `{ code, message, fallbackAllowed: true, suggestedActionVi }` với 503/504; Backend đổi thành câu trả lời dự phòng và khách vẫn chọn dịch vụ, đặt thợ được.
- Ảnh không đọc được thì bỏ qua ảnh đó, lời khách vẫn tính.
- Lỗi chưa chốt thì gợi ý dịch vụ sửa của chính thiết bị; không biết thiết bị thì hỏi.

## Bố cục

```
app/
  api/v1/endpoints/  diagnosis.py, chat.py, meta.py
  core/              cấu hình, ngưỡng
  schemas/           Pydantic, camelCase trên dây
  services/
    ai_provider.py   chọn engine theo AI_ENGINE
    chat2/           brain.py (router, prompt, schema, hỏi/chốt), provider.py (phiên, ảnh, map response),
                     answer.py (hỏi đáp), menu.py (lỗi, dịch vụ của một thiết bị), pushback.py (câu bác)
    pipeline/        engine local cũ: detector, truy hồi, Qwen client, hội thoại
  data/
    knowledge/       168 tài liệu tiếng Việt
    fault_cards.json, knowledge_index.json, device_catalog.json, service_catalog.json, ...
  web/chat.html      trang chat thử
docker/serve/        image serve (entrypoint chọn FP8 hay AWQ theo VRAM)
docker/train/        image train YOLO
tools/               rent_gpu, watch_instance, hub, eval_chat2, probe_chat2, sim_chat2, load_test, chat2_lora, ...
tests/               2.823 test, 57 file
docs/                CONTEXT, CHAT-BRAIN-V2, RENTING-A-GPU, DETECTOR-V2, hợp đồng với Backend
```

`.venv` chạy dịch vụ và test; `.venv-tools` chỉ có `vastai` và client Hugging Face (tách vì một gói công cụ từng nâng `starlette` làm hỏng `fastapi`).

Bộ ảnh huấn luyện không nằm trong git (giới hạn dung lượng của GitHub); dữ liệu ở Hugging Face Hub, còn `datasets/split.json` có trong git để số đo lặp lại được.

## Còn biết, chưa làm

- Khách tự chẩn đoán sai ("hết gas rồi, chảy nước tong tong") đôi khi được tin theo.
- Câu trả lời cho máy thứ hai trong một tin nhiều máy có lần lọt chữ không phải tiếng Việt; yêu cầu vệ sinh khi khách có đơn sửa cũ cùng máy vẫn kèm câu "lỗi cũ quay lại" (BUG DETECTOR 97, 98, tìm thấy 12/11).
- Chẩn đoán chỉ có ảnh, không có chữ, chưa chạy: schema bắt `description` ít nhất 1 ký tự.
- Chưa có xác thực giữa Backend và service; API và trang `/chat` mở công khai trên máy GPU khi đang thuê.
- 821 mục kho tri thức chờ thợ có nghề xác nhận, 36 giá chờ Admin duyệt: [docs/CAN-THO-XAC-NHAN.md](docs/CAN-THO-XAC-NHAN.md).
- Một số tài liệu trong `docs/` mô tả pipeline cũ và đã cũ: `DATASET-AND-TRAINING.md`, `KB-NEXT-STEPS.md`, `LIVE-RUN.md`, `CHATBOT-NEXT.md`.
