---
doc_id: KB_FAULT_PIPE_LOW_PRESSURE
doc_type: fault
device_type: water_pipe
fault_code: PIPE_LOW_PRESSURE
name_vi: Áp lực nước yếu toàn nhà
urgency: LOW
confusable_with: [FAUCET_LOW_FLOW, PIPE_BURST, PIPE_RUSTY_WATER, WH_LOW_PRESSURE]
price_policy: Không ghi giá trong tài liệu này. Giá lấy từ bảng giá của hệ thống.
last_reviewed: 2026-09-17
needs_technician_review:
  - Áp lực thực tế tại điểm vào nhà
---

# Áp lực nước yếu toàn nhà

## Bệnh mà một nửa số ca không phải bệnh

Khách báo mã này bằng một câu: nước nhà em yếu quá.

Và trong một phần đáng kể số ca, không có gì hỏng cả. Áp lực nguồn vốn như vậy, hoặc nhà ở
tầng cao, hoặc đang là giờ cao điểm.

Trong một phần khác, vấn đề nằm ở một cái vòi chứ không ở đường ống, và nó xử lý trong năm
phút mà không cần ai tới.

Chỉ một phần nhỏ là bệnh thật của đường ống.

Vì vậy thứ tự đúng của mã này là **thu hẹp trước, chẩn đoán sau**, và việc thu hẹp thì
khách tự làm được hết.

Nhưng có một ngoại lệ phải nhận ra sớm, và nó là lý do mã ưu tiên thấp này vẫn cần cẩn
thận: **áp lực tụt đột ngột có thể là dấu hiệu của một đường ống đang vỡ ở đâu đó**. Phần
đó ở dưới.

## Câu hỏi vàng: phạm vi

**"Nước yếu ở một vòi, một phòng, hay cả nhà ạ?"**

Câu này chia bệnh làm ba hướng hoàn toàn khác nhau, và khách kiểm được trong hai phút bằng
cách mở lần lượt các vòi.

**Một vòi yếu, các vòi khác bình thường:** không phải mã này. Đầu lọc ở vòi bị cặn bít,
hoặc lõi vòi có vấn đề, hoặc van chặn của vòi đó chưa mở hết. Chuyển sang FAUCET_LOW_FLOW,
và khách tự xử lý được.

Nhánh này chiếm tỷ trọng lớn nhất, nên hỏi trước là đúng.

**Một phòng yếu:** nhánh cấp cho phòng đó. Van chặn khu vực, hoặc ống nhánh bị hẹp.

**Cả nhà yếu:** đường chính, van tổng, lọc tổng, bơm, bể chứa, hoặc nguồn cấp.

Câu hỏi thứ hai đi kèm và nó rất quan trọng: **"hàng xóm có bị không ạ?"**

Hàng xóm cũng yếu: nguồn cấp. Không phải chuyện của nhà, và không sửa gì được trong nhà.

Hàng xóm bình thường: chuyện trong nhà.

Hai câu đó tách được phần lớn ca trước khi bàn tới bất cứ chi tiết kỹ thuật nào.

## Câu hỏi thứ ba: yếu từ bao giờ

Quan trọng không kém phạm vi, vì nó tách nhánh nguy hiểm ra khỏi các nhánh còn lại.

**Yếu dần qua nhiều tháng hoặc nhiều năm:** lòng ống hẹp dần vì rỉ hoặc vì cặn vôi. Nhánh
của nhà cũ, và nó không nguy hiểm nhưng cũng không sửa lẻ được.

**Yếu đột ngột, hôm qua còn bình thường:** cần chú ý. Nghi van bị đóng bớt, nghi lọc bị
tắc đột ngột, nghi bơm hỏng — hoặc nghi **có một chỗ vỡ ở đâu đó đang lấy hết nước**.

**Yếu theo giờ, mạnh lúc khác:** áp lực nguồn. Không phải bệnh.

