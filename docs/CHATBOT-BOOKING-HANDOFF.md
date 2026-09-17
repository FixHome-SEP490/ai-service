# Từ câu trả lời của AI sang nút "Đặt thợ ngay"

PO chốt ngày 17/09/2026. Ghi lại nguyên ý để không trôi:

> Khi ta nhận được danh sách dịch vụ thì dạy cho RAG biết, và cho khách hàng biết
> nên book dịch vụ nào. Sau khi biết book dịch vụ nào rồi thì AI sẽ có một cái
> button kiểu "Đặt thợ ngay". Khi người dùng nhấn vào đó thì nó route qua trang
> booking và đặt cái filter sao cho ra đúng dịch vụ. Cái này triển khai hoàn toàn
> trên mobile app.

## Phần AI Service đã xong, cập nhật 17/09/2026

Không còn việc nào ở repo này chặn mobile nữa. Cụ thể những gì đã làm:

`app/data/service_mapping.json` đã được điền đủ. 134 bệnh, 72 bệnh có dịch vụ riêng
và 62 bệnh rơi về `KIEM_TRA_CHAN_DOAN_THIET_BI` đúng như PO chốt. File được sinh
bởi `tools/map_services.py` đọc thẳng `backend/src/database/seeds/seed-catalog.ts`,
nên tên dịch vụ khách nhìn thấy đúng là tên trong catalog chứ không phải tên
ai đó gõ lại. Backend đổi tên dịch vụ thì chạy lại tool, không sửa tay.

Mỗi dịch vụ mang theo `base_price` của Backend, nên con số AI nói khi mời đặt
lịch là con số catalog tính tiền, không phải sàn công thợ của bảng giá nội bộ.

`ChatResponse` đã có `recommendedServices`, giống `DiagnosisResponse`. Trước đây
chỉ mặt chẩn đoán có, mà nút "Đặt thợ ngay" lại sống trong khung chat.

**Mọi câu trả lời đều kèm một dịch vụ đặt được, kể cả câu hỏi lại.** Đây là chỗ
mobile cần đọc kỹ nhất. Quy tắc:

Biết thiết bị và các bệnh trong danh sách ngắn đều đặt chung một dịch vụ thì
trả đúng dịch vụ đó.

Các bệnh khác dịch vụ nhau, hoặc chưa biết thiết bị gì, thì trả
`KIEM_TRA_CHAN_DOAN_THIET_BI`. Đây không phải trả bừa: thợ sang xem tận nơi đúng
là việc đang được đề nghị.

Câu hỏi không về thiết bị hỏng — bảo hành bao lâu, quy trình đặt lịch — thì
`recommendedServices` rỗng. Không ai đặt thợ sau khi hỏi bảo hành, và dí nút vào
đó biến mọi câu trả lời thành lời chào hàng.

Khách nói thẳng là muốn đặt lịch thì AI không chẩn đoán nữa. "Bây giờ anh muốn
đặt lịch vệ sinh máy lạnh" trả về `status: ok`, `suspectedFaults` rỗng, một dịch vụ
trong `recommendedServices`, và `messageVi` mời khách bấm nút. Mobile gặp dạng này
thì đưa thẳng sang màn đặt lịch chứ đừng hiển thị như một kết luận bệnh.

`app/data/knowledge/system/danh-muc-dich-vu.md` mô tả danh mục bằng lời khách, nên
câu "giờ tôi nên thuê dịch vụ nào" được trả lời từ tài liệu chứ không phải từ
suy đoán của mô hình.

## Còn thiếu một thứ, và nó thuộc Backend

AI trả `serviceCode` chứ chưa trả `serviceId`. Mapping được sinh từ file seed, mà
file seed không chứa id — id sinh ra lúc chạy seed vào database. Hai cách để đóng:
Backend cho AI Service một endpoint trả bảng code → id, hoặc mobile lọc
`GET /services` theo `code`. Cách thứ hai không cần ai làm gì thêm và nên chọn
trước, cách thứ nhất sạch hơn nếu sau này danh mục to lên.

## Việc còn lại, chia theo repo

### Backend

Chốt và cấp danh sách dịch vụ: `serviceId`, `categoryId`, tên, `pricingMode`. Mục
8.3.1 của `SEP490- tổng.md` đã có 18 dịch vụ giá cố định và `GET /services` đã có
trong bảng API, cần xác nhận đây là danh sách cuối hay còn thêm.

Không cần endpoint mới. Mobile gọi `GET /services` sẵn có với tham số lọc.

### Mobile — phần lớn việc nằm ở đây

Bỏ mảng `ALL_SERVICES` viết cứng trong `CustomerServicesScreen`, chuyển sang gọi
`servicesApi.getServices()`. Đây là việc nên làm dù có chatbot hay không: hiện màn
dịch vụ đang hiển thị 8 nhóm không liên quan gì tới catalog thật của Backend.

Mở rộng `RootStackParamList` cho `CustomerServices` nhận thêm `serviceId` và
`categoryId`, không chỉ `query`. Lọc theo id thì chính xác; lọc theo chuỗi tên thì
hỏng ngay khi Admin sửa tên dịch vụ.

Thêm nút "Đặt thợ ngay" vào khung chat, hiện ra khi `recommendedServices` khác
rỗng. Nhấn thì `navigation.navigate('CustomerServices', { serviceId })`, hoặc đi
thẳng `CustomerServiceDetail` nếu chỉ có đúng một dịch vụ — đỡ cho khách một lần
chạm, và AI đã đủ chắc thì đừng bắt họ chọn lại.

Xử lý trường hợp AI không chắc: `recommendedServices` rỗng, hoặc `status` là
`low_confidence`. Lúc đó nút phải dẫn về danh sách dịch vụ chưa lọc chứ không lọc
sai, và không được biến mất — nguyên tắc "AI hỏng không được chặn luồng đặt lịch"
trong `CLAUDE.md` áp dụng cả ở đây.

## Có phải train lại không

Không. Không có mô hình nào đang được train trong hệ thống này.

Qwen2.5-VL-3B AWQ dùng nguyên bản, không fine-tune. Tri thức tới với nó qua prompt
ở thời điểm chạy, nên thêm dịch vụ chỉ là thêm dữ liệu cho retrieval đọc.

Retrieval là lexical: BM25 cộng chấm theo độ hiếm của từ, không có embedding và
không có index vector nào phải build lại. Thêm file vào `app/data/knowledge/` là
lần chạy sau đã thấy, vì `get_corpus()` đọc thẳng từ đĩa.

YOLO nhận diện thiết bị trong ảnh, không liên quan tới danh mục dịch vụ.

Nên chi phí thật của việc này là: điền một file JSON, thêm một trường vào schema,
viết vài file tri thức, và sửa màn hình dịch vụ bên mobile cho nó gọi API thật.

## Chỗ cần PO quyết trước khi làm

Một bệnh ánh xạ sang mấy dịch vụ? Nếu một bệnh có thể ra hai dịch vụ khác nhau tuỳ
mức độ, thì AI chọn hay để khách chọn.

Nút "Đặt thợ ngay" dẫn tới màn danh sách đã lọc, hay dẫn thẳng vào màn chi tiết
dịch vụ, hay dẫn thẳng vào form tạo Booking với dịch vụ đã điền sẵn.

Có cho khách sửa lựa chọn của AI trước khi đặt không. Nên có, nhưng đây là quyết
định sản phẩm chứ không phải kỹ thuật.
