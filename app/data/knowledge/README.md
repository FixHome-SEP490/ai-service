# Kho tri thức cho RAG

Đây là phần văn bản mà RAG đọc để dựng ngữ cảnh cho Qwen. Dữ liệu có cấu trúc
nằm ở `app/data/*.json` và trả lời được câu hỏi "bệnh nào, giá bao nhiêu". Thư
mục này trả lời phần còn lại: vì sao, phân biệt thế nào, khách nói câu đó nghĩa
là gì, khi nào thì chưa được kết luận.

Trước khi có thư mục này, toàn bộ vốn chữ của hệ thống là 22.764 ký tự. Đó là lý
do phần tư vấn nghe như tra bảng.

## Ba tầng

`devices/` — một file cho mỗi loại thiết bị. Cấu tạo, nguyên lý, các nhóm triệu
chứng gốc và cây phân nhánh, hãng phổ biến, mã lỗi, lắp đặt và nghiệm thu, bảo
dưỡng, tuổi thọ, an toàn, bối cảnh nhà ở Việt Nam, bảo hành, sửa hay thay.

`faults/` — một file cho mỗi mã bệnh. Cơ chế hỏng, nguyên nhân gốc, phân biệt
với từng bệnh gần giống, khách tự kiểm tra được gì, thợ làm gì, để lâu thì sao.

Tầng nghiệp vụ lấy từ `docs/SEP490- tổng.md`, chunk chứ không viết mới.

## Frontmatter

Mỗi file mở đầu bằng YAML. Các khoá bắt buộc:

    doc_id          định danh duy nhất, KB_FAULT_<mã> hoặc KB_DEVICE_<mã>
    doc_type        fault | device | policy
    device_type     khớp device_catalog.json
    fault_code      chỉ với doc_type: fault, khớp fault_knowledge_base.json
    last_reviewed   ngày rà lại gần nhất

Khoá nên có: `confusable_with` liệt kê mã bệnh dễ nhầm, `needs_technician_review`
liệt kê những chỗ cố ý không ghi số.

## Chunk theo tiêu đề

Mỗi `##` là một chunk. Viết mỗi mục sao cho đứng một mình vẫn đọc hiểu được, vì
nó sẽ bị tách ra khỏi phần còn lại khi đưa vào ngữ cảnh. Nhắc lại tên thiết bị
hoặc tên bệnh trong mục thay vì dùng "nó" trỏ ngược lên mục trước.

Cỡ mục dễ dùng là khoảng 700 tới 1.500 ký tự.

## Bốn luật viết

**Không ghi giá.** Bảng giá của hệ thống là nguồn giá duy nhất. Tài liệu chỉ
giải thích cái gì làm giá thay đổi. Một con số tiền viết ở đây sẽ mâu thuẫn với
bảng giá và Qwen sẽ đọc nhầm cái nào tùy lúc.

**Không sao chép nguyên văn.** Research để lấy sự thật kỹ thuật rồi viết lại
bằng giọng của dự án. Chép nguyên là rủi ro bản quyền cho đồ án.

**Không chắc thì ghi là cần thợ xác nhận.** Mỗi file có mục `Chỗ cần thợ xác
nhận` ở cuối. Một con số kỹ thuật sai ở đây sẽ được Qwen lặp lại với mọi khách.
Mã lỗi của hãng là chỗ nguy hiểm nhất: chỉ ghi mã đã đối chiếu được, không đoán.

**Ghi nguồn ở mục `Nền tri thức của tài liệu này`.** Để người sau biết phần nào
dựa trên đâu, và phân biệt được phần dựa trên tiêu chuẩn với phần dựa trên quan
sát thực tế.

## Viết cho khách thật, không cho khách lý tưởng

Phần lớn tin nhắn thật là câu cụt, không dấu, sai chính tả, gọi tên bộ phận theo
dân gian, hoặc đã kèm sẵn một kết luận sai của khách. Mỗi file bệnh phải có các
mục phủ những dạng đó, không chỉ mục triệu chứng viết bằng từ kỹ thuật.

Mục `Khi nào KHÔNG được kết luận` quan trọng ngang mục triệu chứng. Đoán bừa
khi đáng lẽ phải hỏi đắt hơn nhiều so với hỏi khi đáng lẽ trả lời được.

## Hai file mẫu

`faults/AC_LOW_REFRIGERANT.md` và `devices/air_conditioner.md` là mẫu đã được
duyệt về độ sâu, giọng văn và bố cục. File mới bám theo hai file đó.
