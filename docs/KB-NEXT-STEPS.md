# Kho tri thức RAG — hiện trạng và việc tiếp theo

Cập nhật: 17/09/2026. Nhánh `feat/rag-knowledge-corpus`.

## Đã xong

**132 file markdown, 2.877 chunk, 2.095.511 ký tự** trong `app/data/knowledge/`.

| Tầng | Số file | Nội dung |
|---|---|---|
| `faults/` | 108 | Một file cho mỗi mã bệnh trong `fault_knowledge_base.json`. Đủ 108/108. |
| `devices/` | 17 | Một file cho mỗi thiết bị trong `device_catalog.json`. Đủ 17/17. |
| `persona/` | 2 | `giong-noi.md`, `quy-tac-ung-xu.md` |
| `system/` | 5 | Tổng quan FixHome, quy trình đặt lịch, cách tính tiền, bảo hành, vai trò AI |

Kèm theo:

- `app/data/acknowledgements.json` — 10 nhóm câu xác nhận, gồm nhóm `safety_first` thay thế mọi câu xã giao khi phát hiện tín hiệu nguy hiểm.
- `app/services/pipeline/acknowledgement.py` — chọn câu theo tình huống, không lặp trong cùng phiên, khớp cả tiếng Việt không dấu.
- `GET /api/v1/chat/acknowledgements` — client lấy toàn bộ tập câu để hiện ngay khi người dùng gửi tin.
- `tools/chunk_kb.py` — cắt chunk theo `##`, báo cáo phân bố, chỉ ra chunk ngoài ngưỡng.
- `tests/test_knowledge_chunks.py` — hợp đồng chunk và hợp đồng dữ liệu, chạy trên từng file.

Gate hiện tại: **1232 test pass**, `ruff` sạch.

## Việc thứ nhất, thứ hai và thứ ba: đã xong

Ba việc này làm liền một mạch vì chúng phụ thuộc nhau: không nối corpus thì không đo được, không đo được thì không biết nhánh an toàn có chạy hay không.

**Nối corpus vào retrieval.** Trình đọc corpus chuyển từ `tools/chunk_kb.py` sang `app/services/pipeline/corpus.py`, để đường chạy production không phụ thuộc vào thư mục công cụ; `tools/chunk_kb.py` giờ chỉ còn in báo cáo. Lọc theo `device_type` trước khi chấm điểm, và chỉ lấy văn bản khi danh sách bệnh nghi ngờ khác rỗng. Chấm điểm bằng BM25 chứ không phải đếm từ trùng: cách đếm cũ cho mọi chunk của cùng một thiết bị số điểm 1.00 như nhau, thứ tự rơi về thứ tự bảng chữ cái. Mục an toàn không xếp hạng mà được ghim, khai báo bằng khoá `safety_heading` trong frontmatter của cả 25 bệnh HIGH.

**Bộ đánh giá.** `tools/chat_cases.py` có 143 ca viết theo đúng kiểu khách hàng viết, `tools/eval_retrieval.py` chấm chúng không cần server và không cần GPU. Số đo hiện tại: danh sách bệnh 100%, lấy đúng văn bản 100%, ghim cảnh báo 100%, im lặng khi hỏi ngoài phạm vi 100%, tra cứu dịch vụ 4/5.

**Nhánh an toàn.** `tests/test_safety_first.py` kiểm từng câu lệnh bắt buộc, còn `tests/test_retrieval_quality.py` giữ các mốc tổng hợp để một lần tinh chỉnh sau này không âm thầm làm tụt chất lượng.

### Ba lỗi bộ đánh giá tìm ra, đều là lỗi thật

Thứ nhất, cách cắt từ tên thiết bị khỏi câu hỏi đã cắt luôn những từ vừa là tên thiết bị vừa là triệu chứng. "ống nước bị bể" còn lại hai từ, không khớp bệnh nào, và một ca vỡ ống nước tới khách bằng sự im lặng. Thay bằng chấm theo độ hiếm của từ trong chính danh mục triệu chứng của thiết bị đó: từ nào xuất hiện ở hầu hết các bệnh thì tự mất trọng số, nên không cần danh sách từ phải xoá nữa.

