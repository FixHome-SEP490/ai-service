# Từ câu trả lời của AI sang nút "Đặt thợ ngay"

PO chốt ngày 17/09/2026. Ghi lại nguyên ý để không trôi:

> Khi ta nhận được danh sách dịch vụ thì dạy cho RAG biết, và cho khách hàng biết
> nên book dịch vụ nào. Sau khi biết book dịch vụ nào rồi thì AI sẽ có một cái
> button kiểu "Đặt thợ ngay". Khi người dùng nhấn vào đó thì nó route qua trang
> booking và đặt cái filter sao cho ra đúng dịch vụ. Cái này triển khai hoàn toàn
> trên mobile app.

## Tin tốt: phần lớn đường ống đã dựng sẵn

Không phải làm lại từ đầu, và **không phải train lại gì cả**. Lý do ở mục cuối.

`app/data/service_mapping.json` đã tồn tại và đang **cố ý để trống**. Chú thích
trong file ghi đúng tình huống hôm nay: "De rong cho toi khi Backend chot catalog;
khi do chi can dien file nay, khong dung vao bang loi hay code." Đây chính là chỗ
"dạy cho RAG biết danh sách dịch vụ".

`DiagnosisResponse` đã có sẵn trường `recommended_services: List[RecommendedService]`
với `service_code` và `name_vi`, và `local_pipeline.py` đã điền nó: gọi
`services_for_fault()`, nếu chưa có ánh xạ thì lùi về mã công trong
`labour_catalog.json` để câu "giờ tôi nên thuê dịch vụ nào" không bị trả lời bằng
sự im lặng. Nghĩa là AI **đã** biết trả lời nên đặt dịch vụ nào, chỉ là đang trả về
mã nội bộ của AI Service chứ chưa phải `serviceId` của Backend.

Bên mobile, `CustomerServicesScreen` đã nhận `route.params?.query` và lọc theo nó.
Tức là cơ chế "route qua trang dịch vụ kèm bộ lọc" đã chạy được, chỉ là đang lọc
trên một mảng `ALL_SERVICES` viết cứng 8 nhóm trong chính file màn hình, chứ chưa
gọi `servicesApi.getServices({ categoryId, search })` — hàm này đã viết xong trong
`src/api/services.api.ts` nhưng chưa ai dùng.

## Việc cần làm, chia theo repo

### AI Service

Điền `service_mapping.json`: mỗi `fault_code` ánh xạ sang một hoặc nhiều
`service_code` của Backend. 108 bệnh, và nhiều bệnh chung một dịch vụ nên số dòng
thật sẽ ít hơn nhiều. Đây là dữ liệu, không đụng code.

Thêm `recommended_services` vào `ChatResponse`. Hiện `DiagnosisResponse` có,
`ChatResponse` không — mà nút "Đặt thợ ngay" sống trong khung chat. Đây là sửa
schema, không sửa logic: dữ liệu đã có sẵn trong pipeline.

Trả kèm `service_id` của Backend chứ không chỉ `service_code`. Mobile cần thứ đưa
thẳng vào bộ lọc được, không phải thứ phải đoán lại bằng cách so tên.

Viết thêm vài file tri thức nghiệp vụ trong `app/data/knowledge/system/` mô tả
danh mục dịch vụ bằng lời khách: dịch vụ nào bao gồm gì, khi nào chọn dịch vụ này
thay vì dịch vụ kia. Corpus hiện có 5 file nghiệp vụ, đây là file thứ 6 trở đi.

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
