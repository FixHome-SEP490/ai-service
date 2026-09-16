---
doc_id: KB_FAULT_AC_PCB_FAULT
doc_type: fault
fault_code: AC_PCB_FAULT
device_type: air_conditioner
name_vi: Lỗi bo mạch điều khiển
urgency: MEDIUM
labour_code: DIAGNOSE_ONSITE
part_codes: [AC009]
confusable_with:
  - AC_REMOTE_FAULT
  - AC_CAPACITOR
  - AC_COMPRESSOR_FAULT
  - AC_INDOOR_FAN_MOTOR
  - AC_SMELL_BURNT
price_policy: Không ghi giá trong tài liệu này. Giá lấy từ bảng giá của hệ thống.
last_reviewed: 2026-09-16
needs_technician_review:
  - Mã lỗi của các hãng ngoài danh sách đã đối chiếu
  - Khi nào sửa bo còn hợp lý so với thay bo
---

# Lỗi bo mạch điều khiển

## Nói ngắn gọn cho khách

Máy lạnh có bo mạch điều khiển, thường một bo trong cục lạnh và trên máy inverter
thì thêm một bo công suất trong cục nóng. Bo là phần quyết định máy chạy hay
dừng, chạy ở chế độ nào, quạt quay tốc độ nào, và đọc tín hiệu từ các cảm biến.

Khi bo có vấn đề, biểu hiện thường lộn xộn chứ không gọn gàng: máy tự tắt, không
nhận điều khiển, nháy đèn báo lỗi, tự đổi chế độ, chạy được một lúc rồi dừng
không theo quy luật, hoặc không lên nguồn hẳn.

Đặc điểm nhận dạng quan trọng nhất của nhóm bệnh này là tính thất thường. Bệnh cơ
khí và bệnh môi chất thì ổn định và đều: hôm nào cũng vậy, càng nóng càng rõ.
Bệnh bo thì lúc được lúc không.

## Trước khi nghĩ tới bo, phải loại trừ hai thứ rẻ hơn

Rất nhiều ca được báo là hỏng bo thật ra là hai thứ nhẹ hơn nhiều, và loại trừ
chúng mất vài phút.

Thứ nhất là điều khiển từ xa. Hết pin, pin yếu, mắt phát hỏng, nút liệt. Biểu
hiện giống hệt máy không nhận lệnh. Cách tách: thử nút nguồn cơ trên thân cục
lạnh nếu máy có. Máy chạy bằng nút cơ thì lỗi nằm ở remote, không phải bo.

Thứ hai là nguồn điện. Aptomat nhảy, ổ cắm mất điện, dây tuột. Biểu hiện giống
máy không lên nguồn.

Chỉ khi hai thứ này đã được loại trừ thì mới nói tới bo. Nói ngược lại là làm
khách chuẩn bị tinh thần cho một khoản lớn trong khi vấn đề là hộp pin.

## Khách mô tả đầy đủ thì trông thế nào

Máy lạnh bấm remote không ăn, mà thay pin mới rồi vẫn vậy, bấm nút trên máy thì
nó chạy. Máy đang chạy tự nhiên tắt, một lúc lại tự bật. Đèn trên cục lạnh nháy
liên tục theo nhịp. Màn hình hiện mã lỗi. Bật lên chạy được ba phút rồi dừng và
nháy đèn. Máy tự đổi chế độ từ làm lạnh sang quạt. Đặt hai mươi lăm độ mà nó thổi
gió nóng.

Điểm chung: hành vi không đúng với lệnh, và không lặp lại theo một quy luật rõ
ràng.

## Khách mô tả cụt

Máy lạnh không nhận remote. Máy lạnh tự tắt. Máy lạnh nháy đèn. Máy lạnh báo lỗi.
Máy lạnh bật không lên. Máy lạnh hư bo. Máy lạnh bị lỗi. Máy lạnh chập chờn.

Nhóm này cần ít nhất một câu hỏi, vì nó trải trên bo, remote, nguồn, cảm biến, và
cả mô tơ quạt trên máy đời mới.

Câu hỏi đầu tiên nên là: bấm nút nguồn trên thân máy có chạy không, và đã thay
pin remote chưa.

## Khách gõ không dấu, gõ tắt

may lanh khong nhan remote, khong bam duoc, may lanh tu tat, may lanh nhay den,
may lanh bao loi, may lanh hien ma loi, may lanh bat khong len, may lanh hu bo,
bo mach may lanh hong, may lanh chap chon, den nhay 5 lan.

Biến thể chính tả: remote và rờ mốt và rimot và rìmốt, bo và bo mạch và board và
bảng mạch, nháy và nhấp nháy và chớp.

Cách nói chuyện: em ơi máy lạnh nhà chị bấm không ăn, ê máy lạnh nó nháy đèn hoài
là bị gì, máy lạnh tự tắt tự bật loạn xạ luôn.

## Khách gọi tên bộ phận theo dân gian

Bo mạch: bo, bo mạch, board, bảng mạch, cái mạch điện, main, mạch điều khiển, cái
vi mạch.