**Yếu theo tầng:** áp không đủ cho chiều cao. Cần bơm.

**Chỉ nước nóng yếu:** không phải đường ống. Vấn đề ở bình nóng lạnh hoặc ở van của nó, và
nó dẫn sang WH_LOW_PRESSURE.

Nhánh cuối đáng hỏi riêng vì khách hay gộp: **"nước lạnh có mạnh không ạ?"** Một câu, và
nó loại được cả một hướng.

## Nhánh phải nhận ra: yếu đột ngột kèm dấu hiệu rò

Đây là lý do mã ưu tiên thấp này vẫn cần được đọc cẩn thận.

Khi một đường ống vỡ ở chỗ khuất — dưới sân, trong tường, dưới nền — nước thoát ra ở đó
thay vì tới các vòi. Áp lực trong nhà tụt.

Khách thấy triệu chứng là nước yếu, và họ báo là nước yếu. Không ai báo là vỡ ống, vì
không ai thấy nước.

**Dấu hiệu nghi:**

Áp tụt **đột ngột** chứ không yếu dần.

Hoá đơn nước tăng bất thường.

Kim đồng hồ nước quay dù mọi vòi đều khoá.

Có vùng sân, nền, hoặc tường lúc nào cũng ẩm.

Nghe tiếng nước chảy khi không ai dùng nước.

Nếu có từ hai dấu hiệu trở lên thì chuyển sang xử lý theo PIPE_BURST, và gợi ý phép thử
đồng hồ nước ngay.

Vì nhánh này tồn tại, **trong mọi ca áp lực yếu đột ngột nên hỏi một câu về hoá đơn nước**.
Câu đó rẻ và nó bắt được nhánh duy nhất nguy hiểm của mã này.

## Sáu nhánh của "cả nhà yếu"

Sau khi đã xác định là cả nhà yếu và hàng xóm thì bình thường.

**Một, van tổng chưa mở hết.** Nhánh phổ biến nhất và nó miễn phí. Ai đó khoá bớt để giảm
tiếng ồn hoặc để chống rò, hoặc khoá lúc sửa gì đó rồi mở lại không hết.

Kiểm: ra chỗ van tổng, xoay mở hết cỡ theo chiều ngược kim đồng hồ.

**Hai, lọc tổng bị tắc.** Nhà có lắp lọc thô ở đầu vào. Lõi lọc đầy cặn thì nước qua rất
chậm.

Dấu hiệu: yếu dần qua vài tháng rồi yếu hẳn. Kiểm: nhìn lõi lọc, thường nhìn thấy được qua
cốc lọc trong suốt.

**Ba, bơm tăng áp hỏng hoặc yếu.** Nhà có bơm. Bơm không chạy, chạy yếu, hoặc rơ le áp
hỏng.

Kiểm: nghe bơm có chạy khi mở vòi không.

**Bốn, bể chứa cạn hoặc phao bể hỏng.** Nhà dùng bể chứa và bơm lên bồn mái. Nếu phao ở bồn
mái hỏng thì bồn không đầy.

Kiểm: nhìn mực nước trong bồn mái hoặc trong bể.

**Năm, lòng ống hẹp vì rỉ.** Nhà cũ dùng ống thép tráng kẽm. Rỉ đóng từ trong ra và thu hẹp
dần tiết diện.

Dấu hiệu: yếu dần qua nhiều năm, thường kèm nước hơi vàng ở lần mở đầu tiên buổi sáng.

**Sáu, ống bị bẹp hoặc gập.** Sau khi thi công, sau khi lún nền, hoặc do đè nặng lên đoạn
ống chôn nông.

## Nhánh nhà cao tầng và nhà cuối nguồn

Không phải bệnh, nhưng nó chiếm nhiều ca và cần được giải thích rõ chứ không bị gạt đi.

Áp lực nước trong mạng cấp có giới hạn. Mỗi mét chiều cao lấy đi một phần áp đó.

