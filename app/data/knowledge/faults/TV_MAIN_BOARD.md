---
doc_id: KB_FAULT_TV_MAIN_BOARD
doc_type: fault
device_type: television
fault_code: TV_MAIN_BOARD
name_vi: Hỏng bo xử lý tín hiệu
urgency: LOW
confusable_with: [TV_POWER_BOARD, TV_PANEL_DAMAGE, TV_NO_SOUND]
price_policy: Không ghi giá trong tài liệu này. Giá lấy từ bảng giá của hệ thống.
last_reviewed: 2026-09-17
needs_technician_review:
  - Bo xử lý thay thế có còn hàng cho model đó không
---

# Hỏng bo xử lý tín hiệu

## Bệnh khó chẩn đoán nhất cụm, và nên nói thật điều đó

Bo nguồn hỏng thì máy không lên: dễ nhận. Đèn nền hỏng thì có tiếng mà màn tối: dễ nhận,
và có phép thử đèn pin. Tấm nền hỏng thì nhìn thấy: dễ nhận.

Bo xử lý thì không có triệu chứng riêng nào cả. Nó làm quá nhiều việc, nên hỏng ở đâu
thì biểu hiện ra ở đó, và cái gì cũng có thể.

Nó có thể làm máy không lên hình, có thể làm mất tiếng, có thể làm hình vỡ, có thể làm
máy tự khởi động lại, có thể làm mất một cổng vào, có thể làm treo máy, có thể làm remote
không ăn.

Nghĩa là mã này thường là kết luận sau khi loại trừ, chứ không phải là chẩn đoán từ
triệu chứng.

Vì vậy cách trả lời đúng cho cụm này là nói thật: triệu chứng này có mấy nhánh, có nhánh
rẻ và có nhánh đắt hơn, và cần thợ đo mới tách được. Đừng đoán là bo xử lý qua tin nhắn,
vì xác suất sai cao và vì đoán sai theo hướng này đẩy khách về phía bỏ máy.

## Bo xử lý làm gì

Nó là phần "biết suy nghĩ" của cái tivi.

Nhận tín hiệu vào từ các cổng, từ đầu thu, từ ăng ten.

Giải mã tín hiệu đó thành khung hình và thành âm thanh.

Xử lý hình ảnh: đổi độ phân giải cho khớp tấm nền, chỉnh màu, chỉnh độ tương phản.

Đưa dữ liệu hình ảnh sang bo T-CON để hiển thị ra tấm nền.

Chạy phần mềm của máy: menu, danh sách kênh, cài đặt, và trên smart tv thì cả một hệ
điều hành với các ứng dụng và kết nối mạng.

Nhận lệnh từ mắt hồng ngoại và từ nút bấm trên thân.

Từ danh sách đó thấy ngay vì sao nó hỏng thì ra đủ kiểu: nó dính vào gần như mọi chức
năng của máy.

## Sáu nhóm triệu chứng có thể là bo này

**Nhóm một, hình vỡ thành ô, thành mảng màu lạ, hoặc nhiễu hạt khắp màn.** Nghiêng về
bo xử lý hoặc bo T-CON.

**Nhóm hai, máy tự khởi động lại, tự tắt rồi bật, hoặc treo đứng không phản hồi.** Trên
smart tv thì đây là nhóm phổ biến nhất, và phần lớn ca lại không phải hỏng phần cứng.

**Nhóm ba, mất một cổng vào trong khi các cổng khác vẫn dùng được.** Triệu chứng khá đặc
trưng và nó hẹp: mạch của đúng cổng đó.

**Nhóm bốn, có hình mà không có tiếng, hoặc ngược lại.** Giao với mã âm thanh.

**Nhóm năm, không dò được kênh, mất hết kênh, hoặc không bắt được tín hiệu.** Có thể là
bộ thu trên bo, nhưng cũng rất có thể là ăng ten hoặc đầu thu.

**Nhóm sáu, không kết nối được mạng, ứng dụng không chạy, menu lỗi.** Trên smart tv.
Phần lớn không phải phần cứng.

Ba trong sáu nhóm có nhánh phần mềm hoặc nhánh bên ngoài rẻ hơn nhiều, và những nhánh
đó phải được loại trừ trước.

## Loại trừ những thứ miễn phí trước, và có nhiều

Đây là phần có giá trị thực tế cao nhất của tài liệu này, vì với bo xử lý thì tỷ lệ ca
kết thúc ở một việc miễn phí là cao nhất trong cụm tivi.