Thứ hai, `symptoms_vi` và corpus đã trôi xa nhau. Corpus ghi sẵn từng bệnh khách gõ thế nào, nhưng retrieval lại khớp trên một danh sách bốn đến bảy mục sửa tay. Quét toàn bộ câu mà corpus gán cho bệnh HIGH thì một phần tư không tới được đúng bệnh. `tools/sync_symptoms.py` chép các mục đó sang, chỉ đụng `symptoms_vi` và không chạm giá, độ khẩn hay cờ duyệt: 621 lên 1.714 triệu chứng, và không còn câu nguy hiểm nào bị trả về rỗng.

Thứ ba, từ dừng bị lọc ở một bên mà không lọc ở bên kia. Câu toàn từ dừng thì giữ nguyên, còn danh mục triệu chứng thì bị lọc, nên hai bên không bao giờ gặp nhau. "không đi được" là cách một ca tắc bồn cầu tới thường xuyên nhất và cả ba từ đều nằm trong danh sách từ dừng.

### Chỗ còn hở, đã biết và chưa sửa

Câu "fixhome là làm gì vậy" trả về mục bảo hành thay vì mục tổng quan. Nguyên nhân: tiêu đề được nhân trọng số ba lần, nên một tiêu đề chỉ vì có chữ "FixHome" đã vượt mục trả lời đúng. Sửa chỗ này là đổi trọng số tiêu đề, mà trọng số ấy đang đỡ toàn bộ các con số vừa đạt 100%, nên để lại và ghi ra đây thay vì tinh chỉnh mò. Đây là câu hỏi dịch vụ, không phải nhánh an toàn.

Hai câu còn lại trong bộ quét bệnh HIGH rơi sang bệnh cùng thiết bị chứ không rỗng: "trần bị ố đen chỗ quạt" và "hai bếp đều yếu". Cả hai đều mơ hồ thật, và rơi sang bệnh hàng xóm thì khách vẫn được hỏi lại rồi quay về đúng bệnh ở lượt sau.

## Việc thứ tư: chốt phần giá

`labour_catalog.json` đã khớp đúng mục 8.3.1 của `SEP490- tổng.md` (18 dịch vụ, đã đối chiếu từng dòng). `parts_catalog.json` có 791 mã. Không có khoảng trống cần lấp.

Corpus **không chứa một con số tiền nào**, và có test cơ học chặn việc đó (`test_no_money_amounts_anywhere_in_the_corpus`). Nguyên tắc một nguồn giá đang được giữ.

`fault_pricing_map.json` đã đối chiếu: phủ đủ 108/108 mã bệnh, không có mã lạc theo chiều nào, mọi `labour` đều có trong danh mục công, mọi `parts` đều có trong danh mục linh kiện, và `labour_code` cùng `part_codes` trong `fault_knowledge_base.json` khớp từng dòng với bảng ánh xạ.

Hai chỗ cần anh quyết, vì là dữ liệu nghiệp vụ chứ không phải lỗi mã:

Thứ nhất, danh mục linh kiện không có bóng đèn và không có ổ cắm. Bảng công ghi rõ "tiền công", nên `LIGHT_BULB_DEAD` và `OUTLET_BROKEN_FACE` hiện chỉ báo được tiền công, không báo được tiền vật tư; hỏi "thay bóng đèn bao nhiêu" thì không có dòng giá nào trả về. Em không tự điền giá vào đây.

Thứ hai, một khối 100 mã thuộc nhóm "Đồ điện gia dụng" đang gắn cùng lúc cho năm loại thiết bị (quạt bàn, quạt trần, bình nóng lạnh, đèn, ổ cắm), và trong khối đó còn sót linh kiện bếp từ. Khi ghi chú này được viết, bếp từ chưa nằm trong danh mục nên không thể rò ra câu trả lời; **nay bếp từ là một trong 22 thiết bị**, nên lập luận đó không còn đúng và chỗ này cần dọn thật chứ không phải để khi rảnh.