Nghĩa là tầng một có thể mạnh trong khi tầng ba rất yếu, với cùng một nguồn. Và ở giờ cao
điểm khi cả khu cùng dùng nước, áp trong mạng tụt xuống, nên tầng trên mất nước hẳn.

Cùng nguyên lý với nhà ở cuối tuyến ống: nước đi qua nhiều nhà trước khi tới, và mỗi nhà
lấy đi một phần.

**Giải pháp không phải là sửa ống**, mà là một trong ba thứ:

**Bể chứa cộng bơm.** Cách phổ biến nhất và ổn định nhất. Nước vào bể khi có áp, bơm lên
khi cần. Nó cắt hẳn sự phụ thuộc vào giờ.

**Bồn nước mái.** Dùng trọng lực. Đơn giản và không tốn điện, nhưng áp phụ thuộc chiều cao
bồn nên vòi sen ở tầng sát mái vẫn yếu.

**Bơm tăng áp trực tiếp trên đường ống.** Rẻ nhất, nhưng có nơi không cho phép vì nó hút
trực tiếp từ mạng và ảnh hưởng tới nhà khác.

Điểm cuối đáng nói: **bơm hút trực tiếp từ đường ống chung có thể vi phạm quy định** ở một
số nơi, và nó làm nhà hàng xóm yếu đi. Đáng nhắc để khách hỏi trước khi lắp.

## Nhánh áp lực yếu theo giờ

Rất phổ biến và nó có một lời giải thích đơn giản mà khách thường thấy nhẹ người khi nghe.

Buổi sáng sớm và chiều tối là lúc cả khu cùng dùng nước. Áp trong mạng tụt xuống.

Ban đêm và giữa trưa thì ít người dùng, áp lên cao.

Cách kiểm và nó là phép thử đáng gợi ý: **mở vòi lúc mười một giờ đêm hoặc lúc năm giờ
sáng**. Nếu lúc đó mạnh thì áp lực nguồn vốn đủ, và vấn đề chỉ là giờ cao điểm.

Kết luận đó quan trọng vì nó đổi hẳn hướng xử lý: không phải sửa gì trong nhà, mà là tích
nước vào lúc áp cao để dùng vào lúc áp thấp. Tức là bể chứa hoặc bồn mái.

Nhiều khách đã gọi thợ nhiều lần cho chuyện này và lần nào cũng không tìm ra gì, vì thợ tới
vào giữa buổi khi nước đang mạnh.

Vì vậy nếu khách kể là thợ tới thì nước bình thường, đó chính là dấu hiệu của nhánh này chứ
không phải chuyện lạ.

## Nhánh nước yếu sau khi sửa chữa

Đáng tách vì nó thu hẹp rất nhanh.

Nếu khách kể là nước yếu ngay sau khi nhà sửa chữa, sau khi khu vực mất nước rồi có lại,
hoặc sau khi đơn vị cấp nước sửa đường ống ngoài đường, thì nghi ngờ tập trung vào ba thứ.

**Van nào đó chưa mở hết.** Thợ khoá lúc làm rồi mở lại không hết. Nhánh phổ biến nhất và
miễn phí.

**Cặn bị khuấy lên và bít lọc hoặc bít đầu vòi.** Sau khi đường ống ngoài đường được sửa,
cặn trong ống bị khuấy và trôi vào nhà. Nó tích ở lọc tổng và ở đầu lọc các vòi.

Dấu hiệu kèm: nước đục hoặc có màu trong vài ngày đầu. Nhánh này giao với PIPE_RUSTY_WATER.

Cách xử lý: tháo rửa lọc tổng và các đầu lọc vòi. Việc khách làm được và nó giải quyết phần
lớn ca nhóm này.

**Khí trong đường ống.** Sau khi mất nước rồi có lại, ống có khí. Nước ra ngắt quãng, có
tiếng phì phì, và yếu. Nó tự hết sau khi xả vài phút ở vòi cao nhất.

