# Chat brain v2: detector + LLM + thẻ chuyên môn

Từ 06/11/2026 (PO chốt), chat AI chạy bằng `app/services/chat2` (`AI_ENGINE=chat2`, mặc định trong image serve). Pipeline cũ (`app/services/pipeline/local_pipeline.py`) vẫn còn cho `AI_ENGINE=local` nhưng không còn là đường chính.

## Vì sao làm lại

Pipeline cũ chọn lỗi bằng cách khớp chữ câu khách với danh sách triệu chứng (truy hồi lexical), rồi để Qwen2.5-VL-3B viết lại. Câu khách không trùng chữ là ra lỗi lạc: "máy lạnh rơi xuống đất" thành nghẹt thoát nước, "mùi hôi như thối, rất bẩn" thành chập điện, "tủ lạnh mùi hôi" thành hỏng máy nén. Đo cùng thiết kế mới, Qwen2.5-VL-3B trả "không phải việc sửa chữa" cho 489/515 câu mô tả rõ: model 3B không đủ sức theo một prompt dài có cấu trúc.

## Vai của từng phần

- YOLO11s (`detector-v2-yolo11s`): đọc ảnh, ra loại thiết bị. Model chat không bao giờ nhận ảnh.
- LLM Qwen3.5-9B (tắt đầu vào ảnh/video, tắt chế độ suy nghĩ; image serve tự chọn bản theo card: card từ 24GB chạy `RedHatAI/Qwen3.5-9B-FP8-dynamic`, card 16GB chạy `cyankiwi/Qwen3.5-9B-AWQ-4bit` với `--max-num-seqs 64`, đặt `VLM_MODEL_NAME` để ép một bản): đọc cả cuộc trò chuyện, điền `need` (khách cần gì), `need_kind` (`hong_hoc`, `hu_hai`, `xin_viec`, `chua_ro`), `fault_code`, `service_code`, `reply`, `options`. Giải mã dưới JSON schema mà enum là đúng mã lỗi, mã dịch vụ của thiết bị đó.
- Code (`brain._decide`): quyết hỏi hay chốt. Khách đã kể hiện tượng, hư hại hay xin việc là chốt; chưa kể gì (`chua_ro`, hoặc `need` chỉ có chữ chung chung như "hư", "có vấn đề") mới hỏi đúng một câu kèm 2-4 nút; tối đa 2 câu hỏi một cuộc. Hư hại (rơi, vỡ, ngấm nước) luôn ra dịch vụ sửa. Lỗi có tên luôn ra dịch vụ catalog ánh xạ cho lỗi đó.
- Router: mỗi lượt xác định thiết bị khách nhắc (tối đa 3) và ý định. Chữ gọi đích danh tên máy (tên hoặc alias trong `device_catalog.json`, bỏ qua "như cái X") chỉ thắng ảnh giữa các cặp detector hay nhầm (`confusable_with`); máy khác chữ nhắc tới thành thiết bị thêm, mỗi máy chẩn đoán riêng (`Verdict.others`). Có ảnh thì router không được tự từ chối "lạc đề".
- Mã lỗi theo hãng (`error_codes.json`): nghĩa chính thức đưa vào ngữ cảnh; câu nói với khách lấy nguyên văn mẫu của `error_codes.reply_vi`.
- Router xếp mỗi tin vào một ý định: `repair`, `service`, `question`, `book`, `greeting`, `offtopic`. Khách kể máy mình hỏng, kể cả dưới dạng câu hỏi ("máy lạnh chảy nước là sao vậy em"), là `repair`; hỏi thông tin mà không kể máy mình hỏng là `question`.
- `question` đi tầng hỏi đáp (`answer.py`, xem dưới), dùng được cả khi đang giữa một cuộc chẩn đoán: thanh đặt lịch giữ nguyên dịch vụ đã chốt, câu hỏi tiếp ("sửa có lâu không", "tự làm được không") được hỏi về đúng bệnh vừa chốt.
- `book` sau khi đã chốt: một câu mời bấm "Đặt thợ ngay" cho đúng dịch vụ đó, không chẩn đoán lại.
- Đổi chủ đề: chỉ tin mới nhất đổi được máy đang nói. Tin gọi tên máy khác thì chuyển hẳn sang máy đó; gọi cả máy cũ lẫn máy mới thì xét cả hai; không gọi tên máy nào thì ở lại máy đang nói.

Câu khách đọc: bước an toàn (lỗi HIGH) + nghĩa mã lỗi (nếu có) + 1-2 câu của model. Tên dịch vụ và giá không nhắc lại trong câu, vì web hiện trên thanh đặt lịch. Lượt hỏi: `messageVi` để trống, câu hỏi nằm ở `clarification.questionsVi[0]`, nút ở `clarification.answerOptionsVi`.

## Chia tri thức (RAG)

