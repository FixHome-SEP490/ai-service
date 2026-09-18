# Nối chatbot AI vào mobile và Backend

Tài liệu bàn giao, viết ngày 18/09/2026 cho người làm chatbot trên mobile và
Backend. Mọi thông tin dưới đây **đọc ra từ dịch vụ đang chạy**, không phải từ ký
ức: đặc tả lấy từ `/openapi.json` của máy thật, thời gian lấy từ mốc thời gian
trong log container.

Mobile đã có sẵn UI chatbot. Việc còn lại là **nối dây**: gửi ảnh, giữ phiên, và
hiển thị đúng những gì AI trả về.

---

## 1. Thuê máy: mất bao lâu trước khi AI hoạt động lại

Đo trên máy đã chốt (`machine_id 27076`, RTX A4000):

| bước | thời gian |
|---|---|
| huỷ máy cũ | ~10 giây |
| vast.ai cấp máy + kéo image 8,74 GB | ~3 phút |
| tải weights detector + nạp Qwen + biên dịch CUDA graph | **3 phút 35 giây** (đo) |
| **tổng, từ lệnh `serve` đến API trả lời** | **khoảng 7 phút** |

**Nếu code AI vừa thay đổi và chưa merge**, cộng thêm **~13 phút** để CI build lại
image serve. Bỏ bước chờ đó thì máy thuê chạy **code cũ** và mọi thử nghiệm sai.

Trên máy không đạt chuẩn, con số này là **vô hạn**: có máy pull 33 phút không xong.
Điều kiện và cách chọn máy ở [RENTING-A-GPU.md](RENTING-A-GPU.md).

---

## 2. Config plug-and-play: mỗi lần thuê là một IP và port khác

Đây là vấn đề anh nêu, và cách giải quyết gọn nhất là **không bao giờ hardcode địa
chỉ**. Một lệnh in ra đúng dòng cần dán:

```bash
python tools/rent_gpu.py address
```

```
AI_SERVICE_URL=http://38.29.145.157:40347
  READY — Qwen and detector attached, 3319 knowledge passages

Paste into the consumer that needs it:

  Backend  .env          AI_SERVICE_URL=http://38.29.145.157:40347
  Mobile   .env          EXPO_PUBLIC_AI_SERVICE_URL=http://38.29.145.157:40347
  Eval     shell         AI_SERVICE_URL=http://38.29.145.157:40347

  chat     http://38.29.145.157:40347/chat
  health   http://38.29.145.157:40347/health
  diagnose http://38.29.145.157:40347/api/v1/diagnosis/analyze-upload
```

Ghi thẳng vào file `.env`, thay dòng cũ:

```bash
python tools/rent_gpu.py address --write-env ../backend/.env
python tools/rent_gpu.py address --write-env ../mobile/.env
```

Lệnh này **gọi `/health` trước khi in**, nên nó nói luôn máy đã sẵn sàng chưa. Cổng
đã publish **không có nghĩa là dịch vụ chạy** — hai thứ đó cách nhau 3 phút 35 trên
máy nhanh nhất, và có máy publish cổng mà không bao giờ route tới. Dán một địa chỉ
chết vào `.env` rồi đi debug Backend là phiên bản đắt tiền của lỗi này.

**Yêu cầu với Backend:** đọc `AI_SERVICE_URL` từ env, **không** hardcode, và **không**
cache nó qua các lần khởi động. Đổi địa chỉ thì chỉ cần đổi env rồi restart.

**Yêu cầu với mobile:** `EXPO_PUBLIC_AI_SERVICE_URL`. Nếu mobile gọi AI **qua
Backend** (khuyến nghị, xem mục 6) thì mobile không cần biến này.

---

## 3. Sáu endpoint, và hai cái thật sự cần cho chatbot