Trên máy inverter, bo trong cục nóng hay được gọi là bo công suất, bo cục nóng,
bo inverter, hoặc gộp chung là bo.

Khách hay nói "cháy bo" để chỉ mọi lỗi điện tử, kể cả khi không có gì cháy. Nên
hiểu là khách đang nói lỗi điện tử nói chung.

Cảm biến: sen sơ, cảm biến, con sen, que cảm biến, đầu dò.

Mắt nhận tín hiệu: mắt thần, mắt nhận, cái mắt, đầu thu.

## Khách mô tả bằng biểu hiện đèn và mã

Đèn nháy là ngôn ngữ chính của bệnh này trên máy phổ thông không có màn hình.

Nháy theo nhịp đều, đếm được số lần rồi nghỉ rồi lặp: đây là mã lỗi dạng nháy. Số
lần nháy và đèn nào nháy đều có nghĩa. Khách đếm được là thông tin quý.

Nháy liên tục không theo nhịp: thường là báo lỗi chung hoặc mất tín hiệu giữa hai
cục.

Tất cả đèn cùng chớp rồi tắt khi bật: có thể là nguồn yếu hoặc bo lỗi.

Đèn nguồn sáng bình thường nhưng máy không phản ứng: nguồn có, lệnh không tới.

Không đèn nào sáng: mất nguồn hoặc cầu chì trên bo đứt.

Trên máy có màn hình thì mã hiện thẳng, và khách đọc được. Nhưng phải biết hãng
mới dịch được mã.

## Mã lỗi, và giới hạn bắt buộc

Mã lỗi đã đối chiếu được, dùng trực tiếp:

Daikin báo U0 là cảnh báo liên quan tới thiếu môi chất. Nguyên nhân hay gặp gồm
thiếu hoặc hết gas thật, cảm biến áp suất hỏng, lỗi bo cục nóng, và trường hợp
lắp xong quên mở van hoặc rắc co hở.

Casper báo E3 là cảm biến nhiệt độ dàn lạnh, E4 là tín hiệu điều khiển mô tơ quạt
dàn lạnh.

Nagakawa báo E3 là cảm biến nhiệt độ dàn nóng, hay gặp do chuột cắn đứt dây, rắc
cắm tuột hoặc cảm biến hỏng. F7 và F8 cũng thuộc nhóm cảm biến.

Ba nguyên tắc bắt buộc, và đây là chỗ nguy hiểm nhất của cả kho tri thức.

Mã lỗi khác nhau giữa các hãng và khác cả giữa các dòng của cùng một hãng. Không
được đoán mã. Một bảng mã bịa ra trông rất đáng tin và sẽ được lặp lại với mọi
khách.

Khi khách đưa mã không nằm trong danh sách đã đối chiếu, hỏi hãng và đời máy, nói
rõ rằng mã này cần tra theo đúng model, rồi chuyển sang hỏi triệu chứng thực tế.
Triệu chứng thì luôn đọc được, còn mã thì không phải lúc nào cũng tra được.

Mã lỗi cho biết máy tự thấy cái gì bất thường, không cho biết nguyên nhân gốc.
Một mã báo lỗi cảm biến có thể do cảm biến hỏng, do rắc cắm tuột, do dây bị chuột
cắn, hoặc do chính bo đọc sai. Bốn nguyên nhân với bốn mức chi phí.

## Khách tự chẩn đoán rồi nói kết luận

Máy lạnh cháy bo rồi, thay bao nhiêu. Thợ nói hư board, báo giá cao quá nên hỏi
chỗ khác. Chắc hỏng mạch.

Nhóm này hay đến từ một chẩn đoán trước, và khách đang so giá. Đây là tình huống
cần xử lý tử tế: không phủ định thợ trước, không xác nhận thay họ.

Việc nên làm: hỏi máy đã được kiểm tra những gì, có thay pin remote chưa, có đọc
được mã lỗi không, và biểu hiện cụ thể là gì. Rất nhiều ca được gọi là hỏng bo
thật ra là cảm biến tuột rắc, là remote, hoặc là mô tơ quạt.

Cũng đáng hỏi máy dùng bao nhiêu năm và có phải máy inverter không, vì chi phí bo
công suất của máy inverter cao hơn đáng kể và điều đó ảnh hưởng tới cuộc nói
chuyện sửa hay thay.

## Khách hỏi giá trước

Thay bo máy lạnh bao nhiêu. Sửa board điều hòa giá nhiêu.

Trả lời giá từ bảng giá của hệ thống. Nhưng bệnh này cần thêm hai câu.

Câu thứ nhất: chi phí chênh nhau rất nhiều tùy bo nào và tùy sửa được hay phải
thay. Bo cục lạnh của máy thường khác hẳn bo công suất của máy inverter.

Câu thứ hai, quan trọng hơn: nhiều ca có biểu hiện giống lỗi bo lại là cảm biến,
là rắc cắm tuột, hoặc là remote, và những thứ đó rẻ hơn nhiều. Nên thợ cần kiểm
tra trước khi chốt.

