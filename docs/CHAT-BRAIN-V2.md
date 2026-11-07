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
- Hỏi lại kết luận (07/11): đã chốt mà khách chỉ đáp cụt ("Không.", "đúng rồi") hoặc hỏi chính kết luận không kèm gì cụ thể ("vậy giờ em thấy sao", "vậy là bị gì") thì code (`asks_for_the_verdict`) nhắc lại đúng bệnh đã chốt kèm lời mời bấm "Đặt thợ ngay". Chạy live 07/11, tầng hỏi đáp trả bảng giá cho "Vậy giờ em thấy sao?" và danh sách nhóm lỗi cho "Không.", vì nó buộc phải chọn một mục tài liệu. Thử thêm ý định `followup` vào router trước: probe 81 cuộc tụt từ 38/38 xuống 34/38 ở nhóm ngữ cảnh, vì model gộp luôn "sửa có lâu không", "bảo hành bao lâu", "có nguy hiểm không" vào đó; nên việc này nằm ở code với tập câu hẹp, router giữ nguyên.
- Lỗi có tên mà là hư hại (kính bếp từ nứt, móc quạt trần lỏng, nắp bồn cầu gãy, bình nóng lạnh rò): là đúng lỗi đó, không phải "hư hại chung". Đo 06/11, luật cũ "hư hại thì NONE" là 51 trong 87 ca sai ở bộ `clear`. NONE chỉ còn cho rơi, va đập chung chung.
- Lượt chọn lỗi thứ hai (`needs_fault`, `_pick_fault`): khách đã kể hiện tượng hoặc hư hại mà model vẫn để NONE thì gọi thêm một lần ngắn, chỉ còn trường `fault_code`, enum là mã lỗi của đúng thiết bị (không có NONE với hiện tượng; có NONE với hư hại). Một JSON phải điền cùng lúc nhu cầu, loại, lỗi, dịch vụ và câu trả lời; tách riêng việc chọn lỗi khi lần đầu bỏ trống là sửa rẻ, chỉ tốn thêm ở các lượt đó.
- `book` sau khi đã chốt: một câu mời bấm "Đặt thợ ngay" cho đúng dịch vụ đó, không chẩn đoán lại.
- Tên máy khách gõ đích danh (tên hoặc alias catalog, `named_in`) thắng máy router đoán, ngay trong `brain.turn` chứ không chỉ ở provider: "lắp đèn trần" là bóng đèn chứ không phải quạt trần, "lắp đặt bếp điện" là bếp từ chứ không phải quạt điện (07/11, bộ `service`). Máy router đoán chỉ được giữ nếu khách có gọi tên ở đâu đó trong cuộc chat. Máy đã được gọi tên thì không bao giờ là "lạc đề" ("lap khoa van tay" từng bị từ chối).
- Câu mơ hồ xét trên chính lời khách, không chỉ trên `need` model chép lại: "mấy bữa nay hơi kỳ kỳ" từng được chốt theo một hiện tượng model tự viết ra. Trước khi trợ lý hỏi câu nào, mỗi tin của khách được xét riêng; sau một câu hỏi thì "Không" là câu trả lời có nghĩa, không xét nữa. Động từ dùng máy (chạy, nấu, nướng...) đi với một chữ đánh giá chung chung ("không ổn", "sao sao") cũng là chưa kể gì, nhưng chỉ khi còn đúng một động từ: bỏ dấu thì "chảy nước" thành "chay nuoc", là hiện tượng.
- Máy mới được gọi tên lần đầu ở tin mới nhất thì chỉ được chẩn đoán từ tin đó (`brain._scope`): chạy live 07/11, "còn cái tủ lạnh nhà em kêu to lắm" sau "máy lạnh chảy nước" ra tủ lạnh nghẹt thoát nước, vì model mang nước của máy lạnh sang.
- Khách nói máy đã được sửa hay vệ sinh trước đó ("thợ bên em làm", "mới vệ sinh tuần trước mà lại chảy nước"): code thêm một câu về mục Bảo hành điện tử, đúng như `system/bao-hanh.md` cho phép nói (thợ xem lại, đúng chỗ đã sửa trong thời hạn thì thuộc bảo hành), mỗi cuộc chat một lần.
- Giật điện, tê tay, rò điện: code đặt bước "ngắt aptomat, không bật lại, không chạm khi chân ướt" lên đầu dù lỗi nào được chọn (`SHOCK_STEP`, theo mục "An toàn điện" của `devices/washing_machine.md`): máy giặt không có lỗi nào tên là giật điện, nên trước đó câu trả lời chỉ nói bo mạch.
- Trợ lý vừa hỏi mà khách đáp cụt ("Không") thì là trả lời câu hỏi chẩn đoán, không đưa sang tầng hỏi đáp.
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
3. Trả lời: model chép nguyên văn câu bằng chứng vào `quote` rồi mới viết `reply` tối đa hai câu. Đo 06/11: không có bước chép, model cầm danh sách quận có Gò Vấp vẫn trả lời "chưa có thông tin". Có bước chép, nó chép đúng câu rồi vẫn viết "chưa có thông tin", vì model nhỏ lặp lại câu dự phòng prompt cho nó xem; nên code (`answer._tidy`) bỏ câu đó khi đã có trích, và dùng chính câu trích khi không còn gì khác. Câu hỏi giá luôn nhận bảng giá của mọi thiết bị đang nói. Không có trích nào thì nói chưa có thông tin, không đoán. Câu trích chỉ được dùng thay câu trả lời khi model đánh dấu có căn cứ và câu trích chứa một từ hiếm (hay một cặp chữ) của câu hỏi (`quote_holds_the_question`): chạy live 07/11, "có trả góp không" ra "không có khoản ký quỹ của thợ", vì model gọi một câu gần chủ đề là có căn cứ. Khi bệnh đã chốt, cả các mục của bệnh đó (tối đa 12) luôn có trong mục lục, để "giờ em phải làm gì trước", "có nguy hiểm không" tìm được "Khách tự kiểm tra", "Khi nào ca này thành gấp".

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