| Method | Path | Dùng khi |
|---|---|---|
| POST | `/api/v1/diagnosis/analyze` | **có ảnh** hoặc mô tả sự cố — JSON, ảnh base64 |
| POST | `/api/v1/diagnosis/analyze-upload` | như trên, ảnh gửi dạng multipart |
| POST | `/api/v1/chat/ask` | **câu hỏi tự do** không kèm ảnh |
| GET | `/api/v1/chat/acknowledgements` | câu "em đang xem ạ" cho client hiện trong lúc chờ |
| GET | `/api/v1/meta/catalog` | danh mục thiết bị và dịch vụ |
| GET | `/health` | máy sẵn sàng chưa |

Chatbot chỉ cần **`diagnosis/analyze` và `chat/ask`**. Quy tắc chọn:

- Tin nhắn **có ảnh** → `diagnosis/analyze`
- Tin nhắn **tả sự cố** ("máy lạnh không mát") → `diagnosis/analyze`
- Tin nhắn **hỏi thông tin** ("bảo hành bao lâu", "giá vệ sinh máy lạnh") → `chat/ask`

Không chắc thì gửi `diagnosis/analyze`: nó tự nhận ra câu hỏi nghiệp vụ, câu chào,
và ý định đặt lịch, rồi xử đúng nhánh.

---

## 4. Gửi ảnh: hai cách, chọn một

### Cách A — JSON, base64 (khuyến nghị cho mobile)

```
POST /api/v1/diagnosis/analyze
Content-Type: application/json

{
  "description": "máy lạnh nhà em không mát",
  "images": ["data:image/jpeg;base64,/9j/4AAQ...."],
  "sessionId": "8f3c…"          // bỏ trống ở tin nhắn đầu
}
```

- `images` nhận **tối đa 3 ảnh**, mỗi ảnh **≤ 8 MB** sau khi giải mã
- Nhận cả **data URI** (`data:image/jpeg;base64,...`) và **base64 trần**
- MIME cho phép: `image/jpeg`, `image/png`, `image/webp`
- `description` là **bắt buộc** nhưng **được để chuỗi rỗng** nếu khách chỉ gửi ảnh

### Cách B — multipart

```
POST /api/v1/diagnosis/analyze-upload
Content-Type: multipart/form-data

files=<file>&files=<file>&description=...&session_id=...
```

> **Chú ý dễ sai:** endpoint multipart dùng **snake_case** (`session_id`,
> `request_id`, `category_hint`, `include_trace`, `files`), còn JSON và mọi phản
> hồi dùng **camelCase** (`sessionId`). Hai kiểu đặt tên trong cùng một API.

Ảnh nên **resize trước khi gửi** từ mobile. Ảnh điện thoại 4000px không cho kết quả
tốt hơn: detector chạy ở 640px, và ảnh lớn chỉ tốn băng thông và thời gian giải mã.
Resize cạnh dài về **1280px, JPEG quality 85** là đủ.

---

## 5. Giữ phiên: hợp đồng đúng một câu

**Gửi rỗng ở tin nhắn đầu, rồi echo lại `sessionId` mà phản hồi trả về.**

```
tin nhắn 1:  POST { description: "...", images: [...] }        (không có sessionId)
phản hồi 1:  { sessionId: "8f3c…", ... }                        ← lưu lại
tin nhắn 2:  POST { description: "mới vệ sinh tháng trước", sessionId: "8f3c…" }
```

**Server phát id, client không được tự đặt.** Trường này nhận chuỗi bất kỳ nên hai
client cùng gửi `"guest"` sẽ **dùng chung hội thoại** — thiết bị và triệu chứng của
người này hiện sang người kia. Server **không nhận** id nó chưa phát: gửi id lạ thì
nó mở phiên mới và trả về id mới, nên client cứ echo là đúng.

Phiên giữ lại những gì:

- **thiết bị** đã nhận ra từ ảnh — khách không gửi lại ảnh ở tin nhắn sau
- **mọi triệu chứng** khách đã kể, gom lại để truy hồi
- **những câu đã hỏi**, để không hỏi lại

Thông số: **hết hạn sau 1 giờ không nhắn**, giữ **40 lượt** mỗi phiên, tối đa
**5.000 phiên** cùng lúc.