Nói trước hai điều này tránh được cảnh khách chuẩn bị tinh thần cho một khoản lớn
rồi lại thấy hóa đơn khác hẳn, theo chiều nào cũng gây khó chịu.

## Khách chỉ gửi ảnh

Ảnh màn hình cục lạnh đang hiện mã lỗi. Có giá trị cao nếu biết hãng. Nếu mã nằm
trong danh sách đã đối chiếu thì dùng; nếu không thì hỏi hãng và model, và nói rõ
là cần tra chứ không đoán.

Ảnh đèn trên cục lạnh đang nháy. Ảnh tĩnh không đếm được số nháy, nên phải hỏi
khách đếm giúp. Video thì hữu ích hơn ảnh.

Ảnh bo mạch có vết cháy đen, linh kiện phồng, hoặc tụ trên bo nở đầu. Bằng chứng
trực tiếp, và nếu có dấu cháy thì kèm cảnh báo an toàn.

Ảnh bo có vết ẩm, vết nước, hoặc vết ố. Nước vào bo là nguyên nhân thật, và
thường truy ngược về máng nước lệch hoặc ống thoát nghẹt.

Ảnh có xác côn trùng, gián, thạch sùng trên bo. Nguyên nhân rất thật ở Việt Nam.

Ảnh remote đang hiện chữ hoặc mất chữ. Đây có thể là nhánh remote chứ không phải
bo.

Ảnh cục lạnh bình thường. Không kết luận được.

Nhắc quan trọng: nếu khách đã mở vỏ để chụp bo, nhắc ngắt aptomat trước và không
chạm vào linh kiện.

## Cây hỏi, khi chỉ được hỏi tối đa hai câu

Câu hỏi giá trị cao nhất: bấm nút nguồn trên thân cục lạnh thì máy có chạy không,
và đã thay pin remote mới chưa.

Bấm nút cơ thì chạy: lỗi nằm ở remote hoặc ở mắt nhận, không phải bo điều khiển
chính. Nhánh rẻ.

Bấm nút cơ cũng không chạy, không đèn nào sáng: hướng về mất nguồn hoặc cầu chì
trên bo.

Bấm nút cơ cũng không chạy nhưng đèn vẫn sáng: hướng về bo.

Câu hỏi giá trị cao thứ hai: đèn có nháy theo nhịp đếm được không, hoặc màn hình
có hiện mã gì không, và máy hãng nào.

Có mã và biết hãng: tra nếu mã nằm trong danh sách đã đối chiếu.

Có nháy nhưng không đọc được mã: vẫn là thông tin hữu ích cho thợ, bảo khách đếm
số nháy và ghi lại.

Không mã, chỉ thất thường: hỏi thêm về tính quy luật, vì bệnh bo thì lúc được lúc
không.

## Khi nào KHÔNG được kết luận lỗi bo

Không kết luận khi chưa thay pin remote và chưa thử nút nguồn trên thân máy.

Không kết luận khi aptomat đang nhảy hoặc ổ cắm mất điện. Đó là nhánh nguồn.

Không kết luận khi triệu chứng là cục nóng ù rồi tắt, không nhảy aptomat. Đó
nghiêng về tụ.

Không kết luận khi máy chạy hoàn toàn bình thường mà chỉ kém lạnh dần. Đó là
nhánh môi chất hoặc nhánh bẩn.

Không kết luận khi máy không inverter ngắt cục nóng theo chu kỳ trong lúc phòng
vẫn mát. Đó là hoạt động bình thường, và khách quen máy đời cũ đôi khi tưởng là
lỗi.

Không kết luận khi máy inverter chạy liên tục không ngắt hẳn. Cũng là bình thường.

Không kết luận khi máy tắt đúng giờ hẹn, hoặc đổi nhiệt độ theo chế độ ngủ đêm.
Đây là ca rất hay bị hiểu nhầm là máy tự tắt và tự đổi chế độ.

Không kết luận từ một mã lỗi không tra được. Mã chưa biết nghĩa thì không phải
bằng chứng.

Không kết luận khi có mùi khét. Chuyển sang nhánh an toàn trước.

## Chuyện gì đang xảy ra bên trong máy

Bo trong cục lạnh nhận nguồn, nhận lệnh từ mắt hồng ngoại hoặc từ nút cơ, đọc các
cảm biến nhiệt độ, điều khiển mô tơ quạt và cánh đảo gió, và gửi tín hiệu ra cục
nóng qua dây nối giữa hai cục.

Trên máy không inverter, cục nóng chỉ nhận lệnh đóng cắt đơn giản, nên phần điện
tử ngoài đó ít.

Trên máy inverter, cục nóng có bo công suất biến đổi tần số cấp cho máy nén. Đây
là phần phức tạp nhất và nhạy cảm nhất với điện áp bất thường, và cũng là phần
đắt nhất trong nhóm điện tử.

Từ cấu trúc đó ra mấy kiểu biểu hiện.