Probe FP8 có 3 lượt lỗi mạng của máy thuê, tính là sai.

Chạy live 07/11 bằng chính image serve trên RTX 3090 (tự chọn FP8), qua `/api/v1/diagnosis/analyze` như Backend gọi: `tools/live_chat2.py` 8/8 cuộc đúng dịch vụ, trễ p50 2,8 s. `tools/load_test.py --mix` (một nửa khách nói 2-3 máy, có ảnh): 10 khách cùng lúc 0 lỗi, p95 8,9 s; 30 khách 0 lỗi, p95 21,9 s; 50 khách 10/50 quá hạn 25 s, p95 32,9 s. Một card phục vụ khoảng 30 cuộc chat cùng lúc, khoảng 40 cuộc mỗi phút; lượt quá hạn Backend chuyển sang luồng đặt tay, không chặn đặt lịch. Bản AWQ chạy được card rẻ hơn nhưng chọn sai lỗi nhiều hơn khoảng 6 điểm ở câu mô tả rõ, nên mặc định thuê card 24GB (`rent_gpu.py offers --min-vram 24`).

Vòng 07/11 (RTX 3090, FP8, vLLM gốc, code chạy trên máy dev; mỗi dòng là một lần chạy đủ bộ):

| | v2 | v3: thêm lượt tự kiểm | v4 (đang dùng) |
|---|---|---|---|
| Clear (515): đúng / sai mà chắc | 89,9% / 8,9% | 82,5% / 16,7% | 89,5% / 9,5% |
| Vague hỏi lại (66) | 84,8% | 84,8% | 98,5% |
| Service (60) | 91,7% | 95% | 98,3% |
| Scripted (17), offtopic (49) | 17/17, 95,9% | 17/17, 95,9% | 17/17, 95,9% |
| Probe 81 / holdout 34 / holdout2 25 / holdout3 23 | 97,5% / 100% / 100% / 100% | 96,3% / 100% / 100% / 100% | 97,5% / 100% / 100% / 100% |
| Tự do (90 cuộc) | 95,6% | 94,4% | 100% |
| Trễ p50 bộ 707 ca | 3,9 s | 5,3 s | 3,9 s |

v2 là các sửa ở trên (hư hại có tên, lượt chọn lỗi thứ hai, nhắc lại kết luận), từ 83,1% lên 89,9% ở `clear`. v3 thử một lượt tự kiểm: đưa lỗi đã chọn cùng 3-4 lỗi dễ nhầm và hỏi lời khách có trúng điều "Không phải lỗi này nếu" nào không, chỉ đổi khi model chép được điều đó. Kết quả tệ hơn rõ: model chép ra một điều không trúng rồi đổi khỏi lỗi đúng, sai mà chắc gần gấp đôi, nên đã bỏ. v4 là hai luật tên máy và câu mơ hồ ở trên. Holdout3 (23 cuộc, viết 07/11 trước khi đo) lần đầu 20/23, ba ca hỏng là do bộ chấm đòi nhánh `answer` ở chỗ nhắc lại kết luận mới đúng.

Chạy live 07/11 trên fixhome.sbs (image 3a50c16, bấm thật trên web bằng Playwright) 21/22; ca hỏng duy nhất là nút trả lời nhanh, chờ web đọc `answerOptionsVi`. 18 cuộc chat tự do mới qua API tìm ra các lỗi đã sửa ở trên (đổi máy mang ngữ cảnh máy cũ, câu trích lạc đề, câu hỏi sau chẩn đoán không có mục của bệnh, bảo hành, giật điện); giữ lại thành `tools/probe_live.py` (`--live`). Sau các sửa đó (v7, v8): probe 81 cuộc 98,8%, holdout 1/2/3 100%, live 14/14, tự do 90/90; bộ 707 ca không đổi so với v4 (các sửa này nằm ở provider và tầng hỏi đáp, bộ 707 ca gọi thẳng `brain.turn`).

