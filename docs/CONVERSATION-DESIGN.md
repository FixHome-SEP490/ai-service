# Thiết kế hội thoại và vai trò ba thành phần

Tài liệu này ghi lại kiến trúc mục tiêu do chủ dự án đặt ra. Nó mô tả thứ cần
đạt tới, không phải thứ đã có. Mục cuối liệt kê khoảng cách giữa hai bên.

## Vai trò từng thành phần

**YOLO** nhận diện loại thiết bị và khoanh vùng chính xác bộ phận cần nói tới,
rồi cắt vùng đó ra. Đầu ra của nó là hai thứ: thiết bị này là gì, và phần nào
trong ảnh đáng để nhìn kỹ.

**Qwen** nhận vùng ảnh YOLO đã cắt và nhìn vào tình trạng bề mặt: cũ kỹ, rỉ sét,
cháy xém, nứt vỡ, đọng nước. Đây là việc YOLO không làm được vì YOLO chỉ trả lời
"vật này là gì", không trả lời "vật này đang thế nào".

**RAG** tra bảng tri thức, lấy ra các khả năng hư hỏng cùng triệu chứng kèm
theo, và đưa phần kiến thức đó vào cho Qwen làm nguyên liệu suy luận. Qwen không
tự nhớ bệnh của máy lạnh Việt Nam; RAG là chỗ cung cấp.

**RAG cũng là nơi làm việc trực tiếp với khách hàng.** Đây là điểm quan trọng
nhất của thiết kế này. Khách nói chuyện với RAG, không nói chuyện với Qwen. RAG
là tầng đối thoại, Qwen là tầng suy luận nằm sau.

## YOLO cắt ở mức nào

Câu "cắt chính xác bộ phận cần nói tới" có hai cách hiểu, và chúng dẫn tới hai
bộ dữ liệu khác hẳn nhau.

**Mức thiết bị** là cắt cả cái máy lạnh, cả cái ổ cắm. Đây là thứ đang làm: 16
lớp, nhãn có sẵn từ Open Images và Roboflow, ảnh chụp bình thường là gán nhãn
được.

**Mức bộ phận** là cắt riêng máy nén, riêng dàn lạnh, riêng mặt ổ cắm, riêng
chân phích. Muốn vậy phải định nghĩa lớp mới cho từng bộ phận, và **không nguồn
công khai nào có nhãn đó** — phải tự vẽ khung cho từng bộ phận trên từng ảnh.

Hiện tại đi theo mức thiết bị, và để Qwen lo phần nhìn chi tiết bên trong vùng
đã cắt. Lý do: Qwen nhìn được "chỗ này rỉ sét", "chỗ này cháy đen" mà không cần
ai vẽ khung dạy nó, còn YOLO thì cần. Chia việc như vậy thì phần đắt nhất là gán
nhãn được giữ ở mức rẻ nhất.

Nếu sau này muốn lên mức bộ phận thì đó là một vòng thu thập và gán nhãn mới,
không phải chỉnh tham số.

## Vòng làm việc

1. Khách mô tả sự cố, có thể kèm ảnh hoặc chưa.
2. YOLO xác định thiết bị và cắt vùng cần xem, nếu có ảnh.
3. Qwen đọc vùng ảnh đó, ghi nhận tình trạng bề mặt.
4. RAG tra bảng lỗi theo thiết bị và mô tả, dựng danh sách khả năng kèm triệu
   chứng, đưa vào context cho Qwen.
5. Trong lúc Qwen suy luận, RAG **đồng thời** hỏi thêm khách. Câu hỏi lấy từ
   chính kiến thức sẵn có, nhắm vào chỗ đang chưa phân biệt được.
6. Khách trả lời, RAG nhồi câu trả lời đó vào context và đưa lại cho Qwen.
7. Qwen suy tiếp, trả kết luận cho RAG.
8. RAG diễn đạt lại cho khách.

Vòng 5 tới 7 lặp cho tới khi đủ chắc chắn, hoặc tới lúc phải nhường cho kỹ thuật
viên.

## Chatbot phải hỏi ngược trong lúc chờ

Đây là yêu cầu riêng và không nằm trong luồng chẩn đoán. Khách không được để
ngồi im chờ. Trong lúc hệ thống làm việc, bot vẫn phải giữ nhịp hội thoại: gợi ý
các bước kiểm tra đơn giản, xác nhận đã nhận thông tin, và xin ảnh đúng lúc.

Ví dụ hội thoại mẫu do chủ dự án đưa ra:

> **Khách:** Màn hình của tôi bị như thế này
> **Bot:** Anh/chị thử kiểm tra nút nguồn bên dưới xem đã bật chưa
> **Khách:** Bật rồi nhưng mà nó cứ chớp chớp
> **Bot:** Vậy anh/chị thử kiểm tra cổng kết nối hoặc ổ cắm giúp em nhé
> **Khách:** Kiểm tra rồi cắm kỹ lắm nhưng vẫn chớp, có khi tắt luôn
> **Bot:** Dạ em nhận tình trạng của anh/chị, vui lòng đợi em kiểm tra hệ thống
> **Bot:** Anh/chị vui lòng cho em xem mặt sau màn hình được không ạ
> **Khách:** *(gửi ảnh)*
> **Bot:** Dạ em nhận tình trạng của anh/chị, vui lòng đợi em kiểm tra hệ thống

Ba hành vi rút ra từ ví dụ này.

**Kiểm tra dễ trước, chẩn đoán sau.** Hai lượt đầu không phải chẩn đoán mà là
loại trừ những nguyên nhân tầm thường: nút nguồn, cổng cắm. Phải loại xong mới
đáng gọi thợ. Những bước này không phải bệnh trong bảng lỗi, chúng là bước sàng
lọc đứng trước.

