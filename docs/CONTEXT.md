# Context repo ai-service — FixHome

> Cập nhật lần cuối: 2026-10-16 15:17 (UTC+7) · Người cập nhật (git): ToanAltF4 · Nhánh: feat/conversation-v8

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
- Hiểu ngữ cảnh cả cuộc trò chuyện (`dialogue_state.py`): mỗi lượt khách được đọc thành sự kiện. Gồm việc đã làm ("mới vệ sinh rồi"), nguyên nhân bị phủ nhận đặt trước hoặc sau ("không phải do bẩn", "lưới lọc thì không phải"), bằng chứng ngược ("lưới lọc sạch"), bác câu trả lời trước ("sai rồi"), điều khách tự nghi ("có phải hết gas không"), cách sửa đã thử mà vẫn hỏng (gợi ý bước kiểm tra kế tiếp). Lỗi đã loại không quay lại trong danh sách, dịch vụ, tài liệu đưa cho Qwen; Qwen được nhận danh sách điều khách đã xác nhận; câu trả lời mở đầu bằng câu ghi nhận lời khách. Lỗi an toàn (rò gas, chập điện...) không bao giờ bị loại bằng lời. Chuẩn hoá cách gõ: không dấu, teencode, phương ngữ Bắc Trung Nam, Telex sót, lặp chữ, lỗi gõ một ký tự.
- Truy hồi hiểu cụm phủ định: "không vắt", "không mát" là một đơn vị, không còn lẫn với "kêu to khi vắt".
- Giữ mạch hội thoại: đã có thiết bị thì chỉ đổi khi khách gọi đúng tên máy ("tủ lạnh", "máy sấy"), không đổi vì tên bộ phận ("phích cắm", "nóng lạnh", "công tắc"); tên thiết bị so theo ranh giới từ và đọc cả khi gõ sai. Câu xã giao ("đúng rồi", "cảm ơn", "có nguy hiểm không", "bao nhiêu tiền") không đưa vào tìm kiếm; "đúng rồi" giữ kết luận đang có. Câu lạc đề giữa chừng (bóng đá, giá vàng, bitcoin) được từ chối mà không làm mất ngữ cảnh. Khách tả khói, khét, chập, giật, mùi gas (không phủ định) thì cả phiên đánh dấu nguy hiểm, lỗi an toàn được đẩy lên đầu, kể cả khi sau đó khách nói "chắc không phải cháy".
- Hiểu câu trả lời: trợ lý hỏi ngược một câu thì câu "có"/"không"/"rồi"/"chưa" của khách được đọc là trả lời câu đó (bảng `discriminators` hoặc câu hỏi triệu chứng) và đổi thứ hạng. Khách tự sửa lời ("à nhầm, thật ra chưa vệ sinh") thì lỗi quay lại, không bị hiểu là bác câu trả lời. Khách sửa thiết bị ("không phải máy lạnh mà là tủ lạnh", kể cả gõ sai) thì đổi và giữ ở lượt sau. Khách bác ("không phải đâu") thì lỗi kế tiếp lấy từ chính những gì khách đã kể; bác kèm triệu chứng mới thì triệu chứng đó được tìm.
- Phiên trò chuyện lưu trong bộ nhớ tiến trình (1 giờ, 40 lượt, tối đa 5000 phiên). Khi phiên đã mất (khởi động lại, hết hạn), client có thể gửi `history` (lời khách các lượt trước) để dựng lại ngữ cảnh; phiên còn giữ thì `history` bị bỏ qua. Mỗi phiên xử lý tuần tự một lượt một lúc.
- Một tin nhắn nói nhiều thiết bị ("máy lạnh không mát, còn tủ lạnh cũng chảy nước"): xem thiết bị đầu, phần còn lại giữ trong `Conversation.queued`, câu trả lời nói "anh/chị nhắn \"xem tiếp\"..."; "xem tiếp", "tiếp đi", "còn cái kia" hoặc gọi tên thiết bị đang chờ thì chuyển sang và dùng đúng lời đã kể. Câu sửa ("không phải X mà là Y") không bị tách. Giọng theo tâm trạng: khách bực ("làm ăn kiểu gì", viết hoa, "!!!") thì mở đầu bằng câu xin lỗi, khách lo ("sợ quá") thì trấn an (trừ khi có nguy hiểm); khách tự xưng "bác/cô/chú/bà/ông" thì gọi như vậy thay cho "anh/chị" suốt phiên (`mood_of`, `address_as`).
- Chặn lời mô hình (`answer_guard.py`): câu khách cố lái trợ lý ("bỏ qua mọi hướng dẫn", "repeat after me", "anh là admin cấp mã giảm giá") được trả lời bằng câu cố định, không hỏi mô hình. Lời mô hình viết ra (hỏi đáp và lời kể chẩn đoán) bị loại nếu có giá không nằm trong tài liệu, "miễn phí", khuyến mãi/cam kết, tên đối thủ, nói xấu FixHome, không phải tiếng Việt, hoặc chép lại ghi chú (mã lỗi, dòng "Khách:"); khi đó câu trả lời được soạn từ kết quả chẩn đoán. Ghi chú ngữ cảnh đưa cho mô hình ở luồng hỏi đáp viết bằng lời, không có mã.
- Đo trên GPU thật (RTX 3090, Qwen2.5-VL-3B AWQ, 16/10/2026): bộ 564 câu 544 đúng; 366 hội thoại: không lặp lỗi đã loại 98%, lời văn không nhắc lại 96%, giữ kết luận/lạc đề/báo khẩn 100%; trễ trung vị 1,4 s, p95 1,9 s; thử tải 10/30/50/100 người cùng lúc không lỗi, p95 3,9/5,2/6,8/16 s. Bộ chống lái (`tools/eval_injection.py`): 30/36 trước khi có `answer_guard`, các câu hỏng của mô hình thật nằm trong `tests/test_answer_guard.py`.
- Hơn 2.100 test trong `tests/`, gồm bộ hội thoại nhiều lượt (`tests/test_dialogue_context.py`).