**Rủi ro phải xử ở client:** phiên nằm trong bộ nhớ tiến trình, nên **restart máy
AI hoặc thuê máy khác là mất hết phiên đang dở**. Client sẽ nhận một `sessionId`
mới và AI "quên" thiết bị. Mobile nên:

- luôn ghi `sessionId` từ phản hồi mới nhất, không giữ bản cũ
- **giữ transcript ở phía mình**, đừng dựa vào AI để hiển thị lại lịch sử
- khi `sessionId` trả về khác cái đang giữ, hiểu là phiên đã mới — không cần báo lỗi
  cho khách, chỉ đừng giả định AI còn nhớ ảnh cũ

---

## 6. Mobile gọi AI trực tiếp hay qua Backend

**Khuyến nghị: qua Backend.** Lý do:

- địa chỉ AI đổi mỗi lần thuê — đổi env ở **một** chỗ (Backend) dễ hơn build lại app
- ảnh khách thường đã nằm ở Supabase Storage do Backend quản
- Backend cần biết kết quả chẩn đoán để gắn vào booking (mục 7)
- AI hiện **không có xác thực**: máy thuê có IP công khai và cổng mở, nên không nên
  để app của khách gọi thẳng vào

Nếu cần demo nhanh và chấp nhận rủi ro thì mobile gọi thẳng được, chỉ cần
`EXPO_PUBLIC_AI_SERVICE_URL`. Android emulator nhớ dùng IP thật của máy thuê, không
phải `10.0.2.2` — đó chỉ dành cho service chạy trên máy dev.

---

## 7. Có cần lưu gì xuống DB không

**Cho bản thân cuộc chat: không.** Anh nghĩ đúng. Lý do cụ thể:

- AI **không** đọc DB và **không** ghi DB. Nó nhận request, trả advice.
- Bảng `conversations` / `messages` đã có là của **chat realtime khách ↔ thợ**, và
  theo thiết kế nó **chỉ tồn tại theo cặp (booking, technician)**, sinh ra khi thợ
  nhận booking. Chat với AI diễn ra **trước khi có booking**, nên **không dùng được**
  hai bảng đó và **không nên** cố nhét vào.
- Transcript giữ ở state của app là đủ cho trải nghiệm: khách mở lại app thì bắt đầu
  hội thoại mới, và đó là hành vi bình thường của một trợ lý chẩn đoán.

**Nhưng có một thứ nên lưu, và nó nhỏ:** khi khách bấm "Đặt thợ ngay" từ một câu trả
lời của AI, **gắn kết quả chẩn đoán vào booking**. Không phải transcript — chỉ mấy
trường:

| trường | ví dụ | để làm gì |
|---|---|---|
| `deviceType` | `washing_machine` | thợ biết mang gì |
| `suspectedFaultCodes` | `["WM_NO_SPIN","WM_BEARING_NOISE"]` | brief cho thợ |
| `aiConfidence` | `0.62` | thợ biết mức tin cậy |
| `aiSessionId` | `8f3c…` | truy vết khi cần |

Một cột JSON trên `bookings` là đủ, không cần bảng mới. Lợi ích: thợ đến nhà đã biết
khách nói gì, và khi đối chiếu về sau thì biết AI đã gợi ý gì. **Đây là đề xuất, cần
anh quyết** — không có nó thì chatbot vẫn chạy đủ.

---

## 8. Phản hồi có gì, và client phải hiện gì

### `POST /api/v1/diagnosis/analyze` trả về