**Rút điện tivi hẳn khỏi ổ, chờ vài phút, cắm lại.** Việc số một. Nó xử lý được phần lớn
nhóm treo máy và nhóm tự khởi động lại. Chờ đủ lâu là quan trọng, vài giây không đủ.

**Thử một nguồn tín hiệu khác.** Đổi cổng, rút cắm lại dây, thử thiết bị khác. Rất nhiều
ca "tivi hỏng" thực ra là đầu thu, là dây hdmi, hoặc là chính cái nội dung đang phát.

**Thử nội dung khác.** Một số nội dung có định dạng mà máy đời cũ xử lý không tốt, và nó
cho hình vỡ hoặc mất tiếng chỉ ở nội dung đó.

**Khởi động lại bộ định tuyến mạng**, với nhóm smart tv không vào được mạng.

**Cập nhật phần mềm máy**, nếu vào được menu. Có bản lỗi gây treo và hãng đã vá.

**Khôi phục cài đặt gốc.** Đây là bước cuối trong nhóm miễn phí và nó xử lý được nhiều
ca smart tv. Nhưng phải nói trước rằng nó xoá hết cài đặt, danh sách kênh, và tài khoản
đã đăng nhập, để khách quyết chứ không bất ngờ.

Sáu việc đó nên gợi ý theo thứ tự, và nên gợi ý trước khi nói bất cứ điều gì về bo mạch.

## Smart tv: phần lớn không phải hỏng phần cứng

Đáng tách riêng vì nó chiếm tỷ trọng lớn và vì cách xử lý hoàn toàn khác.

Một cái smart tv là một cái máy tính. Nó có bộ nhớ, có hệ điều hành, có ứng dụng, và nó
gặp đúng các vấn đề mà một cái máy tính gặp.

**Máy chạy chậm dần theo năm tháng.** Bộ nhớ đầy, ứng dụng tích tụ, phần mềm nặng dần
qua các bản cập nhật trong khi phần cứng thì không đổi. Đây không phải hỏng.

**Treo khi mở một ứng dụng nặng.**

**Ứng dụng không chạy nữa vì nhà cung cấp ngừng hỗ trợ đời máy cũ.** Không sửa được và
cũng không phải hỏng.

**Mất kết nối mạng.** Thường là bộ định tuyến hoặc sóng yếu chứ không phải máy.

Với nhóm này, lời khuyên đúng thường là: dọn bớt ứng dụng, khôi phục cài đặt gốc, hoặc
dùng một thiết bị phát rời cắm vào cổng hdmi thay vì dựa vào phần thông minh của máy.

Gợi ý cuối đáng nêu: một thiết bị phát rời rẻ hơn nhiều so với thay bo xử lý, và nó biến
một cái tivi đời cũ thành máy chạy mượt. Đây là lời khuyên thật sự có ích cho khách,
và nó không mang lại đơn hàng nào. Vẫn nên nói.

## Tách với các mã khác

**TV_POWER_BOARD.** Cặp khó tách nhất, ở dạng máy bật lên rồi tự tắt hoặc bật tắt lặp
lại. Cả hai cho triệu chứng đó và không tách được qua tin nhắn.

Điều có thể nói chắc với khách: cả hai đều sửa được, bo nguồn thì rẻ hơn, và cần đo mới
biết là cái nào. Nói vậy trung thực hơn là đoán.

**TV_PANEL_DAMAGE.** Câu hỏi tách rất tốt và khách tự làm được: **hiện tượng có đổi khi
chuyển kênh hoặc đổi cổng tín hiệu không**. Lỗi tấm nền thì cố định tại đúng một chỗ;
lỗi xử lý thì thường đổi theo nội dung.

Câu hỏi thứ hai: lỗi có xuất hiện cả trên menu của máy không. Menu do chính máy vẽ ra,
nên nếu menu hiện bình thường mà chỉ nội dung bị lỗi thì vấn đề nằm ở đường tín hiệu
hoặc ở nguồn phát, không phải ở tấm nền.

**TV_NO_SOUND.** Mất tiếng có thể là mạch âm thanh, cũng có thể là phần giải mã trên bo
xử lý. Tách bằng cách thử nhiều nguồn: mất tiếng ở mọi nguồn và mọi ứng dụng thì nghiêng
về bo.

## Vì sao bo xử lý hỏng