Nhánh cuối không phải bệnh, và giải thích được thì tránh một lần gọi thợ.

## Việc khách tự làm được

Nhiều, và mã này có tỷ lệ tự xử lý cao nhất của cụm đường ống.

**Mở lần lượt từng vòi trong nhà** để xác định phạm vi. Việc đầu tiên và quan trọng nhất.

**Kiểm tra van tổng đã mở hết chưa.**

**Kiểm tra van chặn ở chân từng thiết bị.**

**Tháo đầu lọc ở vòi ra rửa.** Xoay ra bằng tay hoặc bằng kìm có lót vải, rửa sạch cặn, lắp
lại. Với nhánh một vòi yếu thì việc này giải quyết phần lớn ca.

**Rửa lõi lọc tổng**, nếu nhà có.

**Thử vào ban đêm** để tách nhánh giờ cao điểm.

**Nhìn mực nước trong bồn mái hoặc bể chứa.**

**Nhìn đồng hồ nước** xem kim có quay khi mọi vòi đều khoá không.

**Xả vòi cao nhất vài phút** sau khi có nước lại, để đẩy khí ra.

Việc không nên tự làm: tháo van tổng; tự lắp bơm; đục tường tìm ống.

## Vì sao lắp bơm không phải lúc nào cũng là câu trả lời

Khách hay nghĩ tới bơm đầu tiên, nên nói rõ khi nào nó đúng và khi nào không.

**Bơm giúp khi:** áp lực nguồn đủ nhưng không đủ cao cho tầng trên; hoặc nhà có bể chứa và
cần đưa nước lên.

**Bơm không giúp khi:**

**Lòng ống bị hẹp vì rỉ.** Bơm đẩy mạnh hơn vào một đường ống đã hẹp thì lưu lượng vẫn
không tăng bao nhiêu, và áp cao hơn còn làm mối nối yếu bung ra.

**Nguồn không đủ nước.** Bơm không tạo ra nước. Nếu đường ống vào nhà vốn ít nước thì bơm
chỉ hút mạnh hơn và có khi hút cả khí.

**Có chỗ rò đang lấy hết nước.** Bơm chỉ làm chỗ rò chảy mạnh hơn.

Vì vậy thứ tự đúng: **xác định nguyên nhân trước, rồi mới quyết định có lắp bơm không**.
Lắp bơm cho một hệ thống đang có vấn đề khác thì tốn tiền mà không giải quyết được, và có
khi làm hỏng thêm.

Nói điều này rõ là đúng, kể cả khi khách đang muốn lắp bơm ngay.

## Khách nói thế nào

"nước yếu", "nước chảy nhỏ", "áp lực nước yếu", "nước không lên được tầng trên", "vòi sen
yếu quá", "nước chảy rỉ rả", "giờ cao điểm là mất nước", "nước yếu dần", "tắm mà nước như
mưa phùn".

Không dấu: nuoc yeu, nuoc chay nho, ap luc nuoc yeu, nuoc khong len duoc tang tren, voi
sen yeu qua, gio cao diem la mat nuoc.

Cách nói khác: "nước nhà em èo uột", "nước chảy như mèo", "tắm không nổi", "nước lúc mạnh
lúc yếu".

Câu "nước lúc mạnh lúc yếu" là nhánh theo giờ, và nó đáng nhận ra vì cách xử lý khác hẳn.

Câu "nước không lên được tầng trên" là nhánh chiều cao, và nó dẫn tới bể chứa hoặc bơm chứ
không tới việc sửa ống.

Cần tách một chỗ: **"nước yếu" có thể chỉ là một cái vòi**. Khách hay khái quát hoá từ một
chỗ. Hỏi phạm vi luôn là câu đầu tiên.

## Đọc ảnh

Ảnh hoặc video dòng nước chảy từ vòi. Cho biết mức độ thật, thứ mà từ "yếu" thì mỗi người
hiểu một kiểu.

Video có ích hơn ảnh với mã này.