Còn sai ở `clear` sau v4 phần lớn là nhầm giữa hai lỗi giống nhau với câu kể rất gián tiếp ("con mèo không dám nằm trên cục nóng nữa"), cùng một vài nhãn còn bàn được (rung lắc khi vắt ra mòn bạc đạn: kho chưa có lỗi giảm xóc).

Giới hạn còn biết: khách tự chẩn đoán sai ("hết gas rồi, chảy nước tong tong") đôi khi được tin theo; `clear` là câu đội viết, chưa phải câu khách thật; khách giả lập là chính model đang đo nên có thể dễ tính hơn khách thật.

## Vòng 07/11 chiều: hỏi tự do và adapter chọn lỗi

PO yêu cầu hỏi nhiều câu không theo nguyên tắc nào. 50 cuộc (`scratchpad free2`, không dấu, teencode, emoji, tiếng Anh, chửi, kể lan man, chen lệnh lạ, nhiều máy một câu, máy ngoài danh mục) chạy qua `/api/v1/diagnosis/analyze` y như Backend gọi, gửi lại `diagnosticState` mỗi lượt. Những cuộc hỏng được giữ thành `tools/probe_free.py` (`--free`). Sửa theo tầng:

- Hỏi đáp: câu trả lời được kiểm lại với các đoạn tài liệu bằng một lượt riêng chỉ trả có hay không (`answer._verified`). Không có căn cứ thì khách chỉ nhận câu "em chưa có thông tin" của chính model, câu khẳng định tự nghĩ bị bỏ (`answer.unsupported`). Trước đó "có thợ nữ không" ra "Có, anh/chị chọn được thợ nữ", "lắp máy lạnh có cần mua ống đồng không" ra "Cần mua thêm", "thợ có mang đồ nghề không" ra một câu không có trong tài liệu nào. Kiểm câu trích có trả lời câu hỏi không thì quá chặt ("có nổ không" được trả lời bởi "không nguy hiểm tức thì" bị loại), nên kiểm điều câu trả lời khẳng định. Prompt thêm: chỉ nói có hay không khi tài liệu nói đúng điều đó; danh sách khu vực, thiết bị, dịch vụ là đầy đủ; không hỏi lại, không hứa tư vấn thêm.
- Tên gọi khác của máy chỉ được cắt ở đầu câu khi khách chưa gọi đúng tên máy (`describes_nothing`): "bếp gas có mùi gas" mất chữ "mùi gas" (một alias của bếp gas) và bị hỏi lại "có ngửi thấy mùi gas không".
- `named_in`: tên đã gập có khoảng trắng hai đầu, hai tên đứng sát nhau ("vòi nước bồn rửa chén") bị coi là chồng nhau, vòi nước bị bỏ và vòi nhỏ giọt thành rò ống thoát bồn rửa.
- Máy ngoài danh mục: router điền `other_appliance` (máy sấy tóc, nồi cơm điện, máy lọc không khí, robot hút bụi) và code nói thẳng FixHome chưa nhận, thay vì hỏi "thiết bị nào" hay ép về máy gần giống (máy sấy tóc thành máy sấy quần áo vì alias "máy sấy"). Tên có chứa alias mà là thứ khác thì ghi trong danh mục (`not_aliases_vi`: "máy sấy tóc" không phải máy sấy quần áo); tên lạ router điền chỉ dùng để từ chối khi khách không gọi máy nào trong danh mục. Dò alias bên trong tên lạ đã được thử và bỏ: nó gạt mất máy lọc nước khỏi "lõi lọc nước RO bao lâu thay".
- Tên máy không được đọc vắt qua dấu câu (`_fold_names`): "bếp từ, mặt kính nứt" gập thành "bep tu mat kinh" và chứa alias "tủ mát" của tủ lạnh.
- Khách kể rơi, ngã, đổ, va đập mà không nói hư hại nào có trong tên lỗi model chọn thì không gắn lỗi, đặt dịch vụ sửa để thợ kiểm tra (`IMPACT_WORDS`): ca máy lạnh rơi của PO ("bị rơt xuống đất") từng ra hỏng bo mạch với adapter; "làm rơi nồi, mặt kính nứt" vẫn giữ lỗi nứt kính.
- Câu hỏi giá bắt đầu bằng "giá vệ sinh, giá sửa, giá lắp…" là câu hỏi giá; tầng hỏi đáp không hỏi ngược khách (`no_questions_back`); câu trích dạng nhãn ("Đã nhận: …") chỉ thay câu trả lời khi chứa từ hiếm của câu hỏi.
- Hư hại không gắn lỗi không còn bị gọi là "va đập" (dây bị chuột cắn); dây điện hở lõi có bước rút phích trước (`WIRE_STEP`). Câu chốt không được nói "em chuyển, em đặt, em cử" (`SELF_ACTS`). Câu từ chối viết lại cho hợp cả "laptop không lên nguồn" lẫn "hôm nay trời đẹp nhỉ".
- Nhắc đơn cũ (BUG 53): chat2 trước đây bỏ hẳn `pastJobs`. Nay mỗi máy nhắc một lần khi chốt, theo trạng thái đơn ("đã sửa ngày…" với COMPLETED, "đang có lịch ngày…" với SCHEDULED, chữ PO duyệt 01/11), không nhắc cạnh bước an toàn, và ghi cho thợ trong `notesVi`.