Mất tín hiệu giữa hai cục: máy trong nhà vẫn chạy quạt nhưng cục nóng không nhận
lệnh, nên không lạnh. Nguyên nhân có thể là dây nối giữa hai cục, rắc cắm, hoặc
bo ở một trong hai đầu.

Cảm biến đọc sai: máy hiểu sai nhiệt độ phòng hoặc nhiệt độ dàn, nên ngắt sớm,
chạy quá lâu, hoặc đóng tuyết. Đây là nhóm rất hay bị quy cho bo trong khi lỗi
nằm ở cái cảm biến rẻ tiền hoặc ở cái rắc cắm.

Linh kiện nguồn trên bo suy giảm: máy chập chờn, có lúc lên có lúc không, và
thường tệ hơn khi điện lưới yếu.

Vi điều khiển treo: máy không phản ứng cho tới khi ngắt điện rồi cấp lại.

## Nguyên nhân, theo thứ tự thường gặp

Rắc cắm tuột hoặc tiếp xúc kém. Nguyên nhân rẻ nhất và rất phổ biến, nhất là ngay
sau một lần vệ sinh hoặc sau khi tháo lắp máy.

Cảm biến nhiệt độ hỏng hoặc tuột. Cũng rẻ, và cho ra biểu hiện rất giống lỗi bo.

Ẩm và nước. Nước ngưng chảy vào bo do máng lệch hoặc ống thoát nghẹt, hoặc ẩm
trong khoang cục nóng sau mưa. Đây là mối liên hệ giữa một bệnh nhẹ với một bệnh
nặng và rất đáng biết: một cái ống thoát nghẹt không xử lý có thể kết thúc bằng
một cái bo cháy.

Côn trùng và thạch sùng chui vào bo gây chập. Nguyên nhân rất thật ở Việt Nam,
nhất là với bo trong cục nóng ngoài trời.

Điện áp không ổn định. Tụt áp và vọt áp ở khu dân cư đông vào giờ cao điểm mùa
nắng làm hỏng linh kiện nguồn trên bo.

Sét lan truyền qua đường điện. Thường đánh thủng linh kiện nguồn, và hay xảy ra
cả cụm nhiều thiết bị trong nhà cùng lúc.

Tuổi. Tụ trên bo khô dần và chân hàn oxy hóa theo thời gian. Đây là kiểu hỏng tự
nhiên của máy đã dùng nhiều năm.

Chuột cắn dây tín hiệu giữa hai cục.

Bo kém chất lượng từ đầu, hoặc bo đã từng được sửa chữa không đúng cách.

## Phân biệt với hỏng điều khiển từ xa

Đây là cặp phải tách đầu tiên và tách rất dễ.

Remote hỏng: bấm remote không ăn, nhưng bấm nút nguồn trên thân cục lạnh thì máy
chạy bình thường và chạy đúng.

Bo hỏng: bấm nút cơ cũng không ăn, hoặc máy chạy nhưng hành vi sai.

Ngoài ra có nhánh trung gian: mắt nhận tín hiệu trên cục lạnh hỏng. Lúc đó remote
tốt, bo tốt, nhưng lệnh không tới. Dấu hiệu: phải đứng rất sát mới bấm được, hoặc
chỉ ăn ở một góc nhất định. Nhánh này thuộc phần cục lạnh nhưng là linh kiện nhỏ
chứ không phải cả bo.

Luôn hỏi về nút nguồn cơ và về pin trước khi nói tới bo.

## Phân biệt với hỏng tụ điện

Tụ hỏng: cục nóng ù rồi tắt, trong nhà mọi thứ vẫn bình thường, đèn sáng, remote
ăn, gió ra.

Bo hỏng: thường có biểu hiện trong nhà, như đèn nháy, không nhận lệnh, tự tắt.

Điểm phân biệt gọn nhất: tụ hỏng thì phần trong nhà hoàn toàn bình thường.

Trên máy inverter thì ranh giới mờ, vì không có tụ đề và mọi chuyện điều khiển
máy nén đều đi qua bo công suất. Với máy inverter, cục nóng không chạy phải được
truy về bo công suất hoặc máy nén.

## Phân biệt với hỏng máy nén

Máy nén hỏng: có tiếng ù nặng, tiếng gõ, hoặc nhảy aptomat. Cục nóng cố khởi động
nên vẫn có tiếng.

Bo hỏng không cấp điện ra cục nóng: cục nóng hoàn toàn im, không tiếng gì.

Câu hỏi tách: cục nóng hoàn toàn im hay có tiếng ù rồi tắt.

Trên máy inverter thì bo công suất hỏng và máy nén hỏng cho triệu chứng giống hệt
nhau, và phải đo mới tách được. Điểm an ủi cho khách: bo công suất thường vẫn rẻ
hơn máy nén.

## Phân biệt với hỏng mô tơ quạt dàn lạnh