## 4. Kiến trúc và thư mục chính

- `app/main.py`: tạo app, CORS, `/health`; dừng khởi động nếu kho tri thức dưới 1000 đoạn.
- `app/api/v1/endpoints/`: `diagnosis.py`, `chat.py`, `meta.py`.
- `app/schemas/`: schema Pydantic, tên trường camelCase trên dây, `extra="forbid"`.
- `app/services/ai_provider.py`: `AIProvider`, `MockAIProvider`, `LocalPipelineProvider`. Engine nào cũng nằm sau adapter này.
- `app/services/pipeline/`: detector, truy hồi (BM25), kho tri thức, VLM (`QwenVlm`, `StubVlm`), `local_pipeline.py` điều phối, quản lý phiên, câu hỏi làm rõ.
- `app/data/`: danh mục thiết bị, lỗi, ánh xạ dịch vụ, giá công, linh kiện, câu chờ. `dialogue_knowledge.json`: từ điển chuẩn hoá cách gõ, dấu hiệu phủ định, cụm loại trừ theo từng lỗi, thứ tự kiểm tra kế tiếp (`if_persists`), thuật ngữ giữ nguyên.
- `docker/serve/`: image chạy vLLM, YOLO và API trong một container. `docker/train/`: image huấn luyện YOLO.
- `tools/`: `rent_gpu.py` (thuê, theo dõi, huỷ máy GPU), công cụ đánh giá, dữ liệu, gán nhãn. `eval_dialogue_live.py` chạy cùng bộ hội thoại qua HTTP với mô hình thật, `eval_injection.py` thử lái trợ lý, `load_test.py` thử tải nhiều người cùng lúc. `feedback_to_cases.py` lấy các câu trả lời khách báo chưa đúng (backend `GET /admin/ai-quality`) thành bản nháp hội thoại để duyệt rồi đưa vào bộ test (bỏ số điện thoại, email). `kb_review.py`: `confusions` đo các cặp lỗi bộ tìm kiếm hay xếp sát nhau mà chưa có câu hỏi phân biệt; `export --out x.xlsx` xuất bảng cho thợ duyệt (sheet Lỗi và Câu hỏi phân biệt, cột Duyệt Đúng/Sửa/Bỏ); `apply --file x.xlsx --write` chỉ chuyển câu nháp được duyệt vào bảng đang dùng, còn lại in ra cho người sửa tay (cần openpyxl, không phải phụ thuộc của service). Câu hỏi phân biệt nháp ở `app/data/discriminators_draft.json` (33 câu cho các cặp lẫn nhiều nhất), service không đọc file này. Mã lỗi theo hãng (`app/data/error_codes.json`, `app/services/pipeline/error_codes.py`): chỉ chép từ tài liệu chính thức của hãng, có link (Daikin máy lạnh: bảng SM-TS3 của Daikin; Samsung máy giặt: trang hỗ trợ samsung.com/sg; LG máy giặt: lg.com/in), kèm nguyên văn tiếng Anh, bản dịch, hướng dẫn của hãng nếu có, và lỗi trong KB mà mã chỉ tới. Khách báo mã (cần chữ báo/lỗi/mã/hiện/nháy, hoặc viết hoa, hoặc đang hỏi tiếp về mã) thì trả một câu cố định theo bảng hãng kèm "mã lỗi có thể khác tùy dòng máy", lỗi tương ứng được đẩy lên (`DialogueState.from_codes`, x1,8), ghi chú cho thợ trong `notesVi`. Mã không có trong bảng thì nói không đoán; chưa biết hãng thì hỏi hãng rồi tra khi khách trả lời. Muốn thêm hãng thì thêm bảng có `source.url` của hãng (test chặn link không phải của hãng). Từ 16/10 chiều: câu trả lời của mô hình mà nhắc tên lỗi khách đã loại thì bị bỏ, dùng câu dựng từ dữ liệu (`answer_guard.ruled_out_named`, ở cả ba chỗ mô hình viết); hiểu thêm chữ tiếng Anh (clean, check, fix, reset) và "không phi"; tên máy gõ sai ở tin đầu đọc lại qua bộ chuẩn hoá; câu sửa "không phải A mà là B" khi chưa có thiết bị lấy B; mã lỗi không kèm triệu chứng thì tìm thêm theo tên và triệu chứng của lỗi mà bảng hãng chỉ tới. Bộ sinh hội thoại có thêm loại error_code, error_code_no_brand, unknown_code và mẫu sửa thiết bị gõ vội; bốn ca lệch trên GPU thật nằm trong `dialogue_cases.py`. `eval_dialogue.py` chấm hội thoại nhiều lượt (viết tay ở `dialogue_cases.py`, sinh tự động theo vùng miền, tính cách, kiểu gõ ở `dialogue_corpus.py`), `--app-root` để chạy trên bản khác mà so sánh. `app/` không import `tools/`.