Kho cũ cắt 166 tài liệu theo heading thành 3.319 đoạn và truy hồi theo chữ trùng, nên một câu về mùi có thể kéo về đoạn áp suất gas của lỗi bên cạnh. Chẩn đoán ở đây không phải bài toán tìm kiếm: một thiết bị có tối đa 12 lỗi, nên model được xem đủ. Thứ model thiếu là chuyên môn phân biệt các lỗi, nên đơn vị chia là một lỗi một thẻ (`app/data/fault_cards.json`, sinh bằng `tools/build_fault_cards.py` từ chính tài liệu, không viết tay):

- `signs_vi`: khách hay tả thế nào (`symptoms_vi`)
- `rule_out_vi`: "Khi nào KHÔNG kết luận", đưa vào prompt dưới dạng "Không phải lỗi này nếu" (để nguyên chữ "không kết luận" thì model hiểu là phải hỏi lại)
- `ask_vi`: câu hỏi quyết định ("Cây hỏi")
- `versus_vi`: cách tách với từng lỗi dễ nhầm ("Lẫn với bệnh nào", "Phân biệt với ...")
- `summary_vi`: nói ngắn gọn bệnh là gì

Sửa tài liệu thì chạy lại `python tools/build_fault_cards.py`; `tests/test_chat2.py` báo khi thẻ cũ hơn tài liệu.

## Hỏi đáp (RAG cho câu không phải chẩn đoán)

Kho: `app/data/knowledge_index.json`, sinh bằng `tools/build_knowledge_index.py`. Đơn vị chia là một mục `##` của tài liệu, vì README của kho bắt mỗi mục đọc một mình vẫn hiểu. Lấy: 7 tài liệu hệ thống (FixHome là gì, vai trò AI, quy trình đặt lịch, giá, bảo hành, khu vực, câu hỏi thường gặp), mục "Em là ai" của persona, 22 tài liệu thiết bị, và các mục khách hỏi sau chẩn đoán của tài liệu lỗi (nói ngắn gọn, để lâu thì sao, tự kiểm tra, thợ làm gì, chi phí, giữ cho bệnh không tái...). Bỏ: mục viết cho trợ lý chứ không phải cho khách (kịch bản mẫu, nguồn, câu cấm nói, chờ thợ xác nhận, cách khách gõ sai) và mục đọc ảnh (model chat không xem ảnh). Thêm hai loại sinh từ catalog: "FixHome đang nhận những dịch vụ gì" và bảng giá từng thiết bị, để giá và danh sách dịch vụ không bao giờ là câu ai đó gõ tay rồi quên sửa. 985 đoạn: 66 nền tảng, 392 thiết bị, 527 theo lỗi.

Mỗi đoạn có phạm vi: `platform` luôn được dùng, `device:<loại>` khi cuộc chat đang nói máy đó, `fault:<mã>` khi bệnh đó vừa được chốt. Truy hồi có ba bước, mỗi bước sửa một lỗi đo được:

1. Rút gọn (`answer.shortlist`): trong các đoạn thuộc phạm vi, lấy 16 đoạn sát nhất theo chữ (độ hiếm của chữ, tiêu đề tính gấp ba, cặp chữ liền nhau), cộng luôn bảng giá của thiết bị, danh sách dịch vụ và 14 mục nền tảng lõi (FixHome là gì, em là ai, thanh toán, phát sinh, báo giá, bảo hành, huỷ, khu vực, thợ được kiểm tra, chọn thợ...). Mục lục 110 dòng làm model chọn nhầm ("thợ có được kiểm tra lý lịch không" bỏ qua mục có đúng tên đó); mục lõi có mặt vì "thợ đòi thêm tiền" không chung chữ nào với "Chi phí phát sinh".
2. Chọn: model xem mục lục 30 dòng, mỗi dòng kèm đoạn chữ quanh từ hiếm nhất của câu hỏi có trong mục (không phải câu mở đầu: "bình nóng lạnh có sợ giật không" nằm ở dòng thứ ba của mục "thiết bị nguy hiểm nhất trong nhà tắm"), chọn tối đa 3 mục theo enum.
3. Trả lời: model chép nguyên văn câu bằng chứng vào `quote` rồi mới viết `reply` tối đa hai câu. Đo 06/11: không có bước chép, model cầm danh sách quận có Gò Vấp vẫn trả lời "chưa có thông tin". Có bước chép, nó chép đúng câu rồi vẫn viết "chưa có thông tin", vì model nhỏ lặp lại câu dự phòng prompt cho nó xem; nên code (`answer._tidy`) bỏ câu đó khi đã có trích, và dùng chính câu trích khi không còn gì khác. Câu hỏi giá luôn nhận bảng giá của mọi thiết bị đang nói. Không có trích nào thì nói chưa có thông tin, không đoán.

`app/data/knowledge/system/cau-hoi-thuong-gap.md` (06/11) bổ sung các câu khách hay hỏi mà tài liệu khác chưa nói thẳng (thợ có được kiểm tra không, chọn thợ được không, nhắn tin với thợ, thợ huỷ, khi nào đơn xong, đánh giá, ảnh dùng làm gì), lấy từ các mục đã chốt của `docs/SEP490- tổng.md`.