```jsonc
{
  "sessionId": "8f3c…",
  "status": "ok",                    // hoặc "needs_clarification"
  "device": { "deviceType": "washing_machine", "nameVi": "Máy giặt",
              "confidence": 0.94, "source": "image", "boundingBox": {…} },
  "suspectedFaults": [
    { "faultCode": "WM_NO_SPIN", "nameVi": "Không vắt, hỏng dây curoa",
      "confidence": 0.62, "source": "description" }
  ],
  "recommendedServices": [
    { "serviceCode": "SUA_MAY_GIAT", "nameVi": "Sửa máy giặt rung lắc / không vắt" }
  ],
  "suggestedActionsVi": ["Rút điện và kiểm tra lồng giặt còn nước không"],
  "priceEstimate": { "min": 180000, "max": 450000,
                     "currency": "VND", "requiresAssessment": false },
  "urgency": "MEDIUM",               // LOW | MEDIUM | HIGH
  "confidence": 0.62,
  "isLowConfidence": false,
  "clarification": { "questionsVi": ["Máy có xả hết nước ra khỏi lồng không?"],
                     "serviceGroupCodes": ["SVG_APPLIANCE"] },
  "messageVi": "Em đã đọc và kiểm tra thông tin anh/chị gửi. Có khả năng hư hỏng là mòn bạc đạn lồng giặt. Chi phí từ 100.000đ, phần còn lại kỹ thuật viên phải xem tận nơi mới tính được. Em sẽ đặt dịch vụ Sửa máy giặt rung lắc / không vắt cho anh/chị.",
  "disclaimerVi": "Đây là gợi ý sơ bộ, kết luận cuối cùng thuộc về kỹ thuật viên…"
}
```

**`messageVi` là câu đã soạn sẵn để hiện thẳng làm bong bóng chat**, và các trường
có cấu trúc bên cạnh là để dựng chip, nút, cảnh báo. Trước đây trường này để `null`
và client phải tự ghép câu; nay pipeline tự soạn. Vẫn phải xử `null`: có nhánh
không sinh câu, và khi đó client dựng câu từ các trường có cấu trúc như mô tả dưới
đây.

Client nên hiện, theo thứ tự:

1. **`urgency: "HIGH"` thì hiện `suggestedActionsVi` TRƯỚC MỌI THỨ**, nổi bật. Đó là
   cảnh báo an toàn — khoá van gas, ngắt aptomat — và nó được cố tình tách khỏi phần
   còn lại. Hiện nó sau chẩn đoán là làm mất tác dụng.
2. `device.nameVi` — "Em thấy đây là máy giặt"
3. `suspectedFaults[*].nameVi` — danh sách, **không phải một kết luận**. Từ ngữ nên
   là "có thể là", vì đó đúng là những gì nó là.
4. `priceEstimate` — `requiresAssessment: true` thì hiện "từ X đồng, thợ báo giá sau
   khi kiểm tra", đừng hiện một khoảng giá chắc chắn.
5. `recommendedServices[0]` → **nút "Đặt thợ ngay"**
6. `disclaimerVi` — nhỏ, ở cuối. **Luôn hiện**, đây là yêu cầu nghiệp vụ.

Khi `status: "needs_clarification"`: hiện `clarification.questionsVi` như câu hỏi
của bot. **Vẫn có `recommendedServices`** — thường là gói kiểm tra tại nhà — nên
**vẫn hiện nút đặt**. Khách không bị buộc phải trả lời mới được đặt.

### `POST /api/v1/chat/ask` trả về

```jsonc
{
  "sessionId": "8f3c…",
  "status": "ok",          // ok | out_of_scope | general_knowledge | no_grounding
  "answerVi": "Bảo hành công 30 ngày…",     // ở đây LUÔN có chữ
  "citations": [ { "docId": "KB_SYS_WARRANTY", "titleVi": "Bảo hành", "score": 1.0 } ],
  "recommendedServices": [ … ],
  "confidence": 0.8,
  "disclaimerVi": "…"
}
```

`answerVi` **luôn có nội dung** ở endpoint này. `citations` dùng để debug hoặc hiện
"theo chính sách của FixHome", không bắt buộc hiện.

`status: "out_of_scope"` hoặc `"no_grounding"` → `answerVi` là câu từ chối lịch sự,
**hiện y nguyên**. Đừng thay bằng câu lỗi của app.

---

## 9. Những chỗ dễ làm sai