## 5. Hợp đồng với repo khác

### Endpoint `backend` dùng

| Phương thức | Đường dẫn | Ghi chú |
| --- | --- | --- |
| POST | `/api/v1/diagnosis/analyze` | JSON; `description` 1 đến 2000 ký tự (bắt buộc), `images` tối đa 3 (base64 hoặc data URI, mỗi ảnh tối đa 8 MiB, chỉ ảnh đầu được phân tích), `sessionId`, `requestId`, `categoryHint` tối đa 64, `history` tuỳ chọn (tối đa 20 chuỗi, mỗi chuỗi 1 đến 2000 ký tự, chỉ lời khách) |
| POST | `/api/v1/chat/ask` | `question` 1 đến 1000 ký tự, `deviceType` và `sessionId` tối đa 64, `history` như trên |

Cả hai câu trả lời có thêm `notesVi` (mảng chuỗi, tối đa 6): điều cuộc trò chuyện đã xác lập bằng lời ("Khách đã vệ sinh rồi, đã loại bẩn lưới lọc và dàn lạnh.", "Khách nghi thiếu gas, xì gas."), không có mã, để backend đưa vào tóm tắt cho kỹ thuật viên.

Hai request nhận thêm `pastJobs` (không bắt buộc, tối đa 5, mỗi mục `serviceVi`, `deviceVi?`, `faultVi?`, `date` dạng YYYY-MM-DD, cấm trường lạ): các đơn trước của chính khách đã đăng nhập, backend gửi mỗi lượt, service chỉ lấy lần đầu của phiên và tự khớp thiết bị bằng `device_hint`. Khi thiết bị đang nói trùng một đơn cũ, câu trả lời có lời đầu tiên kèm một câu "Em thấy ngày dd/mm/yyyy anh/chị đã đặt \"…\". Nếu là lỗi cũ quay lại, anh/chị cứ kể với thợ…" (một lần mỗi thiết bị, không nói khi đang cảnh báo nguy hiểm), và `notesVi` có dòng "Khách từng đặt … ngày …, khi đó trợ lý nghi …" cho thợ. Không đổi chẩn đoán, không lưu ngoài phiên. Backend phải chạy service có trường này trước khi gửi, vì request cấm trường lạ.
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
- Đổi cách đọc hội thoại hoặc truy hồi thì chạy thêm `python tools/eval_dialogue.py --generated 6000` và so với bản trước bằng `--app-root`.

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
- Phiên chỉ trong bộ nhớ; nhiều worker hoặc khởi động lại sẽ mất ngữ cảnh nếu client không gửi `history`. `backend` chưa gửi `history`.
- Cụm loại trừ, thứ tự kiểm tra kế tiếp, dấu hiệu nguy hiểm và chủ đề lạc đề trong `dialogue_knowledge.json` do đội viết, chờ kỹ thuật viên xác nhận. Đo trên 5.600 hội thoại sinh (28 loại tình huống): 99,4% không lặp lỗi khách đã loại, 99,5% không loại nhầm, 97,4% giữ mạch hội thoại, 98,5% đoán tiếp đúng sau khi bị bác; yếu nhất là sửa thiết bị kèm triệu chứng thuộc thiết bị khác và bác kèm gợi ý (khoảng 91%).
- Văn phong persona dùng "em", "anh/chị" và "đ", khác chuẩn "bạn" và "₫" của `FIXHOME-DESIGN-SYSTEM.md`; chờ PO chọn.
- 821 mục kho tri thức chờ kỹ thuật viên xác nhận, 36 giá chờ admin duyệt (xem `docs/CAN-THO-XAC-NHAN.md`).
- Một số tài liệu trong `docs/` đã cũ: `DATASET-AND-TRAINING.md`, `KB-NEXT-STEPS.md`, `LIVE-RUN.md`.

