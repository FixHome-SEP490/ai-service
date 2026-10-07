# Context repo ai-service — FixHome

> Cập nhật lần cuối: 2026-10-07 14:43 (UTC+7) · Người cập nhật (git): ToanAltF4 · Nhánh: docs/repo-context

## 0. Quy tắc cập nhật file này (bắt buộc)

File này là nguồn ngữ cảnh chung của repo cho cả dev lẫn AI agent. Đọc trước khi làm bất kỳ việc gì trong repo. Bốn repo `ai-service`, `backend`, `web`, `mobile` dùng chung một bộ quy tắc này; test `tests/test_context_doc.py` kiểm tra định dạng mỗi lần chạy `pytest` và trong CI, sai quy tắc là CI đỏ.

### Khi nào phải cập nhật

Cập nhật trong cùng PR với thay đổi, không để PR sau. Bắt buộc khi PR làm thay đổi một trong các thứ sau:

1. Tính năng hoặc luồng nghiệp vụ người dùng thấy được.
2. API, sự kiện realtime, enum, schema gửi qua lại giữa các repo.
3. Biến môi trường, cổng, cách chạy, cổng kiểm thử (gate), CI, Docker.
4. Migration hoặc cấu trúc dữ liệu.
5. Quyết định của PO hoặc luật nghiệp vụ.
6. Việc đang dở, rủi ro mới phát hiện, hoặc một mục ở phần 8 đã xong.

Sửa lỗi không đổi hành vi bên ngoài thì không bắt buộc. Không chắc thì cập nhật.

### Cách cập nhật

1. Sửa nội dung mục 1 đến 8 cho đúng hiện trạng. Viết lại câu cũ cho đúng, không chồng thêm ghi chú lên câu đã sai.
2. Sửa dòng `> Cập nhật lần cuối:` ở đầu file theo đúng mẫu:
   `> Cập nhật lần cuối: YYYY-MM-DD HH:mm (UTC+7) · Người cập nhật (git): <git user.name> · Nhánh: <nhánh>`
   Giờ là giờ Việt Nam lúc sửa, lấy bằng lệnh dưới đây (chạy được trên Windows, macOS, Linux; đừng dùng `TZ=... date` vì Git Bash trên Windows lặng lẽ trả giờ UTC):
   `node -e "console.log(new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date()))"`
   hoặc `python -c "from datetime import datetime,timezone,timedelta;print(datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d %H:%M'))"`.
   Tên lấy đúng chữ từ `git config user.name`. Nhánh lấy từ `git branch --show-current`.
3. Thêm một dòng lên đầu mục 9, cùng giờ và cùng tên với dòng đầu file:
   `- YYYY-MM-DD HH:mm (UTC+7) | <git user.name> | <nhánh hoặc PR #số> | <đã đổi gì trong context, một câu>`
4. Chạy `pytest tests/test_context_doc.py` trước khi commit.

### Viết gì và không viết gì

- Chỉ ghi điều đã kiểm chứng trong code, PR hoặc lần chạy thật. Điều chưa kiểm chứng ghi rõ `CHƯA KIỂM CHỨNG`.
- Repo là public. Tuyệt đối không ghi mật khẩu, khoá API, token, chuỗi kết nối có mật khẩu, địa chỉ IP máy chủ hay máy GPU, dữ liệu khách hàng. Biến môi trường chỉ ghi tên, không ghi giá trị. Test chặn các mẫu này.
- Không ghi ý kiến cá nhân, việc vặt, nhật ký làm việc hằng ngày, hay chỗ trống kiểu "để sau". Việc chưa làm ghi ở mục 8 với tên việc cụ thể.
- Không chép lại tài liệu khác; dẫn đường dẫn tới file đó.
- Tiếng Việt, câu ngắn. Tên kỹ thuật, tên file, tên API giữ nguyên tiếng Anh, đặt trong backtick.
- Không đổi tên, không xoá, không đổi thứ tự mười tiêu đề `##` số 0 đến 9; nội dung con dùng `###`. Không thêm tiêu đề `##` khác.
- Mục 9 mới nhất ở trên cùng, giữ tối đa 40 dòng; dòng cũ hơn thì xoá, lịch sử đã có trong git.
- File dài tối đa 700 dòng. Dài hơn thì rút gọn và dẫn link.

### Khi thay đổi chạm nhiều repo