Việc còn lại:

- Chốt cách AI nói về giá: nói dải, nói "giá cuối do kỹ thuật viên báo sau khi xem trực tiếp", và không bao giờ tự cộng trừ. Phần này đã viết trong `system/gia-va-cach-tinh-tien.md`, cần kiểm là prompt thực sự dùng nó.
- Kiểm quy tắc hoa hồng 10% chỉ trên công, không trên linh kiện, có bị AI hiểu nhầm thành giảm giá cho khách không.

## Việc thứ năm: chỗ cần thợ xác nhận

Mỗi file có mục "Chỗ cần thợ xác nhận", và frontmatter có trường `needs_technician_review`. Tổng cộng có khoảng 400 mục.

Đây là danh sách những gì đã cố ý **không** viết số cụ thể vì không chắc. Ví dụ: chu kỳ thay dây gas và van điều áp, áp làm việc của van theo loại bếp, trị số tụ theo model quạt, mức rò sóng cho phép của lò vi sóng.

Cần: một buổi ngồi với thợ thật để điền dần. Mỗi lần điền được một mục thì bỏ nó khỏi `needs_technician_review` và ghi ngày vào `last_reviewed`.

Việc này không chặn các việc trên. Nó chạy song song và chạy dài.

## Việc thứ sáu: thuê GPU và chạy thật

Theo cam kết ban đầu: **chưa thuê máy nào cho tới khi kho tri thức xong**. Giờ nó xong.

Khi thuê lại, dồn cả ba lên một máy: YOLO (detector ảnh), RAG (retrieval + embedding nếu dùng), và Qwen2.5-VL-3B AWQ qua vLLM. Trước khi thuê, nên đã có việc thứ nhất và việc thứ hai, để mỗi giờ GPU đều dùng vào việc đo chứ không vào việc dò.

## Việc thứ bảy: dọn nhánh

`feat/rag-knowledge-corpus` hiện có 22 commit, đã push. Khi retrieval đã nối xong và bộ đánh giá đã chạy được, mở PR và merge. Sau đó xoá nhánh và tách nhánh mới từ `main` vừa cập nhật.

## Ghi chú về môi trường

Trong phiên này, môi trường Python cục bộ lệch khỏi `requirements.txt`: `httpx` cài 0.28.1 (repo ghim `0.27.*`) và `fastapi` cài 0.109.0 (repo ghim `0.115.*`). Nó làm `TestClient` gãy và làm 2 file test không chạy được.

Đã chạy `pip install -r requirements.txt` để đưa về đúng pin, và toàn bộ test pass trở lại. Nếu máy khác gặp lỗi `Client.__init__() got an unexpected keyword argument 'app'` thì đó là nguyên nhân.

## Nguyên tắc đã giữ trong toàn bộ corpus

Bốn điều này được giữ trên cả 132 file, và nếu sau này có ai viết thêm thì nên giữ tiếp:

1. **Không có con số tiền nào.** Giá chỉ từ bảng giá của hệ thống. Có test chặn.
2. **Không sao chép nguyên văn từ nguồn nào.** Mọi tài liệu có mục "Nền tri thức của tài liệu này" ghi rõ nội dung dựa trên nguồn nào và phần nào là quan sát thực tế cần cập nhật.
3. **Chỗ nào không chắc thì ghi là cần thợ xác nhận**, không viết bừa. Đặc biệt với mã lỗi của hãng: chỉ ghi ba mã đã kiểm chứng; cụm tủ lạnh và máy giặt cố ý để trống bảng mã thay vì bịa.
4. **Chunk phải đứng một mình được.** Mỗi mục `##` đọc riêng vẫn hiểu, vì retrieval sẽ tách nó khỏi các mục bên cạnh. Có test chặn chunk quá ngắn và quá dài.