Adapter chọn lỗi (LoRA r16 trên các phép chiếu attention và MLP của Qwen3.5-9B bf16, phục vụ trên nền FP8 bằng `--lora-modules`): dữ liệu là nửa dev của `understanding_bank` (1.225 câu), mỗi câu cho model gốc chạy đúng prompt chẩn đoán nhưng schema ghim `fault_code` đúng nhãn, để phần còn lại của JSON do chính model viết quanh đáp án đúng. Model gốc tự đúng 89% số câu này. Bản đầu dùng cho mọi lượt gọi thì hỏng router ("máy in kẹt giấy" thành lò vi sóng) và, vì chỉ học câu có lỗi, chốt cả ca máy lạnh rơi của PO thành hỏng bo mạch. Sửa: adapter chỉ dùng cho lượt chẩn đoán (`CHAT_TURN_MODEL`), router và hỏi đáp vẫn là model gốc; thêm 299 câu mơ hồ và hư hại chung chung tự viết (không lấy từ bộ chấm) với đáp án hỏi lại hoặc không gắn lỗi.

Lượt kiểm căn cứ được đo hai kiểu. Cho xem cả câu hỏi thì nó loại cả câu đúng (tổng giá hai máy, so sánh vệ sinh với sửa, giải thích vì sao tốn điện), probe 98,8% xuống 95,1%, mà vẫn cho qua "Cần mua thêm ống đồng"; nên chỉ kiểm câu trả lời với tài liệu, và không kiểm câu hỏi giá (giá đọc từ bảng của danh mục). Model 9B tự kiểm chính nó vẫn là bộ lọc thô: ca ống đồng còn lọt.

Số cuối (RTX A6000, FP8, cùng code, adapter chỉ cho lượt chẩn đoán; mỗi ô một lần chạy):

| | Model gốc | Adapter chat2-pick-v2 |
|---|---|---|
| Clear (515): đúng / sai mà chắc | 89,5% / 9,5% | 91,1% / 8,5% |
| Vague (66) / service (60) | 98,5% / 98,3% | 100% / 100% |
| Scripted (17) / offtopic (49) | 17/17, 95,9% | 17/17, 95,9% |
| Probe 81 / holdout 34 / holdout2 / holdout3 / live / free | 95,1% / 91,2% / 100% / 95,7% / 100% / 15 của 17 (trước hai sửa cuối) | 98,8% / 94,1% / 100% / 100% / 100% / 17/17 |
| Giả lập khách (90) | | 89/90 |
| Trễ p50 bộ 707 ca | 4,3 s | 4,4 s |

Adapter sửa được ca PO biết từ trước ("ngăn mát không lạnh mà ngăn đá vẫn lạnh" ra thiếu gas ở model gốc) và "tủ chạy êm mà tiền điện tăng gấp đôi" (gioăng cửa thay vì thiếu gas). Image serve tải nó từ `HF_WEIGHTS_REPO/chat2-pick-v2` (`LORA_RUN`, mặc định trong `rent_gpu.SERVE_LORA_RUN`), chỉ trên bản FP8. Huấn luyện lại: `tools/chat2_lora/` (sinh dữ liệu bằng model đang chạy, train 1 epoch khoảng 50 phút trên A6000).

Còn biết: "sửa có lâu không" sau khi chốt nghẹt thoát nước đôi khi trả lời chung chung dù thẻ lỗi có thời gian; "lắp máy lạnh có cần mua ống đồng không" vẫn có lúc được trả lời "Cần" (tài liệu không có câu nào về việc này); câu hỏi kiểu "em có yêu anh không" ra lời chào thay vì từ chối.

Lặp lại số đo: `python tools/eval_chat2.py --base-url http://<máy>/v1 --model <tên> [--turn-model <adapter>] --api-key <key> --extra '{"chat_template_kwargs":{"enable_thinking":false}}'` và `python tools/sim_chat2.py ... --repeat 2 --md sim.md`.