Hợp đồng giữa các repo (mục 2 và mục 5) phải khớp nhau. Đổi API ở `backend` thì cập nhật context của `web`, `mobile` (và `ai-service` nếu liên quan) trong PR của từng repo đó, cùng ngày. Mục 2 của bốn repo giống nhau; sửa ở một repo thì sửa cả bốn.

### Với AI agent

Đọc file này trước, rồi `AGENTS.md`, rồi `docs/AI-TECHNICAL-GUIDE.md`. Không tạo file ngữ cảnh khác thay cho file này. Khi kết thúc việc, áp dụng đúng mục "Cách cập nhật" ở trên với tên git của máy đang chạy.

## 1. Repo này là gì trong FixHome

`ai-service` là FastAPI cung cấp AI gợi ý cho FixHome: chẩn đoán sơ bộ từ ảnh và mô tả, và chatbot tư vấn tiếng Việt. Tự host, không dùng API AI bên ngoài: bộ phát hiện thiết bị YOLO11s (detector-v2, 22 lớp) và Qwen2.5-VL chạy bằng vLLM trên máy GPU thuê. Chỉ `backend` gọi service này; `web` và `mobile` không gọi thẳng. Kết quả chỉ mang tính gợi ý, không bao giờ quyết định giao việc, báo giá hay trạng thái đơn.

## 2. Liên kết với các repo khác

FixHome gồm năm repo trong tổ chức GitHub `FixHome-SEP490`. Bốn repo mã nguồn có file context cùng cấu trúc:

| Repo | Vai trò | Nhánh tích hợp | Context |
| --- | --- | --- | --- |
| `backend` | NestJS, nguồn sự thật về nghiệp vụ, quyền và dữ liệu | `dev` | `https://github.com/FixHome-SEP490/backend/blob/dev/docs/CONTEXT.md` |
| `web` | Vue cho cả bốn vai trò; khu `/console` cho quản lý dịch vụ và admin | `dev` | `https://github.com/FixHome-SEP490/web/blob/dev/docs/CONTEXT.md` |
| `mobile` | Expo / React Native cho khách hàng và kỹ thuật viên | `dev` | `https://github.com/FixHome-SEP490/mobile/blob/dev/docs/CONTEXT.md` |
| `ai-service` | FastAPI, chẩn đoán từ ảnh và mô tả, chatbot tư vấn; chỉ mang tính gợi ý | `main` | `https://github.com/FixHome-SEP490/ai-service/blob/main/docs/CONTEXT.md` |
| `docs` | Tài liệu dự án | — | — |

Luồng gọi giữa các repo:

```text
web  ──┐  REST /api/v1 + Socket.IO (JWT)
       ├──────────────────────────────▶ backend ──HTTP──▶ ai-service (/api/v1/diagnosis/analyze, /api/v1/chat/ask)
mobile ┘                                   │
                                           ├──▶ Supabase PostgreSQL (TypeORM, migration); Supabase Storage (riêng ảnh KYC)
                                           ├──▶ Cloudinary (ảnh đại diện, ảnh booking, ảnh bằng chứng sửa chữa)
                                           ├──▶ VNPay (thanh toán hoá đơn, nạp ví) và payOS (chi tiền rút ví)
                                           ├──▶ MapTiler (gợi ý địa chỉ, đổi toạ độ ra địa chỉ)
                                           └──▶ Google OAuth (đăng nhập Google), SMTP (gửi OTP)
```

`web` hiển thị bản đồ bằng MapTiler; `mobile` dùng `react-native-maps`. Chat và gọi thoại dùng chung Socket.IO namespace `/chat` của `backend`; thông báo hiện chỉ đọc qua REST (chưa có đẩy realtime hay push).

Ba điều không đổi giữa các repo:

1. `web` và `mobile` không gọi thẳng `ai-service`, database hay cổng thanh toán; mọi thứ đi qua `backend`.
2. `backend` là nơi quyết định nghiệp vụ và phân quyền; kiểm tra phía client chỉ để trải nghiệm.
3. `ai-service` chỉ gợi ý. AI hỏng hoặc chậm không được chặn luồng đặt lịch; `backend` trả kết quả dự phòng.

Luật nghiệp vụ gốc nằm ở tài liệu dự án (bản chính thức của nhóm). Mâu thuẫn giữa code và tài liệu thì ghi vào mục 8 và hỏi PO, không tự quyết.