Ảnh đầu lọc vòi sau khi tháo ra. Thấy được mức độ cặn bám. Nếu đầy cặn thì đã có câu trả
lời cho nhánh một vòi.

Ảnh lõi lọc tổng, nếu nhà có. Cùng lý do.

Ảnh van tổng. Thấy được nó mở tới đâu.

Ảnh máy bơm và bể chứa. Có ích cho nhánh bơm.

Ảnh bồn nước mái và phao trong bồn.

Ảnh đồng hồ nước với kim nhỏ, cho nhánh nghi rò.

Ảnh cốc nước hứng từ vòi. Nếu nước đục hoặc có cặn thì nó nối sang nhánh rỉ và giải thích
được vì sao lọc bị bít.

## Lẫn với bệnh nào

**FAUCET_LOW_FLOW.** Cặp phải tách đầu tiên, vì đó là nhánh phổ biến nhất và rẻ nhất. Tách
bằng câu hỏi phạm vi.

**PIPE_BURST.** Nhánh nguy hiểm ẩn trong mã này. Tách bằng ba dấu hiệu: yếu đột ngột, hoá
đơn nước tăng, và kim đồng hồ quay khi không dùng nước.

**PIPE_RUSTY_WATER.** Cùng một nguyên nhân gốc ở nhà cũ: ống thép tráng kẽm rỉ. Rỉ vừa làm
hẹp lòng ống vừa làm nước đục. Nếu khách có cả hai triệu chứng thì chúng là một chuyện, và
nó nói lên rằng cả tuyến đã tới tuổi.

**WH_LOW_PRESSURE.** Nếu chỉ nước nóng yếu thì không phải mã này. Tách bằng một câu về nước
lạnh.

Có một nhánh không thuộc bệnh nào: **nguồn cấp yếu**. Tách bằng câu hỏi về hàng xóm, và nên
hỏi sớm vì nó loại bỏ toàn bộ việc tìm kiếm trong nhà.

## Sửa hay làm lại tuyến

Với nhà cũ dùng ống thép tráng kẽm, đây là câu hỏi thật.

Rỉ đóng từ trong ra và nó đóng đều trên cả tuyến, vì mọi đoạn cùng vật liệu và cùng tuổi.

Nghĩa là **không có một chỗ nào để sửa**. Thay một đoạn thì các đoạn còn lại vẫn hẹp như
cũ, và áp lực không cải thiện được bao nhiêu.

Vì vậy với nhánh này, câu trả lời trung thực là: thay cả tuyến, hoặc chấp nhận sống chung
cộng với một giải pháp bù như bể chứa và bơm.

Nói thẳng điều đó thay vì để khách sửa từng đoạn qua nhiều năm.

Có một lựa chọn trung gian nên nêu: **kéo tuyến mới đi nổi hoặc trong hộp kỹ thuật**, bỏ
tuyến cũ trong tường. Rẻ hơn đục theo tuyến cũ nhiều, và sau này sửa dễ hơn.

Với các nhánh khác thì chi phí thấp: mở van, rửa lọc, thay lọc, sửa bơm. Phần lớn ca của
mã này không đắt, và nói được điều đó sớm thì khách bớt lo.

## Phòng cho lần sau

Rửa đầu lọc các vòi định kỳ, nhất là ở khu vực nước cứng hoặc nước có cặn.

Thay hoặc rửa lõi lọc tổng theo chu kỳ, nếu nhà có.

Sau mỗi lần khu vực mất nước rồi có lại, xả vài phút ở vòi cao nhất rồi mới dùng.

Sau khi sửa chữa gì đó, kiểm tra các van đã mở hết chưa.

Vệ sinh bể chứa và bồn mái định kỳ, vì cặn trong đó trôi xuống làm bít lọc và bít vòi.

Với nhà tầng cao hoặc cuối nguồn: tính tới bể chứa ngay từ đầu thay vì chịu đựng rồi lắp
bơm tạm.