**Thời gian chờ.** Mô hình có hạn mức 8 giây, cộng mạng và giải mã ảnh: đặt timeout
**30 giây**, đừng đặt 5. Trong lúc chờ hiện câu lấy từ
`/api/v1/chat/acknowledgements` thay vì spinner trắng.

**Đừng hardcode địa chỉ AI.** Mỗi lần thuê là một IP và port khác. Dùng
`rent_gpu.py address --write-env`.

**Đừng gửi id phiên do client tự đặt.** Sẽ bị bỏ qua, và nếu server có nhận thì hai
khách dùng chung hội thoại.

**Đừng coi `messageVi` là chắc chắn có.** Bình thường nó có câu đầy đủ, nhưng
vẫn có nhánh trả `null` — client phải dựng được câu từ các trường có cấu trúc.

**Đừng hiện `suspectedFaults` như một kết luận.** Nó là danh sách khả nghi: đo trên
máy thật, mã đúng nằm ở **hạng nhất 91,7%** — cao, nhưng không phải chắc chắn. Từ ngữ
phải là "có thể là", không phải "máy của bạn bị".

**Đừng chôn cảnh báo an toàn.** `urgency: "HIGH"` thì `suggestedActionsVi` lên đầu.

**Ảnh: resize trước khi gửi**, tối đa 3 ảnh, mỗi ảnh ≤ 8 MB.

**AI không có xác thực.** Máy thuê mở cổng ra internet. Nối qua Backend, và đừng để
địa chỉ đó lọt vào bản build công khai của app.

**Kiểm `chunks` trong `/health`.** Phải là **3319** hoặc hơn. Nhỏ hơn nghĩa là đang
chạy **image cũ** và mọi thử nghiệm đo sai con code.

---

## 10. Số đo hiện tại, để biết trông đợi gì

Đo trên máy thật với Qwen thật, 564 ca:

| | |
|---|---|
| hành vi đúng loại (chẩn đoán / hỏi / trả lời / từ chối) | **97,0%** |
| từ chối câu ngoài phạm vi | **100%** |
| nhận đúng thiết bị | 93,4% |
| nhận đúng mã bệnh | 91,7% |
| có dịch vụ đặt được trong câu trả lời | 97,9% |
| ý định đặt lịch → ra nút | **38/38 nhận ra, 11/11 ra nút** |
| lỗi HTTP | **0** |

Độ trễ thực tế: **0,3–2,4 giây**.

Detector: **85,7%** gọi đúng tên trên 22 thiết bị. Lớp yếu nhất là máy sấy quần áo
**69,1%**, hay bị nhầm thành máy giặt — nên với cặp đó bot **hỏi lại** trước khi
chẩn đoán.

Chưa đo được: **chất lượng câu chữ** do mô hình viết, và **nửa có-ảnh** của việc
chọn mã bệnh. Đừng trích số nào cho hai thứ đó.

---

## 11. Mở session mới thì cần biết gì

Đọc ba file, theo thứ tự:

1. **[RENTING-A-GPU.md](RENTING-A-GPU.md)** — thuê máy nào, và năm cách nó hỏng. Máy
   đã chốt: `machine_id 27076`.
2. **File này** — hợp đồng API, gửi ảnh, giữ phiên, client hiện gì.
3. **[CHATBOT-NEXT.md](CHATBOT-NEXT.md)** — vòng lặp cải tiến và nợ đã đo, nếu cần
   sửa chính AI.

Ranh giới quyền hạn hiện tại: `repo/ai-service` được commit, mở PR, merge.
`repo/backend` và `repo/mobile` **chỉ sửa file và báo cáo — không commit, không
push, không PR**. Việc chatbot nằm phần lớn ở hai repo đó, nên cần PO nới quyền
trước khi bắt đầu.

Còn chờ quyết định: có gắn kết quả chẩn đoán vào `bookings` hay không (mục 7), và AI
hiện trả `serviceCode` mà **chưa trả `serviceId`** nên Backend phải tự tra — xem
[CHATBOT-BOOKING-HANDOFF.md](CHATBOT-BOOKING-HANDOFF.md).
