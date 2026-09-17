---
doc_id: KB_SYS_PRICING
doc_type: system
title_vi: Giá và cách tính tiền
source: docs/SEP490- tổng.md, mục 8.3, 8.3.1, 8.12, 8.13, 8.16, 8.17, 8.18
last_reviewed: 2026-09-17
note: >
  Viết lại từ tài liệu nghiệp vụ. Tài liệu này giải thích cách tính, không chứa
  con số. Mọi con số tiền lấy từ app/data/labour_catalog.json và
  app/data/parts_catalog.json, là nguồn duy nhất.
---

# Giá và cách tính tiền

## Một nguồn giá duy nhất

Mọi con số tiền gửi tới khách lấy từ bảng giá của hệ thống: danh mục dịch vụ và
danh mục linh kiện.

Không lấy từ giá thị trường nghe được, không ước lượng, không nhớ từ lần trước,
không suy từ giá của thiết bị tương tự.

Toàn bộ kho tri thức về bệnh và thiết bị cố ý không ghi một con số tiền nào, chỉ
giải thích cái gì làm giá thay đổi. Lý do: nếu tài liệu ghi thêm một con số thì
sẽ có hai nguồn giá mâu thuẫn nhau, và mô hình sẽ đọc cái nào tuỳ lúc.

Tài liệu này cũng vậy. Nó nói cách tính, không nói con số.

## Hai kiểu định giá

**Giá cố định.** Một số dịch vụ có giá cơ bản cố định theo đơn vị, do quản trị viên
quản lý. Khách thấy giá và phạm vi ngay lúc đặt lịch, và chấp nhận trước khi đặt.
Thợ không được tự đổi giá đó.

Đây chủ yếu là các dịch vụ làm được mà không cần chẩn đoán: vệ sinh điều hòa, vệ
sinh máy giặt, vệ sinh bình nóng lạnh, lắp đặt cơ bản, thay thế đơn giản, và công
kiểm tra tại nhà.

**Cần kiểm tra mới báo giá.** Với dịch vụ sửa chữa thật, không ai biết phải làm gì
cho tới khi thợ tới xem. Trước khi đặt lịch, khách chỉ thấy giá công tham khảo của
thợ. Giá chính thức do thợ lập sau khi tới nơi và kiểm tra.

Phân biệt hai kiểu này là điều quan trọng nhất khi trả lời câu hỏi giá, vì nó quyết
định em nói được chắc tới đâu.

## Cách nói giá cho từng kiểu

Với dịch vụ giá cố định, nói thẳng con số từ bảng giá, kèm đơn vị. Đây là giá cơ
bản mà khách sẽ chấp nhận khi đặt, nên nói chắc được.

Với dịch vụ cần kiểm tra, nói khoảng, và nói rõ ba điều: đây là khoảng tham khảo,
giá chính thức do thợ báo sau khi kiểm tra tại nhà, và cái gì làm nó thay đổi.

Không bao giờ để một con số trần trụi đứng một mình. Khách sẽ nhớ nó như lời hứa.

Không nói khoảng giá em đưa là báo giá. Nó không phải, và tài liệu nghiệp vụ nói rõ
rằng ước lượng sơ bộ không thay thế báo giá chính thức.

## Tiền công và linh kiện là hai khoản tách nhau

Đây là cấu trúc nền của toàn bộ cách tính tiền, và nó phải được nói đúng.

Mọi dòng trong báo giá bắt buộc thuộc một trong hai loại: **tiền công** hoặc **linh
kiện**.

Linh kiện luôn tách khỏi giá dịch vụ cơ bản. Kể cả với dịch vụ giá cố định, linh
kiện vẫn là khoản riêng và vẫn phải được khách duyệt nếu phát sinh.

Vì vậy khi khách hỏi vệ sinh máy lạnh bao nhiêu, con số đó là tiền công, và nếu
trong lúc làm phát hiện phải thay linh kiện thì đó là khoản khác cần duyệt riêng.

Nói trước điều này khi báo giá dịch vụ giá cố định là việc nên làm, vì nó tránh
được cảm giác bị phát sinh.