## 3. Trạng thái hiện tại

- Chẩn đoán: cổng chặn trước (không phải đồ gia dụng, lời chào, ngoài phạm vi, ý định đặt lịch), nhận diện thiết bị từ ảnh hoặc chữ hoặc phiên trước, truy hồi lỗi theo triệu chứng, Qwen chọn trong danh sách rút gọn, hỏi lại tối đa 2 lượt rồi dùng xếp hạng của truy hồi.
- Chatbot: trả `ok`, `out_of_scope`, `general_knowledge` hoặc `no_grounding`; có trả `recommendedServices`.
- Tên tiếng Việt, mã dịch vụ, giá và mức khẩn cấp lấy từ `app/data/`, không lấy từ chữ tự do của mô hình. Mã không có trong danh mục bị bỏ. Luôn kèm lời miễn trừ.
- Kho tri thức: 166 file markdown trong `app/data/knowledge/` (3319 đoạn), 134 lỗi ánh xạ tới 21 mã dịch vụ của `backend`, 827 linh kiện.
- Phiên trò chuyện lưu trong bộ nhớ tiến trình (1 giờ, 40 lượt, tối đa 5000 phiên), mất khi khởi động lại, không chia sẻ giữa nhiều worker.
- Hơn 2.100 test trong `tests/`.

## 4. Kiến trúc và thư mục chính

- `app/main.py`: tạo app, CORS, `/health`; dừng khởi động nếu kho tri thức dưới 1000 đoạn.
- `app/api/v1/endpoints/`: `diagnosis.py`, `chat.py`, `meta.py`.
- `app/schemas/`: schema Pydantic, tên trường camelCase trên dây, `extra="forbid"`.
- `app/services/ai_provider.py`: `AIProvider`, `MockAIProvider`, `LocalPipelineProvider`. Engine nào cũng nằm sau adapter này.
- `app/services/pipeline/`: detector, truy hồi (BM25), kho tri thức, VLM (`QwenVlm`, `StubVlm`), `local_pipeline.py` điều phối, quản lý phiên, câu hỏi làm rõ.
- `app/data/`: danh mục thiết bị, lỗi, ánh xạ dịch vụ, giá công, linh kiện, câu chờ.
- `docker/serve/`: image chạy vLLM, YOLO và API trong một container. `docker/train/`: image huấn luyện YOLO.
- `tools/`: `rent_gpu.py` (thuê, theo dõi, huỷ máy GPU), công cụ đánh giá, dữ liệu, gán nhãn. `app/` không import `tools/`.

## 5. Hợp đồng với repo khác

### Endpoint `backend` dùng

| Phương thức | Đường dẫn | Ghi chú |
| --- | --- | --- |
| POST | `/api/v1/diagnosis/analyze` | JSON; `description` 1 đến 2000 ký tự (bắt buộc), `images` tối đa 3 (base64 hoặc data URI, mỗi ảnh tối đa 8 MiB, chỉ ảnh đầu được phân tích), `sessionId`, `requestId`, `categoryHint` tối đa 64 |
| POST | `/api/v1/chat/ask` | `question` 1 đến 1000 ký tự, `deviceType` và `sessionId` tối đa 64 |
| GET | `/api/v1/chat/acknowledgements` | câu chờ cho client lưu sẵn |

Ngoài ra có `POST /api/v1/diagnosis/analyze-upload` (multipart), `GET /api/v1/meta/catalog`, `GET /health`, và trang thử `GET /chat`.

- Lỗi trả `{ code, message, fallbackAllowed: true, suggestedActionVi }` với 422, 503 hoặc 504; `backend` đổi mọi lỗi thành câu trả lời dự phòng và không chặn đặt lịch.
- Mã dịch vụ trả về trùng với danh mục của `backend`; dịch vụ dự phòng là `KIEM_TRA_CHAN_DOAN_THIET_BI`. Đổi danh mục ở `backend` thì phải sinh lại `app/data/service_mapping`.
- Đổi schema ở đây là thay đổi liên repo: cập nhật `backend` (DTO và giới hạn trong `ai-contract.dto.ts`) và context của `backend`, `web`, `mobile` cùng ngày.

### Biến môi trường (chỉ tên, xem `.env.example`)