Ít hơn bo nguồn, vì nó được bo nguồn che chắn phần nào. Nhưng vẫn có mấy nguyên nhân rõ.

**Xung sét qua đường cáp truyền hình hoặc dây mạng.** Đây là đường vào thẳng tới bo xử
lý, không qua bo nguồn. Nếu tivi hỏng sau giông mà bo nguồn vẫn còn tốt thì nhánh này
rất đáng nghi.

**Điện áp bất thường từ bo nguồn.** Bo nguồn hỏng theo kiểu cấp sai mức thì nó kéo bo xử
lý đi theo. Đây là lý do khi sửa bo nguồn thì nên kiểm tra luôn bo xử lý.

**Nhiệt và ẩm.** Mối hàn oxy hoá, mối hàn dưới các chip lớn bị nứt vi mô sau nhiều chu
kỳ nóng nguội. Nhánh này cho triệu chứng rất đặc trưng: **máy chạy tốt lúc mới bật rồi
lỗi dần sau khi nóng lên**, hoặc ngược lại là lỗi lúc đầu rồi tự hết.

Nhánh mối hàn nứt đáng biết vì đôi khi nó sửa được bằng cách hàn lại chứ không cần thay
bo, và đó là mức rẻ hơn hẳn.

**Chuột cắn dây hoặc làm tổ sau lưng máy.** Nước tiểu chuột dẫn điện và ăn mòn bo.

## Khách nói thế nào

"tivi bị vỡ hình", "hình bị nhiễu hạt", "hình bị ô vuông", "màu sắc bị sai", "tivi tự
khởi động lại", "tivi cứ tắt rồi bật", "tivi bị đơ", "tivi treo không bấm được", "cổng
hdmi không nhận", "tivi không vào được mạng", "app không chạy", "tivi chậm rì", "mất
hết kênh", "tivi không dò được kênh".

Không dấu: tivi bi vo hinh, hinh bi nhieu hat, tivi tu khoi dong lai, tivi bi do, cong
hdmi khong nhan, tivi khong vao duoc mang, app khong chay, tivi cham ri.

Cách nói khác: "tivi bị loạn", "hình như bị nhiễu sóng", "tivi dở chứng", "tivi bị lag",
"nó cứ quay quay mãi không vào được".

Câu "tivi chậm rì" và "tivi bị lag" gần như luôn thuộc nhánh phần mềm chứ không phải
nhánh phần cứng, và trả lời đúng hướng đó tiết kiệm cho khách rất nhiều.

## Đọc ảnh

Ảnh màn hình đang lỗi, chụp thẳng trong phòng hơi tối. Ảnh cơ bản.

Ảnh hình vỡ thành ô vuông hoặc thành mảng màu. Nghiêng về bo xử lý hoặc bo T-CON.

Ảnh cùng một lỗi ở hai kênh hoặc hai cổng khác nhau. Rất có giá trị: nếu lỗi đổi theo
nguồn thì không phải phần cứng hiển thị.

Ảnh màn hình khi đang mở menu của máy. Có giá trị cao mà ít ai nghĩ tới: menu do chính
máy vẽ, nên menu hiện đẹp mà nội dung lỗi là một thông tin tách nhánh mạnh.

Ảnh thông báo lỗi trên màn, nếu có. Smart tv hay hiện mã lỗi hoặc dòng chữ, và nó có
ích thật.

Ảnh các cổng phía sau máy và dây đang cắm. Thấy được cắm đúng cổng chưa, dây có hỏng
không.

Ảnh tem model. Cần để trả lời câu bo thay thế có còn hàng không.

Ảnh sau lưng máy nếu nghi chuột. Phân chuột, dấu cắn, tổ.

## Sửa hay thay

Bo xử lý nằm ở khoảng giữa của phép tính, khác với bo nguồn là gần như luôn đáng và
tấm nền là thường không đáng.

**Với máy còn tương đối mới:** thường đáng sửa. Bo xử lý rẻ hơn tấm nền nhiều.

**Với máy đã nhiều năm:** cần cân nhắc, vì bo xử lý không rẻ bằng bo nguồn và giá máy
mới đã rơi.

Có ba mức xử lý, và nên nêu cả ba vì mức rẻ nhất khá phổ biến.

**Hàn lại mối tiếp xúc hoặc thay linh kiện nhỏ trên bo.** Mức rẻ nhất, và nó ăn với nhánh
mối hàn nứt do nhiệt.