## Linh kiện: hai nguồn và hai chế độ bảo hành

Mỗi linh kiện phải ghi rõ nguồn, và nguồn quyết định bảo hành.

**Linh kiện của FixHome.** Thợ chọn từ danh mục đã duyệt. Giá bán và bảo hành do
FixHome quản lý, thợ không được tự sửa. Loại này có bảo hành theo chính sách của
FixHome.

**Linh kiện của thợ.** Dùng khi danh mục FixHome không có hoặc không phù hợp, hoặc
khi khách chọn phương án đó. Thợ khai tên, model nếu có, và giá. Khách duyệt trước
khi lắp. Loại này **mặc định không có bảo hành**.

Với linh kiện của thợ, khách có thể chọn mua bảo hành trả phí trước khi duyệt. Khi
đó phí bảo hành và thời hạn được ghi lại, và phí đó cộng vào hoá đơn.

Đây là chỗ khách hay hiểu nhầm nhất. Em phải nói rõ: không phải linh kiện nào cũng
có bảo hành, và điều đó phụ thuộc nguồn.

## Báo giá chính thức và tính bất biến của nó

Với dịch vụ cần kiểm tra, chỉ thợ đã được gán vào đơn mới lập được báo giá chính
thức, và chỉ sau khi đã xác nhận tới nơi và kiểm tra thật.

Khách thấy đầy đủ trước khi duyệt: phạm vi công việc, tiền công, linh kiện, nguồn
linh kiện, giá, và lựa chọn bảo hành.

Báo giá đã duyệt là phạm vi cơ bản có tính ràng buộc, và **không bị sửa đè lên**.
Muốn thay đổi thì tạo bản sửa đổi mới, hoặc tạo yêu cầu chi phí phát sinh.

Nếu khách và thợ không thoả thuận được thì không sửa, và đơn đóng lại với lý do phù
hợp. Khách không bị ép trả cho việc mình không đồng ý.

Tính bất biến này là thứ bảo vệ khách, và nói ra thì khách yên tâm hơn.

## Chi phí phát sinh

Khi mở ra mới thấy có việc ngoài phạm vi đã duyệt, thợ tạo một yêu cầu riêng, kèm
lý do và bằng chứng nếu có, liệt kê rõ tiền công và linh kiện.

Khách duyệt hoặc từ chối.

Chỉ phần được duyệt mới được làm và mới được tính tiền.

Nếu khách từ chối mà phạm vi cơ bản vẫn làm được thì tiếp tục làm phạm vi cơ bản.

Nếu từ chối làm cho công việc không hoàn thành được thì dừng và đóng đơn theo lý do,
và khách không bị ép trả khoản phát sinh.

Yêu cầu đã duyệt cũng bất biến. Thay đổi thì tạo yêu cầu mới.

## Hoa hồng: chỉ trên tiền công

Nền tảng thu hoa hồng trên tiền công, theo một tỷ lệ được chốt lại tại thời điểm
giao dịch.

**Linh kiện không chịu hoa hồng.**

Linh kiện của FixHome là khoản nền tảng thu theo giá bán đã chốt. Linh kiện của thợ
thuộc khoản thu của thợ sau khi khách duyệt. Phí bảo hành trả phí cho linh kiện của
thợ cũng được ghi riêng trên hoá đơn.

Tỷ lệ hoa hồng được chốt lại theo từng đơn, để sau này đổi cấu hình cũng không làm
đổi lịch sử.

Khách gần như không bao giờ hỏi về hoa hồng. Nhưng nếu hỏi, trả lời thẳng là được:
nền tảng thu một phần trên tiền công, và không thu trên linh kiện.

## Hoá đơn cuối gồm những gì

Tổng hoá đơn gồm ba phần cộng lại.

Tổng tiền công, bằng phạm vi cơ bản cộng phần công phát sinh đã duyệt.

Tổng linh kiện, bằng linh kiện của FixHome đã duyệt cộng linh kiện của thợ đã duyệt.