## Hai bài học hạ tầng

- Ép JSON viết liền bằng regex làm model chọn sai ("vệ sinh tủ lạnh" ra bếp gas): ép model ra khỏi chuỗi token nó quen viết. Dùng JSON schema thường.
- JSON schema của vLLM cho phép khoảng trắng; Qwen3 sinh xuống dòng sau trường cuối tới hết `max_tokens`, kể cả với `disable_any_whitespace`. Cắt bằng `stop: ["\n\n\n"]` (chuỗi JSON không chứa xuống dòng thật) rồi tự đóng ngoặc (`_parse`).

## Đo

Hai bộ, cùng server, chạy được với mọi model OpenAI-compatible:

- `tools/eval_chat2.py`: 707 ca cố định. `scripted` (ca PO, BUG 52/54, `tools/chat2_cases.py`), `clear` (nửa test `understanding_bank.json`, có ảnh), `vague`, `service` (`service_understanding_cases.py`), `offtopic`.
- `tools/probe_chat2.py`: test sâu qua chính `Chat2Provider` (router, hỏi đáp, chẩn đoán, đổi chủ đề, đặt lịch, phiên nhiều lượt), 81 cuộc chat viết tay theo nhóm nền tảng, kiến thức, chẩn đoán, ngữ cảnh, ca biên; in từng câu trả lời để người đọc. `--holdout` (34 cuộc) và `--holdout2` (25 cuộc) là các bộ viết sau khi đã sửa, mỗi bộ báo số lần chạy đầu tiên trước khi được dùng để sửa tiếp.
- `tools/sim_chat2.py`: test tự do. 45 kịch bản do người kiểm thử viết (`tools/chat2_freestyle.py`), không lấy từ ngân hàng câu; mỗi kịch bản giấu sự thật, khách giả lập (chính model đó) chỉ trả lời theo `facts`. Mỗi cuộc chấm đúng/sai và xếp lỗi theo tầng: `routing`, `reasoning`, `service`, `dialogue`, `scope`, `safety`, `style`, `detail`.

Số đo 06/11/2026, RTX 3090 thuê, vLLM v0.33.0, cùng thiết kế, cùng prompt:

| | Qwen3.5-9B FP8 | Gemma 4 12B QAT | Qwen3-14B AWQ | Qwen2.5-VL-3B AWQ |
|---|---|---|---|---|
| Tự do (90 cuộc, mỗi kịch bản 2 lần) | 100% | 97,8% | 95,6% | |
| Scripted (17) | 17/17 | 15/17 | 17/17 | 0/17 |
| Clear (515): đúng / chốt luôn | 83,1% / 99,4% | 84,3% / 98,3% | 78,8% / 94% | 0% |
| Service (60) | 91,7% | 86,7% | 95% | |
| Vague hỏi lại (66) | 86,4% | 100% | 98,5% | |
| Trễ p50 / p95, 24 luồng | 8,3 / 11,5 s | 12,4 / 20,1 s | 8,6 / 17,1 s | |

Sau lượt đo này đã thêm các luật ở mục trên (câu chỉ có chữ chung chung thì hỏi, mã lỗi không có trong bảng thì bỏ qua con mã, hỏi đáp theo mục lục, đổi chủ đề) và đo lại Qwen3.5-9B ở hai bản lượng tử, cùng code:

| | FP8, RTX 3090 24GB | AWQ 4-bit, RTX 4060 Ti 16GB |
|---|---|---|
| Scripted (17) | 17/17 | 17/17 |
| Clear (515): đúng / sai mà chắc | 83,1% / 16,1% | 75,9% / 22,3% |
| Service (60) | 91,7% | 93,3% |
| Vague hỏi lại (66) | 83,3% | 80,3% |
| Probe 81 cuộc / holdout 34 / holdout2 25 | 93,8% / 91,2% / 100% | 97,5% / 100% / 100% (sau sửa) |
| Trễ p50 / p95 | 5,8 / 7,5 s (6 luồng) | |

Probe FP8 có 3 lượt lỗi mạng của máy thuê, tính là sai. Bản AWQ chạy được card rẻ hơn nhưng chọn sai lỗi nhiều hơn khoảng 6 điểm ở câu mô tả rõ, nên mặc định thuê card 24GB (`rent_gpu.py offers --min-vram 24`).

Giới hạn còn biết: khách tự chẩn đoán sai ("hết gas rồi, chảy nước tong tong") đôi khi được tin theo; `clear` là câu đội viết, chưa phải câu khách thật; khách giả lập là chính model đang đo nên có thể dễ tính hơn khách thật.

Lặp lại số đo: `python tools/eval_chat2.py --base-url http://<máy>/v1 --model <tên> --api-key <key> --extra '{"chat_template_kwargs":{"enable_thinking":false}}'` và `python tools/sim_chat2.py ... --repeat 2 --md sim.md`.