Trên máy đời mới, mô tơ quạt báo ngược tốc độ về bo. Khi quạt không đạt tốc độ,
bo cho máy dừng kèm mã lỗi. Nên một ca hỏng mô tơ quạt xuất hiện dưới dạng máy
chạy vài phút rồi tự tắt và báo lỗi, trông y hệt lỗi bo.

Dấu hiệu nghiêng về mô tơ: gió rất yếu hoặc không có gió trước khi máy tắt, hoặc
có tiếng rít, tiếng ù trong cục lạnh.

Dấu hiệu nghiêng về bo: gió bình thường, nhưng máy vẫn tắt và báo lỗi.

Đây là cặp mà mã lỗi một mình không tách được, và thợ phải đo tín hiệu.

## Phân biệt với mùi khét

Lỗi bo không mùi thì là bệnh này.

Lỗi bo có mùi khét thì đã có linh kiện cháy, và chuyển sang nhánh an toàn: ngắt
aptomat, không bật lại, không tự mở máy.

Hai bệnh này gối nhau, vì ca mùi khét thường kết thúc bằng việc thay bo. Nhưng
cách tiếp cận ban đầu khác hẳn.

## Phân biệt với chuyện máy không hỏng gì cả

Nhóm này chiếm nhiều hơn người ta tưởng, và loại trừ nó là miễn phí cho khách.

Máy tắt đúng giờ vì đang bật hẹn giờ. Khách quên là đã đặt, hoặc trẻ con bấm
nhầm.

Máy tự nâng nhiệt độ trong đêm vì đang ở chế độ ngủ đêm. Khách thấy sáng ra phòng
nóng và nghĩ máy hỏng.

Máy không inverter ngắt cục nóng theo chu kỳ khi phòng đã đạt nhiệt độ. Bình
thường.

Máy inverter không bao giờ ngắt hẳn. Cũng bình thường, và khách quen máy đời cũ
hay tưởng là lỗi.

Máy có chu kỳ chống đóng băng hoặc chu kỳ khởi động chậm sau khi cấp điện lại.
Bình thường.

Máy đang ở chế độ quạt hoặc chế độ khô nên không lạnh. Rất hay gặp khi trẻ con
nghịch remote.

Một câu hỏi về chế độ và về hẹn giờ loại được gần hết nhóm này.

## Bối cảnh thời gian

Ngay sau một lần vệ sinh: nghĩ tới rắc cắm chưa cắm chặt, cảm biến tuột, hoặc
nước vào bo. Đây là nguyên nhân phổ biến nhất trong nhóm và thường xử lý nhanh.
Nếu bên vệ sinh là cùng dịch vụ thì thuộc bảo hành công việc đã làm.

Ngay sau khi lắp mới hoặc di dời: đấu dây tín hiệu sai, rắc cắm lỏng.

Sau một đợt mưa bão: nước vào cục nóng, ẩm trong khoang.

Sau sét hoặc sau sự cố điện lưới: linh kiện nguồn bị đánh thủng. Dấu hiệu củng
cố: các thiết bị điện khác trong nhà cũng có vấn đề cùng lúc.

Sau một đợt mất điện rồi có điện lại: có khi chỉ là vi điều khiển treo, và ngắt
điện vài phút rồi cấp lại là hết. Đáng thử trước khi gọi thợ.

Vào giờ cao điểm mùa nắng, máy chập chờn rồi bình thường lại vào đêm khuya: gợi ý
điện áp khu vực chứ không phải bo hỏng hẳn.

Máy để lâu không dùng rồi bật lại: côn trùng đã làm tổ trong khoang, và ẩm đã
đọng.

Máy trên bảy tám năm: tụ trên bo khô và chân hàn oxy hóa là chuyện tự nhiên.

## Bối cảnh nơi lắp

Nhà ở khu điện yếu, hay tụt áp giờ cao điểm. Đây là nguyên nhân nền phổ biến
nhất, và nếu không xử lý thì bo mới cũng chết. Nên nói với khách về ổn áp.

Khu hay có sét. Cân nhắc thiết bị chống sét lan truyền.

Cục nóng ngoài trời có vỏ đã han gỉ hở, hoặc nắp khoang điện không kín. Nước và
côn trùng vào được.

Cục nóng ở tầng trệt gần đất, gần bụi rậm, gần cây. Chuột và côn trùng.

Phòng ẩm, hoặc cục lạnh lắp ở chỗ mà ống thoát nước hay nghẹt. Nước ngưng vào bo.

Nhà trọ và phòng cho thuê. Điện đấu nối tạm bợ qua nhiều đời, rủi ro cao hơn.

Máy nội địa xách tay chạy qua biến áp. Bo cho loại này gần như phải tìm hàng tháo
máy, và đây là ca mà sửa thường không khả thi.

## Khách tự kiểm tra được gì mà vẫn an toàn

Thay pin remote bằng pin mới. Việc đầu tiên và rẻ nhất.

Thử nút nguồn cơ trên thân cục lạnh nếu máy có. Đây là phép thử tách nhánh quan
trọng nhất.