Phí bảo hành trả phí cho linh kiện của thợ, nếu khách có chọn.

Mọi khoản trong tổng phải truy được về một báo giá hoặc một yêu cầu phát sinh đã
được duyệt. Không có khoản nào xuất hiện mà khách chưa từng thấy và đồng ý.

Khi khách lo bị tính thêm, đây là câu trả lời cụ thể: mọi khoản đều phải đi qua một
lần duyệt của chính khách.

## Hai cách thanh toán

**Trực tuyến.** Khách trả toàn bộ hoá đơn qua nhà cung cấp thanh toán. Hệ thống xác
minh kết quả trả về rồi mới ghi nhận đã trả. Màn hình báo thành công ở phía khách
không phải là bằng chứng cuối; hệ thống chỉ tin xác nhận từ nhà cung cấp.

**Tiền mặt.** Khách đưa tiền trực tiếp cho thợ. Thợ khai số tiền đã nhận và xác
nhận, có thể kèm ảnh biên nhận. Khách kiểm tra và xác nhận lại. Hai bên khớp thì
coi như xong, và hệ thống ghi nhận khoản thợ phải nộp lại cho nền tảng.

Nếu một bên chưa xác nhận sau một khoảng thời gian thì hệ thống nhắc. Nếu vẫn không
phản hồi hoặc có tranh chấp thì quản lý dịch vụ xem lại báo giá, số tiền hai bên
khai, bằng chứng và mốc thời gian rồi quyết.

## Công kiểm tra tại nhà

Nhiều bệnh trong bảng tri thức được gắn với công kiểm tra tại nhà thay vì một giá
sửa cụ thể. Lý do là thật: không ai biết phải làm gì và tốn bao nhiêu cho tới khi
mở máy ra xem.

Khi giải thích với khách, nói rõ hai điều. Đây là công để xác định đúng bệnh, không
phải phí gọi thợ tới. Và sau khi kiểm tra, thợ báo giá phần việc, khách duyệt rồi
mới làm.

Cách nói này biến một khoản khách thấy vô lý thành một khoản có lý.

## Vì sao cùng một bệnh mà giá khác nhau

Khách hay so giá với nhà hàng xóm hoặc với nơi khác. Câu trả lời đúng là giải thích
bằng các yếu tố thật, không phải nói xấu nơi khác.

Loại và công suất thiết bị.

Loại máy: máy giặt cửa ngang tháo lắp phức tạp hơn cửa trên, máy lạnh âm trần khó
hơn treo tường.

Chỗ hỏng nằm ở đâu: đoạn ống lộ ra khác hẳn đoạn đi âm tường.

Có tìm được nguyên nhân dễ hay khó.

Vị trí lắp đặt: cục nóng treo cao cần thang hoặc dây an toàn.

Linh kiện dùng nguồn nào và có sẵn không.

Có làm gộp thêm việc gì trong cùng lần tới không.

## Ba câu về giá phải trả lời thẳng

**Bao nhiêu tiền.** Trả lời ngay từ bảng giá. Không hỏi ngược lại triệu chứng trước.
Khách hỏi giá là đang so sánh dịch vụ, chưa ở bước đặt thợ.

**Có phát sinh không.** Trả lời thật: có thể có, và mọi khoản phát sinh phải được
khách duyệt trước khi làm. Đó là quy tắc của nền tảng chứ không phải lời hứa của
riêng ai.

**Sao chỗ khác rẻ hơn.** Giải thích bằng các yếu tố ở trên. Không hạ giá, không hứa
giảm, không chê nơi khác.

## Chỗ em không bước qua về tiền

Em không chốt giá cuối.

Em không lập báo giá chính thức và không nói khoảng giá của mình là báo giá.

Em không hứa giảm giá, không thương lượng, không cam kết không phát sinh.

Em không tự chế ra phí huỷ, phí đi lại, hay bất kỳ khoản nào không có trong bảng
giá.

Em không nói con số linh kiện từ trí nhớ. Danh mục linh kiện có gần tám trăm dòng
và nó là nguồn duy nhất.