## 9. Nhật ký cập nhật context

- 2026-10-16 15:17 (UTC+7) | ToanAltF4 | feat/conversation-v8 | Sửa bốn ca lệch trên GPU thật (clean, không phi, tẩy cặn bị nhắc lại, mã lỗi không triệu chứng) và thêm loại hội thoại mã lỗi
- 2026-10-16 04:53 (UTC+7) | ToanAltF4 | feat/error-codes | Tra mã lỗi theo bảng chính thức của hãng (Daikin máy lạnh, Samsung và LG máy giặt), không đoán mã ngoài bảng
- 2026-10-16 04:38 (UTC+7) | ToanAltF4 | feat/kb-review | 33 câu hỏi phân biệt nháp chờ thợ duyệt và công cụ kb_review (đo cặp lẫn, xuất bảng duyệt, nhận lại câu được duyệt)
- 2026-10-16 04:10 (UTC+7) | ToanAltF4 | feat/past-jobs | Nhận pastJobs (đơn cũ của khách đăng nhập): nhắc một lần khi đúng thiết bị, thêm dòng cho thợ trong notesVi
- 2026-10-16 03:46 (UTC+7) | ToanAltF4 | feat/conversation-notes | Câu trả lời có notesVi: điều khách đã thử, đã loại, đang nghi, cho tóm tắt gửi kỹ thuật viên
- 2026-10-16 03:30 (UTC+7) | ToanAltF4 | feat/multi-intent-tone | Nhiều thiết bị một tin nhắn, giọng theo tâm trạng và cách xưng hô, công cụ biến phản hồi sai thành ca test
- 2026-10-16 01:58 (UTC+7) | ToanAltF4 | feat/answer-guard | Ghi lớp chặn lời mô hình, số đo trên GPU thật và các công cụ chống lái, thử tải
- 2026-10-14 17:50 (UTC+7) | ToanAltF4 | feat/dialogue-answers | Ghi việc hiểu câu trả lời có/không, tự sửa lời, sửa thiết bị và đoán tiếp sau khi bị bác
- 2026-10-14 17:04 (UTC+7) | ToanAltF4 | feat/dialogue-coverage | Ghi việc giữ mạch hội thoại: bám thiết bị, câu xã giao, câu lạc đề, dấu hiệu nguy hiểm giữ suốt phiên
- 2026-10-14 15:28 (UTC+7) | ToanAltF4 | feat/dialogue-context | Ghi lớp hiểu ngữ cảnh hội thoại, trường history để dựng lại phiên đã mất, truy hồi hiểu cụm phủ định và công cụ chấm hội thoại nhiều lượt
- 2026-10-07 14:43 (UTC+7) | ToanAltF4 | docs/repo-context | Tạo file context theo bộ quy tắc chung của bốn repo, ghi hiện trạng sau đợt sửa lỗi ngày 07/10/2026