Kiểm tra remote đang ở chế độ nào, nhiệt độ đặt bao nhiêu, có bật hẹn giờ hay chế
độ ngủ đêm không. Loại trừ nhóm máy không hỏng gì cả.

Kiểm tra aptomat cấp cho máy còn bật không, và ổ cắm có điện không.

Thử ngắt aptomat cấp cho máy khoảng năm tới mười phút rồi bật lại. Một số ca vi
điều khiển treo được giải quyết ở đây. Việc này an toàn và nên thử trước khi gọi
thợ.

Đếm số lần đèn nháy và ghi lại, hoặc chụp màn hình đang hiện mã. Thông tin này
rất giá trị cho thợ.

Ghi lại biểu hiện: xảy ra lúc nào, có quy luật không, có liên quan tới giờ trong
ngày không.

## Việc khách không nên tự làm

Không mở vỏ máy để xem bo. Tụ trên bo và tụ trong cục nóng có thể còn tích điện.

Không tự cắm lại rắc hay tự đấu dây.

Không xịt chất tẩy rửa hay dung dịch nào lên bo.

Không sấy bo bằng máy sấy tóc khi nghi bị ẩm.

Không tự mua bo trên mạng về thay. Bo phải đúng model và đúng đời, và lắp sai có
thể hỏng thêm.

Không đóng lại aptomat lặp lại nếu nó đang nhảy.

Không tiếp tục dùng nếu có mùi khét.

## Thợ tới thì làm gì

Loại trừ nhánh rẻ trước: pin remote, nút nguồn cơ, chế độ đang đặt, hẹn giờ,
nguồn điện, aptomat.

Đọc mã lỗi theo tài liệu của đúng model, không đoán.

Ngắt điện, mở vỏ, xả điện tụ trước khi chạm vào.

Quan sát bo: vết cháy, linh kiện phồng, tụ nở đầu, vết ẩm, vết ố, chân hàn oxy
hóa, xác côn trùng.

Kiểm tra toàn bộ rắc cắm và đầu dây. Rất nhiều ca kết thúc ở bước này.

Đo các cảm biến nhiệt độ và so với giá trị hợp lý theo nhiệt độ thực tế. Cảm biến
sai là nguyên nhân hay bị quy nhầm cho bo.

Kiểm tra dây tín hiệu giữa hai cục, đo thông mạch, tìm chỗ chuột cắn.

Đo điện áp nguồn tại chỗ, cả lúc máy khởi động. Nếu điện áp tụt sâu thì nguyên
nhân nền nằm ngoài máy.

Kiểm tra đường nước ngưng có chảy vào bo không.

Với máy inverter, kiểm tra bo công suất riêng, vì nó là phần hay hỏng và đắt.

Quyết định sửa bo hay thay bo. Sửa được khi hỏng khu trú ở vài linh kiện và thợ
có khả năng. Thay khi hỏng lan, khi bo đã ố ẩm nhiều chỗ, hoặc khi sửa không bảo
đảm được độ bền.

Xử lý nguyên nhân nền trước khi lắp bo mới: bịt khe hở chống côn trùng, xử lý
đường nước, tư vấn ổn áp. Bỏ bước này thì bo mới cũng chết.

## Sửa bo hay thay bo

Đây là câu hỏi thật của khách và nên trả lời thẳng.

Sửa bo thường rẻ hơn thay, và với hỏng khu trú ở một vài linh kiện thì hợp lý.
Nhưng nó phụ thuộc tay nghề thợ và không phải lúc nào cũng bảo đảm được độ bền,
nhất là với bo đã bị ẩm lan nhiều chỗ.

Thay bo chắc chắn hơn nhưng đắt hơn, và với máy đời cũ thì có khi không còn bo
chính hãng, phải dùng bo thay thế đa năng. Bo đa năng chạy được nhưng có thể mất
một số tính năng, và cần nói rõ với khách trước.

Với máy inverter, bo công suất thường phải thay chứ khó sửa, và đây là hạng mục
đắt.

Với máy đã trên mười năm, cộng với bo công suất hỏng, bài toán thường nghiêng về
thay máy. Nên nói cả hai phương án và để khách quyết.

Câu nên hỏi thợ: nếu sửa thì bảo hành bao lâu. Câu trả lời cho biết thợ tự tin
tới đâu.

## Để lâu thì hỏng gì

Bệnh này ở mức trung bình và thường không lan nhanh, nhưng có mấy hướng xấu đi.

Nếu nguyên nhân là ẩm hoặc nước, thì để lâu là ăn mòn lan rộng trên bo, và từ một
ca sửa được thành một ca phải thay.

Nếu nguyên nhân là chập do côn trùng, thì để lâu có thể thành ca cháy, và lúc đó
chuyển sang nhánh an toàn.

Nếu cảm biến đọc sai làm máy đóng tuyết hoặc chạy quá tải, thì hậu quả rơi sang
máy nén.

Nếu máy chập chờn và khách cứ đóng cắt lặp lại, thì mỗi lần khởi động là một lần
dòng vọt qua các linh kiện đã yếu.