`AI_ENGINE` (`local` hoặc `mock`), `YOLO_WEIGHTS_PATH`, `DETECTOR_CONFIDENCE_THRESHOLD`, `VLM_BASE_URL`, `VLM_MODEL_NAME`, `VLM_TIMEOUT_SECONDS`, `VLM_API_KEY`, `RETRIEVAL_TOP_K`, `AI_CONFIDENCE_THRESHOLD`, `IMAGE_MAX_BYTES`, `CORS_ORIGINS`. Biến chỉ cho công cụ: `ROBOFLOW_API_KEY`, `SERPER_API_KEY`, `HF_TOKEN`, `HF_DATASET_REPO`, `HF_WEIGHTS_REPO`, `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`.

## 6. Chạy, kiểm thử và cổng chất lượng

- Python 3.11 cho CI và ruff (`.python-version`). Cài `requirements.txt` và `requirements-dev.txt`, chạy `uvicorn app.main:app`. Không có GPU thì để trống `YOLO_WEIGHTS_PATH` và `VLM_BASE_URL`: detector và VLM chạy bản giả, còn truy hồi, kho tri thức và hội thoại chạy thật.
- Chạy với GPU: `python tools/rent_gpu.py offers` rồi `serve --offer <id>`, lấy địa chỉ bằng `address`. Máy tính tiền theo giờ: chỉ thuê khi PO cho phép, xong việc phải `destroy` ngay và báo lại.
- Gate trước mỗi commit: `ruff check app tests`, `pytest`, `python -m compileall -q app tests`, kiểm import, và khởi động thử rồi gọi `/health` nếu đụng `app/`.
- CI `ci.yml` chạy các gate trên khi push hoặc PR vào `main`. `serving-image.yml` và `trainer-image.yml` build và đẩy image khi `main` đổi; chưa có workflow triển khai.
- Repo chỉ có nhánh `main`: tách nhánh từ `main`, PR vào `main`, CI xanh mới merge.

## 7. Quyết định đã chốt

- Tự host YOLO và Qwen2.5-VL; không thêm lại adapter Gemini hay OpenAI khi chưa có quyết định ghi lại.
- AI chỉ gợi ý; mọi chữ, mã, giá đi ra phải lấy từ `app/data/`.
- AI hỏng hoặc chậm không được chặn đặt lịch; `backend` có câu trả lời dự phòng.
- Không thuê GPU khi chưa được PO cho phép.

## 8. Việc đang dở và rủi ro đã biết

- Chẩn đoán chỉ có ảnh không chạy: schema bắt `description` ít nhất 1 ký tự, trong khi `backend` gửi chuỗi rỗng khi khách chỉ gửi ảnh, nên luôn rơi vào câu dự phòng. Cần sửa ở `ai-service` (cho phép rỗng khi có ảnh) hoặc ở `backend`.
- Không có xác thực giữa `backend` và service, không giới hạn tần suất; API và trang `/chat` mở công khai trên máy GPU khi đang thuê.
- Ràng buộc đầu ra là kiểm tra sau khi sinh (`_parse_verdict`), chưa ràng buộc lúc giải mã.
- Trường hợp xấu nhất của chatbot (câu an toàn 25 giây cộng trả lời chung 8 giây) có thể vượt timeout 30 giây của `backend`; tính từ code, CHƯA KIỂM CHỨNG bằng đo thật.
- `categoryHint` được nhận nhưng chưa dùng; chỉ ảnh đầu tiên được phân tích.
- Phiên chỉ trong bộ nhớ; nhiều worker hoặc khởi động lại sẽ mất ngữ cảnh.
- Văn phong persona dùng "em", "anh/chị" và "đ", khác chuẩn "bạn" và "₫" của `FIXHOME-DESIGN-SYSTEM.md`; chờ PO chọn.
- 821 mục kho tri thức chờ kỹ thuật viên xác nhận, 36 giá chờ admin duyệt (xem `docs/CAN-THO-XAC-NHAN.md`).
- Một số tài liệu trong `docs/` đã cũ: `DATASET-AND-TRAINING.md`, `KB-NEXT-STEPS.md`, `LIVE-RUN.md`.

## 9. Nhật ký cập nhật context

- 2026-10-07 14:43 (UTC+7) | ToanAltF4 | docs/repo-context | Tạo file context theo bộ quy tắc chung của bốn repo, ghi hiện trạng sau đợt sửa lỗi ngày 07/10/2026
