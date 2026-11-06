# Chat brain v2: detector + LLM + thẻ chuyên môn

Từ 06/11/2026 (PO chốt), chat AI chạy bằng `app/services/chat2` (`AI_ENGINE=chat2`, mặc định trong image serve). Pipeline cũ (`app/services/pipeline/local_pipeline.py`) vẫn còn cho `AI_ENGINE=local` nhưng không còn là đường chính.

## Vì sao làm lại

Pipeline cũ chọn lỗi bằng cách khớp chữ câu khách với danh sách triệu chứng (truy hồi lexical), rồi để Qwen2.5-VL-3B viết lại. Câu khách không trùng chữ là ra lỗi lạc: "máy lạnh rơi xuống đất" thành nghẹt thoát nước, "mùi hôi như thối, rất bẩn" thành chập điện, "tủ lạnh mùi hôi" thành hỏng máy nén. Đo cùng thiết kế mới, Qwen2.5-VL-3B trả "không phải việc sửa chữa" cho 489/515 câu mô tả rõ: model 3B không đủ sức theo một prompt dài có cấu trúc.

## Vai của từng phần

- YOLO11s (`detector-v2-yolo11s`): đọc ảnh, ra loại thiết bị. Model chat không bao giờ nhận ảnh.
- LLM `Qwen/Qwen3.5-9B` (FP8 lúc nạp, tắt đầu vào ảnh/video, tắt chế độ suy nghĩ): đọc cả cuộc trò chuyện, điền `need` (khách cần gì), `need_kind` (`hong_hoc`, `hu_hai`, `xin_viec`, `chua_ro`), `fault_code`, `service_code`, `reply`, `options`. Giải mã dưới JSON schema mà enum là đúng mã lỗi, mã dịch vụ của thiết bị đó.
- Code (`brain._decide`): quyết hỏi hay chốt. Khách đã kể hiện tượng, hư hại hay xin việc là chốt; chưa kể gì (`chua_ro`, hoặc `need` chỉ có chữ chung chung như "hư", "có vấn đề") mới hỏi đúng một câu kèm 2-4 nút; tối đa 2 câu hỏi một cuộc. Hư hại (rơi, vỡ, ngấm nước) luôn ra dịch vụ sửa. Lỗi có tên luôn ra dịch vụ catalog ánh xạ cho lỗi đó.
- Router: mỗi lượt xác định thiết bị khách nhắc (tối đa 3) và ý định. Chữ gọi đích danh tên máy (tên hoặc alias trong `device_catalog.json`, bỏ qua "như cái X") chỉ thắng ảnh giữa các cặp detector hay nhầm (`confusable_with`); máy khác chữ nhắc tới thành thiết bị thêm, mỗi máy chẩn đoán riêng (`Verdict.others`). Có ảnh thì router không được tự từ chối "lạc đề".
- Mã lỗi theo hãng (`error_codes.json`): nghĩa chính thức đưa vào ngữ cảnh; câu nói với khách lấy nguyên văn mẫu của `error_codes.reply_vi`.
- Câu chính sách (giá, bảo hành, cách FixHome làm việc) không nhắc thiết bị: trả lời từ đoạn chính sách (`Retriever.policy_passages`), tối đa hai câu, kèm trích dẫn.

Câu khách đọc: bước an toàn (lỗi HIGH) + nghĩa mã lỗi (nếu có) + 1-2 câu của model. Tên dịch vụ và giá không nhắc lại trong câu, vì web hiện trên thanh đặt lịch. Lượt hỏi: `messageVi` để trống, câu hỏi nằm ở `clarification.questionsVi[0]`, nút ở `clarification.answerOptionsVi`.

## Chia tri thức (RAG)

Kho cũ cắt 166 tài liệu theo heading thành 3.319 đoạn và truy hồi theo chữ trùng, nên một câu về mùi có thể kéo về đoạn áp suất gas của lỗi bên cạnh. Chẩn đoán ở đây không phải bài toán tìm kiếm: một thiết bị có tối đa 12 lỗi, nên model được xem đủ. Thứ model thiếu là chuyên môn phân biệt các lỗi, nên đơn vị chia là một lỗi một thẻ (`app/data/fault_cards.json`, sinh bằng `tools/build_fault_cards.py` từ chính tài liệu, không viết tay):

- `signs_vi`: khách hay tả thế nào (`symptoms_vi`)
- `rule_out_vi`: "Khi nào KHÔNG kết luận", đưa vào prompt dưới dạng "Không phải lỗi này nếu" (để nguyên chữ "không kết luận" thì model hiểu là phải hỏi lại)
- `ask_vi`: câu hỏi quyết định ("Cây hỏi")
- `versus_vi`: cách tách với từng lỗi dễ nhầm ("Lẫn với bệnh nào", "Phân biệt với ...")
- `summary_vi`: nói ngắn gọn bệnh là gì

Sửa tài liệu thì chạy lại `python tools/build_fault_cards.py`; `tests/test_chat2.py` báo khi thẻ cũ hơn tài liệu.

## Hai bài học hạ tầng

- Ép JSON viết liền bằng regex làm model chọn sai ("vệ sinh tủ lạnh" ra bếp gas): ép model ra khỏi chuỗi token nó quen viết. Dùng JSON schema thường.
- JSON schema của vLLM cho phép khoảng trắng; Qwen3 sinh xuống dòng sau trường cuối tới hết `max_tokens`, kể cả với `disable_any_whitespace`. Cắt bằng `stop: ["\n\n\n"]` (chuỗi JSON không chứa xuống dòng thật) rồi tự đóng ngoặc (`_parse`).

## Đo

Hai bộ, cùng server, chạy được với mọi model OpenAI-compatible:

- `tools/eval_chat2.py`: 707 ca cố định. `scripted` (ca PO, BUG 52/54, `tools/chat2_cases.py`), `clear` (nửa test `understanding_bank.json`, có ảnh), `vague`, `service` (`service_understanding_cases.py`), `offtopic`.
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

Sau lượt đo này đã thêm hai luật code đo bằng unit test, chưa đo lại trên GPU: câu chỉ có chữ chung chung thì hỏi (nhằm vào 86,4% vague), và mã lỗi không có trong bảng hãng thì bỏ qua con mã.

Giới hạn còn biết: khách tự chẩn đoán sai ("hết gas rồi, chảy nước tong tong") đôi khi được tin theo; `clear` là câu đội viết, chưa phải câu khách thật; khách giả lập là chính model đang đo nên có thể dễ tính hơn khách thật.

Lặp lại số đo: `python tools/eval_chat2.py --base-url http://<máy>/v1 --model <tên> --api-key <key> --extra '{"chat_template_kwargs":{"enable_thinking":false}}'` và `python tools/sim_chat2.py ... --repeat 2 --md sim.md`.
