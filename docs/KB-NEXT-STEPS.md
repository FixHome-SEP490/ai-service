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

## Việc quan trọng nhất: kho tri thức chưa được nối vào retrieval

Đây là việc phải làm đầu tiên và không có việc nào thay thế được nó.

`app/services/pipeline/retriever.py` hiện chỉ tìm trên `fault_knowledge_base.json` (các trường `symptoms_vi`) và trên `policies`. **Nó không đọc một dòng nào trong `app/data/knowledge/`.**

Nghĩa là: hai triệu ký tự vừa viết đang nằm trên đĩa và không có đường nào tới câu trả lời của Qwen. Thứ duy nhất đang đọc chúng là `tools/chunk_kb.py` và bộ test.

### Cần làm

1. **Nạp corpus vào retriever.** `tools/chunk_kb.py` đã có `load_corpus()` trả về `List[Chunk]` với đủ `doc_type`, `device_type`, `fault_code`, `heading_vi`, `text`. Chuyển logic đó từ `tools/` sang `app/services/pipeline/`, vì `tools/` không nên là dependency của `app/` khi chạy production.

2. **Lọc trước khi tính điểm.** Frontmatter có `device_type` và `fault_code` chính là để làm việc này. Khi đã biết thiết bị (từ detector ảnh hoặc từ `device_hint.py`), chỉ tính điểm trên chunk của thiết bị đó cộng với `persona/` và `system/`. Bỏ qua bước này thì 2.380 chunk bệnh cạnh tranh nhau trên mọi câu hỏi và độ chính xác tụt.

3. **Giữ lexical trước, đừng nhảy sang embedding ngay.** Docstring của `retriever.py` đã nói đúng: lexical thì deterministic và CI nhanh. Đo baseline bằng lexical trên corpus mới trước, rồi mới quyết định có cần embedding không. Nếu chuyển sang embedding thì `_STOPWORDS` và phần fold dấu vẫn cần cho bước lọc.

4. **Quyết định ngân sách chunk cho prompt.** Trung vị 726 ký tự, lớn nhất 2.273. Cần chốt đưa bao nhiêu chunk vào context của Qwen2.5-VL-3B và theo thứ tự ưu tiên nào. Gợi ý thứ tự: persona trước (nó định giọng), rồi chunk bệnh khớp nhất, rồi chunk thiết bị, rồi system nếu câu hỏi chạm nghiệp vụ.

5. **Viết test cho retrieval.** Một bộ câu hỏi mẫu kèm chunk mong đợi. Nó là thứ duy nhất cho biết việc sửa retriever sau này có làm hỏng gì không.

## Việc thứ hai: bộ đánh giá chất lượng câu trả lời

Chưa có cách nào biết corpus này có làm câu trả lời tốt lên hay không.

- Dựng bộ khoảng 100–150 câu hỏi thật, viết theo đúng kiểu khách hàng viết: cụt, không dấu, sai chính tả, mô tả bằng cảm giác, tự chẩn đoán sai, chỉ gửi ảnh.
- Mỗi câu ghi rõ: mã bệnh đúng, chunk nào phải được lấy ra, và câu trả lời phải chứa điều gì / không được chứa điều gì.
- Đặc biệt kiểm bốn chỗ mà corpus đã viết là không được bịa: giá tiền, số liệu kỹ thuật, mã lỗi của hãng, và hư hỏng nhìn qua ảnh.
- Chạy bộ này trước và sau mỗi lần đổi retriever hoặc đổi prompt.

## Việc thứ ba: kiểm tra các nhánh an toàn thực sự chạy

Corpus có một nhóm quy tắc dạng "cảnh báo trước, chẩn đoán sau". Cần test riêng cho chúng, vì đây là chỗ sai thì không sửa lại được:

- Mùi gas → bốn việc (khoá van, mở thoáng, **không chạm công tắc nào**, không đánh lửa) phải đứng trước mọi câu hỏi.
- Vỡ ống nước → "khoá van tổng" là câu đầu tiên, không hỏi gì trước.
- Mùi khét / khói ở thiết bị điện → rút điện hoặc ngắt aptomat, kèm câu "tắt công tắc tường không đủ" ở các thiết bị đấu cứng (quạt trần, đèn, ổ cắm).
- Tê tay khi chạm thiết bị → ngắt aptomat **trước** khi rút phích.
- Lò vi sóng → không bao giờ gợi ý tự mở vỏ; không bao giờ gợi ý chạy lò rỗng để thử.
- Kính cửa lò nứt, kính lò vi sóng, ổ cắm vỡ mặt ở nhà có trẻ nhỏ → ngừng dùng, không có nhánh "dùng tạm".

Đề xuất: viết `tests/test_safety_first.py` bơm các câu này qua pipeline và assert rằng câu cảnh báo xuất hiện trước câu hỏi làm rõ.

## Việc thứ tư: chốt phần giá

`labour_catalog.json` đã khớp đúng mục 8.3.1 của `SEP490- tổng.md` (18 dịch vụ, đã đối chiếu từng dòng). `parts_catalog.json` có 791 mã. Không có khoảng trống cần lấp.

Corpus **không chứa một con số tiền nào**, và có test cơ học chặn việc đó (`test_no_money_amounts_anywhere_in_the_corpus`). Nguyên tắc một nguồn giá đang được giữ.

Việc còn lại:

- Kiểm tra `fault_pricing_map.json` phủ đủ 108 mã bệnh. Chưa đối chiếu.
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