**Xác nhận đã nhận, không im lặng.** Câu "em nhận tình trạng của anh/chị, vui
lòng đợi em kiểm tra hệ thống" không mang thông tin nào nhưng giữ khách lại. Một
khoảng lặng vài giây trong chat đọc như hệ thống chết.

**Xin ảnh đúng lúc.** Không hỏi ảnh ngay câu đầu. Chỉ hỏi khi mô tả đã thu hẹp
tới mức cần nhìn tận mắt, và hỏi rõ cần nhìn phần nào: "mặt sau màn hình" chứ
không phải "gửi ảnh".

## Câu xác nhận: nói ngay, đừng im

Khách nhắn xong mà màn hình trống trong sáu giây thì họ hiểu là không có ai ở
đó. Với người vừa mô tả cái tủ lạnh hỏng lúc mười giờ đêm, im lặng đọc ra thành
bị phớt lờ. Nên phải nói một câu ngay, trước khi pipeline chạy xong.

Một câu cố định thì không đủ. Lặp lại ở mọi lượt, nó thôi là phép lịch sự và trở
thành tiếng máy: khách nhắn ba lần, nghe đúng một câu ba lần, là học được rằng
không ai đọc cả.

Vì vậy câu xác nhận được chia theo tình huống và bốc không lặp trong một phiên.
Danh sách nằm ở `app/data/acknowledgements.json`, logic ở
`app/services/pipeline/acknowledgement.py`.

**Chín nhóm tình huống.** Lần đầu bằng chữ. Lần đầu có ảnh. Lượt tiếp theo trong
cùng cuộc trò chuyện. Khách hỏi giá. Khách hỏi kiến thức chung. Trước khi hỏi
ngược lại khách. Khi phải chờ lâu hơn bình thường. Khi khách đang bực. Khi khách
nói gấp.

Chia nhóm không phải để cho đẹp. Câu hỏi giá không đáng nhận "em kiểm tra",
nó đáng nhận "để em tra bảng giá". Tin nhắn thứ tư không phải lời chào đầu tiên.
Và khách đang bực thì phải được ghi nhận cái bực trước đã, vì trả lời gọn gàng
vào câu hỏi giá của họ đọc ra thành không để ý gì tới chuyện họ đang khó chịu.

**Nhóm thứ mười không phải câu xã giao.** Khi tin nhắn có dấu hiệu điện đang
chập, gas đang rò, hoặc nước đang chảy tới ổ điện, thì lời khuyên an toàn thay
thế hoàn toàn câu lịch sự. Lý do đơn giản: khách đọc dòng đầu tiên trong lúc
thiết bị vẫn đang cắm điện. Đây là chỗ duy nhất trong thiết kế hội thoại mà thứ
tự sai gây hậu quả thật, nên nó được khoá bằng test.

Dấu hiệu được so khớp trên chữ đã bỏ dấu, vì khách gõ không dấu suốt và đây là
chỗ cuối cùng mà việc thiếu dấu được phép đổi câu trả lời.

**Client bốc câu, không hỏi server.** Câu phải hiện ra đúng lúc bấm gửi, nên một
vòng gọi API để xin câu thì phá mất chính thứ nó dùng để làm.
`GET /api/v1/chat/acknowledgements` trả về nguyên bộ để mobile tải một lần rồi
cache, và tự bốc tại chỗ.

**Hết danh sách thì quay vòng, không rơi về một câu cố định.** Đi vòng thứ hai
ít lộ hơn nhiều so với nói đúng một câu mãi mãi.

## Khoảng cách so với hiện tại

Ghi trung thực để không nhầm giữa thứ đã chạy và thứ còn phải làm.

**RAG chưa phải tầng đối thoại.** Hiện `LocalPipeline` mới là nơi điều phối, còn
RAG chỉ là một bước truy xuất bên trong. Hai endpoint `/diagnosis/analyze` và
`/chat/ask` tách rời nhau, không có đường nối.

**Chưa có trạng thái hội thoại.** Mỗi request độc lập hoàn toàn. Hệ thống trả về
câu hỏi làm rõ nhưng không có chỗ nhận câu trả lời rồi đi tiếp. Muốn có vòng lặp
ở mục 5 tới 7 thì phải có định danh phiên và bộ nhớ lượt.

**Qwen và RAG chạy tuần tự, chưa song song.** Hiện RAG chạy xong mới tới Qwen.
Ý tưởng hỏi khách trong lúc Qwen đang suy luận cần hai luồng, và cần API trả
nhiều lượt thay vì một response duy nhất.

**Chưa có bước sàng lọc trước chẩn đoán.** Bảng lỗi chứa bệnh, không chứa các
bước kiểm tra tầm thường như nút nguồn hay cổng cắm. Cần một lớp riêng cho
những thứ đó.

**Chưa có lượt xác nhận.** API trả một response rồi hết. Không có khái niệm
"đang xử lý, chờ chút".

**Qwen đang nhận context quá mỏng.** Hiện chỉ gửi danh sách mã bệnh trần, không
kèm tên và triệu chứng, nên Qwen chọn gần như mù. Đây là việc sửa được ngay và
không phụ thuộc gì.

## Thứ tự nên làm

Nhồi context đầy đủ cho Qwen trước, vì nó rẻ và ảnh hưởng ngay tới chất lượng.
Sau đó tới trạng thái hội thoại, vì mọi thứ còn lại đều dựng trên đó. Lớp sàng
lọc và lượt xác nhận làm sau cùng, chúng là phần trình bày chứ không phải phần
suy luận.