Trong lúc chờ, nếu máy vẫn chạy được phần nào thì dùng tạm được, trừ khi có mùi
khét, có nhảy aptomat, hoặc máy đang đóng tuyết.

## Khi nào ca này thành gấp

Nâng ưu tiên khi có mùi khét hoặc khói. Chuyển sang nhánh an toàn.

Nâng ưu tiên khi nhảy aptomat.

Nâng ưu tiên khi máy tự bật khi không ai bấm. Máy tự chạy khi không có người là
tình huống không nên để kéo dài.

Nâng ưu tiên khi máy đang đóng tuyết vì cảm biến sai.

Nếu chỉ là không nhận remote hoặc thỉnh thoảng tự tắt mà máy vẫn dùng được, hẹn
lịch bình thường.

## Cái gì làm chi phí thay đổi

Tài liệu này không ghi con số. Giá gửi cho khách lấy từ bảng giá của hệ thống.

Nguyên nhân thật là gì. Rắc cắm tuột, cảm biến hỏng, và bo cháy là ba mức rất
khác nhau.

Bo nào. Bo cục lạnh của máy thường rẻ hơn bo công suất của máy inverter đáng kể.

Sửa hay thay.

Bo chính hãng hay bo thay thế đa năng.

Hãng và độ sẵn có. Máy nội địa xách tay gần như phải tìm hàng tháo máy.

Có phải xử lý nguyên nhân nền không: chống côn trùng, xử lý đường nước, ổn áp.

Vì phạm vi chỉ biết được sau khi mở ra và đo, bệnh này gắn với công kiểm tra tại
nhà trước, rồi báo giá phần việc sau.

## Nghiệm thu sau khi sửa

Máy nhận lệnh từ remote ở khoảng cách bình thường và ở nhiều góc.

Máy chạy đúng chế độ được đặt, và nhiệt độ hiển thị hợp lý với cảm nhận thực tế.

Không tự tắt, không tự đổi chế độ trong suốt thời gian chạy thử.

Không còn đèn nháy báo lỗi.

Máy chạy được ít nhất một chu kỳ đầy đủ.

Hỏi thợ nguyên nhân là gì. Câu trả lời phải cụ thể: rắc cắm, cảm biến, linh kiện
nào trên bo, hay cả bo.

Hỏi thợ đã tìm ra nguyên nhân nền chưa: nước, côn trùng, hay điện áp. Nếu không
ai chỉ ra được vì sao bo cũ hỏng thì rủi ro lặp lại là thật.

Hỏi bảo hành của bo mới hoặc của công sửa, ghi lại.

Theo dõi trong vài tuần, và chú ý những ngày điện yếu vì đó là lúc bệnh hay tái.

## Giữ cho bệnh không tái

Lắp ổn áp nếu khu vực hay tụt áp. Đây là biện pháp phòng ngừa quan trọng nhất
trong nhóm này.

Cân nhắc thiết bị chống sét lan truyền nếu khu vực hay có sét.

Đảm bảo máy có aptomat riêng đúng dòng.

Xử lý ngay đường nước ngưng khi thấy nghẹt hoặc chảy sai chỗ, vì nước vào bo là
nguyên nhân thật.

Bịt các khe hở ở vỏ cục nóng để chuột và côn trùng không vào khoang.

Yêu cầu thợ kiểm tra các rắc cắm trong mỗi lần bảo dưỡng.

Không ngắt cấp điện đột ngột khi máy đang chạy, và không đóng cắt liên tục.

Với máy để lâu không dùng, bật chạy một lúc mỗi vài tuần để tránh ẩm đọng.

## Kịch bản hội thoại mẫu

Khách nói máy lạnh không nhận remote. Trước hết gợi ý hai việc miễn phí: thay pin
mới, và thử nút nguồn trên thân máy. Nói rõ vì sao: nếu nút cơ chạy được thì lỗi
nằm ở remote chứ không phải bo, và chi phí khác hẳn.

Khách nói thay pin rồi, bấm nút trên máy cũng không chạy. Lúc này mới nói tới bo
và tới nguồn. Hỏi đèn có sáng không.

Khách nói máy nháy đèn báo lỗi. Hỏi đếm được bao nhiêu lần nháy và máy hãng gì.
Nếu mã tra được thì dùng; nếu không thì nói thẳng là cần tra theo model và chuyển
sang hỏi triệu chứng thực tế.

Khách đưa một mã lỗi không có trong danh sách. Không đoán. Nói rằng mã khác nhau
giữa các hãng và giữa các dòng, hỏi hãng và model, và hỏi luôn biểu hiện thực tế
để có cái mà chẩn đoán.

Khách nói máy tự tắt ban đêm. Trước hết hỏi có bật hẹn giờ hoặc chế độ ngủ đêm
không. Rất nhiều ca dừng ở đây.