**Thay bo xử lý.** Mức phổ biến. Nhưng có một điểm cần biết: bo xử lý thường gắn với
model, và với máy đời cũ thì có thể không còn hàng.

**Dùng thiết bị phát rời thay cho phần thông minh của máy.** Không sửa gì cả, nhưng nó
giải quyết được phần lớn nhóm smart tv chậm và treo, và nó rẻ hơn mọi phương án sửa.

Gợi ý thứ ba nên nêu chủ động khi triệu chứng thuộc nhóm phần mềm. Nó là lời khuyên
đúng cho khách kể cả khi nó không mang lại việc cho ai.

## Kịch bản mẫu

Khách nhắn "tivi bị vỡ hình thành ô vuông". Hỏi lỗi có đổi khi chuyển kênh không, và có
xuất hiện trên menu không. Gợi ý thử nguồn tín hiệu khác trước.

Khách nhắn "tivi tự khởi động lại liên tục". Gợi ý rút điện chờ vài phút rồi cắm lại
trước. Nếu không ăn thì nói thật là có thể bo nguồn hoặc bo xử lý và cần đo.

Khách nhắn "smart tv nhà em chậm rì, mở app lâu lắm". Nhánh phần mềm. Gợi ý dọn ứng
dụng, khôi phục cài đặt gốc, và nêu phương án thiết bị phát rời.

Khách nhắn "cổng hdmi số 2 không nhận". Hỏi các cổng khác có dùng được không, và thử
dây khác. Nếu chỉ một cổng chết thì nhánh hẹp và thợ xử lý được.

Khách nhắn "tivi không vào được mạng". Gợi ý khởi động lại bộ định tuyến và thử thiết bị
khác cùng mạng trước. Phần lớn ca không phải tivi.

Khách nhắn "tivi mới bật thì bình thường, xem một lúc thì hình lỗi". Nhánh mối hàn nứt
do nhiệt. Nói rõ nhánh này đôi khi sửa được bằng cách hàn lại, tức là mức rẻ.

Khách nhắn "giông xong tivi có hình mà hình bị loạn". Hỏi tivi có nối cáp truyền hình
không. Xung sét qua đường đó đi thẳng vào bo xử lý.

Khách nhắn "vậy là bo main hỏng phải không em". Đừng xác nhận. Nói rằng triệu chứng có
mấy nhánh, có nhánh miễn phí, và đề nghị thử các bước loại trừ trước.

## Nền tri thức của tài liệu này

Toàn bộ nội dung được viết lại bằng lời của dự án, không sao chép nguyên văn từ nguồn
nào.

Chức năng bo xử lý tín hiệu trong tivi, gồm giải mã, xử lý hình ảnh, chạy phần mềm và
điều khiển các cổng vào: nội dung mô đun điện tử dân dụng trong chương trình đào tạo
nghề, đối chiếu tài liệu kỹ thuật của các hãng tivi có mặt tại Việt Nam.

Hiện tượng nứt vi mô ở mối hàn dưới các chip lớn sau nhiều chu kỳ nóng nguội, và biểu
hiện lỗi xuất hiện hoặc biến mất khi máy nóng lên: kiến thức về mỏi nhiệt trong lắp ráp
điện tử.

Đường xung sét đi vào qua cáp truyền hình và dây mạng, không qua bo nguồn: kiến thức về
chống sét lan truyền.

Đặc điểm menu do chính máy vẽ ra, cơ sở của phép tách nhánh bằng cách xem menu có hiển
thị bình thường không: phương pháp chẩn đoán thông dụng trong nghề sửa chữa điện tử.

Tỷ trọng cao của nhánh phần mềm trong các ca smart tv chậm và treo, và phương án dùng
thiết bị phát rời: quan sát thực tế trong nước. Cần cập nhật khi hệ thống chạy thật.

## Chỗ cần thợ xác nhận

Bo xử lý thay thế có còn hàng cho model đó không.

Bệnh nằm ở bo xử lý hay bo nguồn, khi triệu chứng là bật tắt lặp lại. Cần đo.

Bo T-CON có phải nguyên nhân không, khi triệu chứng là hình vỡ.

Có sửa được bằng cách hàn lại mối tiếp xúc không, hay phải thay cả bo.

Bo nguồn có cấp đúng điện áp không, vì bo nguồn sai mức kéo theo bo xử lý.

Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
