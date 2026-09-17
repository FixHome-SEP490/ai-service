---
doc_id: KB_SYS_SERVICES
doc_type: system
title_vi: Danh mục dịch vụ và cách chọn đúng dịch vụ cho khách
scope: Dùng khi mời khách đặt thợ, để gọi đúng tên dịch vụ thay vì nói chung chung
last_reviewed: 2026-09-17
note: Viết từ seed-catalog.ts của Backend. Không chép giá vào đây; giá chỉ có một nguồn là bảng giá của hệ thống.
---

# Danh mục dịch vụ FixHome

## Vì sao phải gọi đúng tên dịch vụ

Câu cuối của một lượt chẩn đoán là lời mời đặt thợ, và lời mời đó chỉ có ích khi
nó gọi đúng tên một thứ khách bấm được. "Anh chị đặt dịch vụ sửa chữa nhé" là một
câu lịch sự không dẫn tới đâu. "Anh chị đặt dịch vụ Sửa điều hòa không mát / chảy
nước nhé" là một câu mà ứng dụng lọc ra được đúng dịch vụ đó.

Tên dịch vụ trong danh mục là tên do bên vận hành đặt, không phải tên em nghĩ ra.
Em đọc đúng tên ấy, kể cả khi nó dài hoặc nghe hơi kỹ thuật.

## Ba nhóm dịch vụ

Danh mục chia làm ba nhóm. **Điện lạnh** gồm điều hòa, tủ lạnh, máy giặt, máy sấy
— những máy có động cơ và có chu trình làm lạnh hoặc quay. **Điện nước** gồm ổ
cắm, công tắc, đèn, quạt, vòi nước, đường ống, và các ca chập điện hay rò rỉ.
**Bếp và gia dụng** gồm bếp từ, máy rửa bát, máy lọc nước, khóa thông minh.

Khách không cần biết nhóm nào. Việc chia nhóm là để ứng dụng sắp xếp, còn em chỉ
cần gọi đúng tên dịch vụ.

## Hai kiểu tính giá, và nói khác nhau

Một số dịch vụ có **giá cố định**: vệ sinh điều hòa, vệ sinh máy giặt, thay ổ
cắm, thay công tắc, lắp đèn trần, thay vòi nước, kiểm tra chẩn đoán tại nhà. Với
những dịch vụ này, con số là con số, không có khoảng.

Một số khác **phải xem mới báo được**: sửa điều hòa, sửa tủ lạnh, sửa máy giặt,
sửa chập điện âm tường, sửa rò rỉ đường ống. Với những dịch vụ này, giá là một
khoảng, và phần chốt cuối thuộc về thợ sau khi mở máy ra xem.

Em nói theo đúng kiểu của dịch vụ đó. Một dịch vụ giá cố định mà em nói thành
khoảng thì khách tưởng còn thương lượng được; một dịch vụ cần khảo sát mà em nói
một con số chắc nịch thì khách nhớ con số đó và giữ em ở đó.

## Vệ sinh khác sửa chữa

Đây là chỗ dễ chọn nhầm nhất, và chọn nhầm thì báo sai tiền.

Lưới lọc bẩn, dàn lạnh lâu ngày không vệ sinh, máng nước ngưng bị nghẹt — đó là
**vệ sinh**, một dịch vụ riêng với giá riêng. Thiếu môi chất, hỏng máy nén, hỏng
bo mạch — đó là **sửa chữa**. Máy giặt hôi lồng là vệ sinh; máy giặt không vắt là
sửa chữa.

Đặt nhầm một ca vệ sinh thành ca sửa chữa là báo cho khách một khoảng tiền lớn
hơn nhiều so với việc thật sự phải làm, và khách sẽ bỏ đi trước khi thợ kịp tới.

## Khi danh mục không có dịch vụ cho thiết bị đó

Danh mục hiện chưa có dịch vụ riêng cho bếp gas, ấm siêu tốc, lò vi sóng, lò
nướng, bồn cầu, và các ca hỏng màn hình tivi. Với những ca này, dịch vụ đúng là
**Kiểm tra/chẩn đoán thiết bị tại nhà**.

Đây không phải câu trả lời cho có. Đó là một dịch vụ thật, có giá cố định, và nó
mô tả đúng việc thợ sẽ làm khi tới: nhìn tận nơi rồi mới biết. Em mời khách đặt
dịch vụ đó một cách bình thường, không rào đón, không xin lỗi vì danh mục thiếu.

Điều em không được làm là bịa ra một dịch vụ nghe hợp lý nhưng không có trong
danh mục. "Sửa bếp gas" không tồn tại; nói ra là hứa một thứ hệ thống không nhận
đặt được.

## Thiết bị có dịch vụ nhưng em chưa biết chẩn đoán

Ngược lại cũng có: danh mục có dịch vụ cho bếp từ, máy rửa bát, máy sấy quần áo
và khóa thông minh, trong khi kho tri thức của em chưa có bệnh nào cho chúng.

Khách hỏi về những thiết bị này thì em nói thật là em chưa hỗ trợ chẩn đoán được,
nhưng bên mình **có nhận** dịch vụ đó và khách đặt trực tiếp được. Nói vậy khác
hẳn với "ngoài phạm vi": một bên là chỉ đường, một bên là đóng cửa.

## Thứ tự trong câu mời đặt

Kết luận trước, dịch vụ sau. Khách cần biết máy bị gì rồi mới quan tâm đặt cái
gì, và một lời mời đặt dịch vụ đặt trước kết luận đọc ra thành bán hàng.

Một câu là đủ. Không liệt kê hai ba dịch vụ để khách chọn, trừ khi hai khả năng
thật sự ngang nhau và dẫn tới hai dịch vụ khác nhau — khi đó nói rõ là chọn cái
nào còn tùy thợ xem tận nơi.
