# Còn gì phải làm để AI này dùng được thật

Thống kê ngày 17/09/2026, sau ba lượt chạy thật trên GPU thuê. Mỗi con số dưới đây đều đếm được từ repo, không ước chừng.

## Đã xong

Kho tri thức 132 file, 2.877 đoạn, phủ 108/108 bệnh và 17/17 thiết bị. Nối vào cả hai đường trả lời: chẩn đoán từ ảnh và hỏi đáp bằng chữ. Bảng giá phủ 108/108 mã bệnh, không mã lạc, khớp từng dòng giữa kho tri thức và bảng ánh xạ; sàn là tiền công, trần là tiền công cộng điểm giữa khoảng giá linh kiện. Bộ đánh giá 403 hội thoại, chạy ngoại tuyến không cần GPU. Trang chat web phục vụ ngay trên cổng của máy thuê. 1.312 test, ruff sạch, CI xanh.

## Chưa xong, xếp theo mức chặn đường

### Một — chưa ai đo trọn vẹn chất lượng trả lời

Bộ 403 ca **chưa chạy hết một lần nào với Qwen thật**. Lần gần nhất đứt ở ca 402 khi phiên làm việc đóng. Số liệu đầy đủ mới nhất là của bộ 143 ca cũ: 131/143, tức 92%, và trích dẫn tài liệu nghề đạt 100%.

Không có con số này thì mọi phát biểu về chất lượng đều là suy đoán. Đây là việc đầu tiên nên làm ở lượt thuê máy tiếp theo, mất khoảng 40 phút.

### Hai — 176 chỗ trong kho tri thức đang chờ thợ thật

125 file có khai báo `needs_technician_review`, tổng **176 mục**. Đây là những chỗ cố ý không viết số cụ thể vì không chắc: mốc áp suất theo từng loại môi chất, áp thử nitơ theo khuyến cáo hãng, trị số tụ theo model quạt, mức rò sóng cho phép của lò vi sóng.

Cần một buổi ngồi với thợ. Điền được mục nào thì bỏ mục đó khỏi khai báo và ghi ngày vào `last_reviewed`.

### Ba — 36 giá do AI ước lượng, chưa ai duyệt

Danh mục linh kiện không có bóng đèn và ổ cắm, nên AI service tự thêm 36 mã với giá thị trường ước lượng, mang cờ `price_estimated: true`. Đây là **chỗ duy nhất trong toàn hệ thống có số tiền không do team cấp**. Admin cần rà trước khi chạy thật với khách.

### Bốn — nút "Đặt thợ ngay" chưa nối được

`service_mapping.json` có **0 dòng**, đang chờ Backend chốt danh sách dịch vụ. Cho tới lúc đó, AI trả về mã dịch vụ nội bộ của chính nó chứ không phải `serviceId` mà mobile lọc được.

Khi có danh sách thì phần còn lại nhẹ: điền một file JSON, thêm `recommendedServices` vào `ChatResponse`, và bên mobile đổi màn dịch vụ từ mảng viết cứng sang gọi API. **Không phải train lại gì** — chi tiết trong `CHATBOT-BOOKING-HANDOFF.md`.

### Năm — Backend mới nối một nửa

`backend/src/modules/ai-diagnosis/ai-diagnosis.service.ts` gọi `/api/v1/diagnosis/analyze`. Nó **không gọi `/api/v1/chat/ask`**, tức toàn bộ bề mặt hỏi đáp — thứ mà khung chat dùng — chưa có đường vào hệ thống.

Mobile thì chưa gọi AI service dòng nào.

### Sáu — bộ nhận diện ảnh còn yếu ở vài thiết bị

Đo trên ảnh thật: 14/16 ảnh bếp gas nhận đúng (một nhầm thành lò vi sóng, một không nhận ra). Ảnh máy giặt trong mẫu thử không nhận ra được. Đây là giới hạn của bộ trọng số hiện tại, không phải lỗi mã.

Khi detector trượt, hệ thống hỏi lại thiết bị nào thay vì đoán — đúng hành vi mong muốn — nhưng mỗi lần trượt là một lần khách phải gõ thêm.

### Bảy — model chọn sai trong danh sách đã lọc

Ca cụ thể: ảnh tivi kèm "sọc màn hình". Model ghi vào ô lý do của chính nó *"hình nghiêng về tấm nền hỏng"* rồi chọn dải đèn nền. Nó hiểu đúng và điền sai ô.

Đã thu danh sách đưa cho model từ 5 bệnh xuống 3 để chặn việc với tay xuống hạng thấp. Ca này vẫn sai vì cả hai ứng viên đều nằm trong top 3. Muốn chữa tận gốc phải hoặc tin thứ hạng của retrieval hơn, hoặc dùng model mạnh hơn.

### Tám — bốn thiết bị phổ biến ngoài danh mục

Nồi cơm điện, bếp từ, máy hút mùi, máy sấy quần áo đều **không nằm trong 17 thiết bị**. Khách hỏi thì AI trả lời ngoài phạm vi, đúng với dữ liệu nhưng nghe như nó kém.

Hai hướng: mở rộng danh mục — mỗi thiết bị cần bệnh, giá, tài liệu tri thức — hoặc sửa câu từ chối cho thành thật, đại ý "thiết bị này bên em chưa nhận sửa".

### Chín — vận hành

Trang chat công khai, **không có đăng nhập**. Ai có link đều dùng được và mỗi câu đều tiêu GPU tính theo giờ. Chấp nhận được khi demo nội bộ, không chấp nhận được khi mở rộng.

Địa chỉ đổi mỗi lần thuê máy mới, nên Backend chưa thể giữ một địa chỉ cố định. Cần một tunnel có tên miền ổn định trước khi nối thật.

### Mười — hai ca nhỏ còn trượt

"Fixhome là làm gì vậy" trả về mục bảo hành thay vì mục tổng quan, do tiêu đề được nhân trọng số ba lần. Hai câu mơ hồ trong bộ sinh tự động vẫn ra sai bệnh: "đường ống nước nước không xuống" và "máy giặt lúc được lúc không". Cả ba đều là câu hỏi dịch vụ hoặc cách nói mơ hồ thật, không phải nhánh an toàn.

## Thứ tự em đề nghị

Chạy hết bộ 403 ca trước, vì mọi quyết định sau đó đều cần con số ấy. Rồi rà 36 giá ước lượng, vì đó là tiền thật đến tay khách. Rồi ngồi với thợ điền 176 mục. Bốn việc còn lại phụ thuộc Backend chốt danh sách dịch vụ và phụ thuộc quyết định của PO về phạm vi thiết bị.