Theo dõi hoá đơn nước. Áp yếu dần kèm hoá đơn tăng là tổ hợp đáng chú ý.

## Kịch bản mẫu

Khách nhắn "nước nhà em yếu quá". Hỏi phạm vi trước: một vòi, một phòng, hay cả nhà. Và
hỏi hàng xóm có bị không.

Khách nhắn "chỉ vòi rửa bát yếu thôi". Không phải mã này. Hướng dẫn tháo đầu lọc ra rửa.

Khách nhắn "cả nhà yếu, hàng xóm cũng vậy". Nguồn cấp. Nói rõ không sửa gì trong nhà được,
và nêu giải pháp bể chứa nếu chuyện kéo dài.

Khách nhắn "giờ cao điểm là không có nước". Nhánh theo giờ. Gợi ý thử vào ban đêm để xác
nhận, và nêu hướng tích nước.

Khách nhắn "nước yếu dần mấy năm nay, nhà em xây lâu rồi". Nhánh ống rỉ. Nói thẳng rằng cả
tuyến cùng tình trạng và sửa lẻ không cải thiện được.

Khách nhắn "hôm qua còn bình thường, hôm nay yếu hẳn". Nhánh cần chú ý. Hỏi hoá đơn nước
và gợi ý nhìn đồng hồ xem kim có quay không.

Khách nhắn "em lắp bơm được không". Hỏi nguyên nhân trước, và nói rõ ba trường hợp bơm
không giúp được gì.

Khách nhắn "chỉ nước nóng yếu". Không phải mã này. Chuyển sang nhánh bình nóng lạnh.

## Nền tri thức của tài liệu này

Toàn bộ nội dung được viết lại bằng lời của dự án, không sao chép nguyên văn từ nguồn
nào.

Quan hệ giữa áp suất và chiều cao cột nước, giải thích vì sao tầng trên yếu hơn tầng dưới:
kiến thức thuỷ tĩnh phổ thông.

Hiện tượng tổn thất áp suất trên đường ống và ảnh hưởng của tiết diện lòng ống tới lưu
lượng: kiến thức thuỷ lực phổ thông, và là cơ sở giải thích vì sao bơm không bù được cho
ống bị hẹp.

Cơ chế rỉ sét đóng từ trong ống thép tráng kẽm làm thu hẹp tiết diện: kiến thức ăn mòn kim
loại.

Yêu cầu về cấp nước bên trong nhà, gồm áp lực tối thiểu tại thiết bị và giải pháp bể chứa
cùng bơm tăng áp: tham chiếu TCVN 4513 về cấp nước bên trong.

Việc bơm hút trực tiếp từ mạng cấp chung ảnh hưởng tới hộ khác và có thể bị hạn chế: quy
định của đơn vị cấp nước, cần kiểm tra theo địa phương.

Hiện tượng khí trong đường ống sau khi mất nước rồi có lại: kiến thức thuỷ lực phổ thông.

Bối cảnh áp lực nguồn thay đổi theo giờ, nhà cuối tuyến và nhà tầng cao, cùng tần suất của
nhánh cặn bị khuấy lên sau khi đơn vị cấp nước sửa đường ống: quan sát thực tế trong nước,
không phải trích dẫn. Cần cập nhật khi hệ thống chạy thật.

## Chỗ cần thợ xác nhận

Áp lực thực tế tại điểm vào nhà là bao nhiêu. Cần đo, và nó là căn cứ quyết định có nên
lắp bơm không.

Vật liệu ống và tuổi của tuyến, quyết định giữa xử lý điểm và thay tuyến.

Lòng ống có bị hẹp tới mức nào, nếu nghi rỉ hoặc cặn.

Bơm và rơ le áp có làm việc đúng không, ở nhà có bơm.

Có chỗ rò nào đang lấy nước không, nếu áp tụt đột ngột.

Việc lắp bơm hút trực tiếp có được phép ở khu vực đó không.

Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