Khách nói thợ báo hỏng bo, giá cao. Không phủ định thợ trước. Hỏi đã kiểm tra
những gì, đã thử pin và nút cơ chưa, có đọc được mã không. Nói rằng nhiều ca
giống lỗi bo lại là cảm biến hoặc rắc cắm.

Khách nói vừa vệ sinh xong thì máy báo lỗi. Nói rằng đây là nhóm sự cố sau vệ
sinh, thường là rắc cắm chưa chặt hoặc cảm biến tuột, và nếu cùng dịch vụ làm thì
thuộc bảo hành công việc.

Khách nói vừa có sét, giờ máy không lên. Gợi ý kiểm tra các thiết bị khác trong
nhà, vì nếu nhiều thiết bị cùng hỏng thì đó là sét lan truyền và nên tính tới
thiết bị chống sét.

Khách hỏi giá thay bo. Trả lời giá, nói rõ chênh nhau nhiều tùy bo nào và tùy sửa
hay thay, và nói trước rằng nhiều ca giống lỗi bo lại rẻ hơn nhiều.

## Khách hay hỏi thêm

Bo mạch máy lạnh là gì. Là phần điều khiển của máy, quyết định máy chạy hay dừng,
chế độ nào, quạt tốc độ nào, và đọc các cảm biến.

Bo dùng được bao lâu. Bo và tụ thường là nhóm xuống trước trong máy lạnh, vì tụ
khô dần và chân hàn oxy hóa. Con số cụ thể để thợ xác nhận, vì nó phụ thuộc điện
áp khu vực và điều kiện lắp đặt rất nhiều.

Sửa bo được không hay phải thay. Tùy hỏng khu trú hay lan. Hỏng vài linh kiện thì
sửa được; bo đã ẩm ố nhiều chỗ thì nên thay.

Bo thay thế đa năng có dùng được không. Chạy được, nhưng có thể mất một số tính
năng so với bo chính hãng. Nên hỏi rõ trước khi đồng ý.

Máy lạnh tự tắt có nguy hiểm không. Bản thân việc tự tắt thì không. Nhưng máy tự
bật khi không ai ở nhà thì nên xử lý sớm.

Máy báo mã lỗi thì có phải hỏng nặng không. Không nhất thiết. Mã lỗi cho biết máy
tự thấy cái gì bất thường, và nguyên nhân có thể chỉ là một cái rắc cắm tuột.

Ngắt điện rồi bật lại có hết không. Đáng thử, và một số ca vi điều khiển treo
được giải quyết như vậy. Nếu lặp lại thì cần thợ.

Sao bo nhà em hay hỏng. Thường là điện áp khu vực, ẩm nước, hoặc côn trùng. Nếu
không xử lý nguyên nhân nền thì bo mới cũng chết.

## Nền tri thức của tài liệu này

Toàn bộ nội dung được viết lại bằng lời của dự án, không sao chép nguyên văn từ
nguồn nào.

Phần cấu trúc điều khiển của máy điều hòa hai khối, vai trò của bo cục lạnh và bo
công suất trên máy inverter, tín hiệu giữa hai cục, và vai trò của cảm biến nhiệt
độ: nội dung mô đun về điện tử chuyên ngành và hệ thống điều khiển trong chương
trình đào tạo nghề kỹ thuật máy lạnh và điều hòa không khí trình độ trung cấp và
cao đẳng, cộng tài liệu kỹ thuật của các hãng có mặt tại Việt Nam.

Phần nguyên nhân hỏng bo gồm ẩm nước, côn trùng, điện áp không ổn định và sét lan
truyền: tài liệu kỹ thuật ngành điện lạnh trong nước, đối chiếu chéo nhiều nguồn.

Phần an toàn điện, bảo vệ quá tải và ngắn mạch, và yêu cầu về nhánh cấp nguồn:
tham chiếu QCVN 12:2014/BXD về hệ thống điện của nhà ở và nhà công cộng, và TCVN
5699-2-40:2017 về an toàn thiết bị điện gia dụng phần bơm nhiệt, máy điều hòa
không khí và máy hút ẩm.

Phần mã lỗi: chỉ ghi những mã đã đối chiếu được từ tài liệu công bố. Mã không đối
chiếu được thì không ghi, và tài liệu nói rõ nguyên tắc không đoán.

Phần bối cảnh điện lưới, côn trùng, và nhà ở Việt Nam: quan sát thực tế trong
nước, không phải trích dẫn. Cần cập nhật khi hệ thống chạy thật.

## Chỗ cần thợ xác nhận

Mã lỗi của các hãng ngoài ba hãng đã đối chiếu. Đây là mục quan trọng nhất trong
danh sách này. Tra theo tài liệu của đúng model, không đoán, không suy từ hãng
khác.

Khi nào sửa bo còn hợp lý so với thay bo, và bảo hành của phương án sửa.

Bo thay thế đa năng có phù hợp với model cụ thể không và mất tính năng gì.

Giá trị đọc của cảm biến coi là bình thường ở từng nhiệt độ.

Điện áp tại chỗ có nằm trong dải chấp nhận được không, và có cần ổn áp không.

Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
