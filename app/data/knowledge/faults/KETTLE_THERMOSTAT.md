---
doc_id: KB_FAULT_KETTLE_THERMOSTAT
doc_type: fault
device_type: kettle
fault_code: KETTLE_THERMOSTAT
name_vi: Hỏng rơ le nhiệt
urgency: MEDIUM
confusable_with: [KETTLE_SCALE, KETTLE_SWITCH, KETTLE_HEATING_BASE]
price_policy: Không ghi giá trong tài liệu này. Giá lấy từ bảng giá của hệ thống.
last_reviewed: 2026-09-17
needs_technician_review:
  - Rơ le có còn tốt không sau khi đã tẩy cặn và kiểm nắp
---

# Hỏng rơ le nhiệt

## Bệnh mà phần lớn ca không phải là rơ le hỏng

Khách báo mã này bằng một trong hai câu: ấm sôi rồi mà không tự tắt, hoặc ấm tắt trước khi
nước sôi.

Cả hai đều là triệu chứng của rơ le nhiệt. Nhưng trong phần lớn ca, **rơ le vẫn tốt và nó
đang phản ứng đúng với một điều kiện sai**.

Nắp không đóng kín. Nước quá ít hoặc quá đầy. Cặn vôi bít đường dẫn hơi. Cặn vôi làm mâm quá
nóng.

Bốn thứ đó chiếm phần lớn số ca, và cả bốn khách tự xử lý được.

Vì vậy nguyên tắc của mã này: **kiểm bốn thứ đó trước, và chỉ kết luận rơ le hỏng sau khi
đã loại hết**.

Nói theo hướng đó cũng đúng về mặt kinh tế, vì với một cái ấm rẻ thì kết luận "rơ le hỏng"
gần như đồng nghĩa với "thay ấm", và đó là kết luận không nên đưa ra vội.

## Rơ le nhiệt làm việc thế nào

Chi tiết quyết định của cả mã này, và nó không hiển nhiên.

**Rơ le nhiệt không đo nhiệt độ của nước.**

Nó nằm ở phần thân hoặc trong tay cầm, cách xa nước. Nó cảm nhận **hơi nước bốc lên**.

Khi nước sôi, hơi nước bốc lên trong ấm và đi theo một **đường dẫn nhỏ** trong thân hoặc
trong tay cầm, tới chỗ đặt rơ le.

Ở đó có một lá kim loại kép: hai lớp kim loại khác nhau dán vào nhau, và chúng giãn nở khác
nhau khi nóng. Hơi nóng làm lá cong đi, và lá cong thì bật cái lẫy giữ công tắc ra.

Công tắc bật lên, điện ngắt.

Ba hệ quả quyết định mọi thứ:

**Nếu hơi không đi đúng đường đó thì ấm không biết nước đã sôi.** Nắp hở, đường dẫn bít, hay
gioăng mòn đều làm hơi đi sai đường.

**Nếu hơi tới quá sớm hoặc quá nhiều thì ấm tắt sớm.**

**Lá kim loại cần thời gian nguội** để trở lại hình dạng cũ. Đó là lý do vừa đun xong thì
không gạt công tắc xuống được.

## Bốn thứ phải kiểm trước

Theo thứ tự, và cả bốn miễn phí.

**Một, nắp đóng kín chưa.**

Nguyên nhân số một của ca ấm không tự tắt. Nắp hở thì hơi thoát ra miệng ấm thay vì đi theo
đường dẫn.

Nhiều ấm có nắp bật và nó đóng nghe tiếng tách. Nếu không nghe tiếng đó thì nắp chưa vào
khớp.

Đáng hỏi luôn: có ai vừa rửa ấm và lắp nắp lại không, vì nắp lắp lệch là chuyện hay xảy ra
sau đó.

**Hai, mực nước.**

Dưới vạch tối thiểu: không đủ hơi, hoặc hơi không tới được đường dẫn. Ấm đun tới cạn.

Trên vạch tối đa: nước sôi trào vào đường dẫn hơi, làm rơ le không nhận đúng, và nước cũng
trào ra ngoài xuống đế.

**Ba, cặn vôi.**

Hai hướng khác nhau, và chúng gây hai triệu chứng ngược nhau.

Cặn bít đường dẫn hơi: ấm không tự tắt.

Cặn phủ mâm nhiệt làm mâm quá nóng: rơ le chống cạn cắt sớm, và ấm tắt trước khi sôi.

**Bốn, gioăng nắp.**

Mòn hoặc chai thì nắp đóng nhưng không kín, và hơi vẫn thoát ra ngoài.

Bốn thứ này nên được hỏi theo đúng thứ tự, và mỗi câu đều là câu khách trả lời được ngay.

## Nhánh không tự tắt

Triệu chứng: nước sôi ùng ục, hơi phun ra, mà công tắc vẫn ở vị trí bật.

Sau bốn thứ ở trên, nếu vẫn không tự tắt thì nghi:

**Đường dẫn hơi bị bít hoàn toàn.** Cặn vôi, hoặc có vật lạ.

**Lá kim loại kép đã mỏi.** Sau hàng nghìn chu kỳ cong rồi thẳng, nó không còn cong đủ để
bật lẫy.

**Lẫy giữ công tắc bị mòn.** Rơ le bật nhưng lẫy không nhả. Nhánh này thực ra thuộc
KETTLE_SWITCH.

Có một cách tẩy cặn dành riêng cho đường dẫn hơi mà khách tự làm được, và nó không hiển
nhiên:

Khi ngâm giấm để tẩy cặn, **nghiêng ấm qua lại và lắc nhẹ**, để giấm vào được đường dẫn hơi
ở phía trên.

Ngâm bình thường thì giấm chỉ ở đáy, còn đường dẫn hơi thì nằm cao hơn mực nước, nên nó
không được tẩy.

Chi tiết này đáng nói vì nhiều khách tẩy cặn xong mà ấm vẫn không tự tắt, và họ kết luận là
rơ le hỏng trong khi thực ra chỉ là chưa tẩy tới chỗ cần.

## Nhánh không tự tắt có nguy hiểm không

Khách sẽ hỏi, và câu trả lời trung thực có hai phần.

**Ấm không cháy.** Nước cạn dần, mâm nhiệt nóng lên, và rơ le chống cạn cắt điện. Đó là chi
tiết an toàn thứ hai và nó độc lập với rơ le nhiệt.

Nghĩa là ấm không tự tắt thì cuối cùng vẫn tắt, chỉ là tắt muộn và tắt vì lý do khác.

**Nhưng có ba vấn đề thật:**

**Hơi nóng phun ra liên tục.** Trong bếp có trẻ nhỏ thì đây là rủi ro bỏng, và nó không nhỏ.

**Mâm nhiệt bị nung khô mỗi lần.** Nó rút ngắn tuổi thọ mâm, và nó làm gioăng quanh mâm chai
nhanh. Từ đó dẫn tới KETTLE_LEAK, một mã ưu tiên cao.

**Tốn điện và mất nước.**

Vì vậy câu trả lời đúng: không cháy, nhưng nên xử lý, và lý do chính là nó làm hỏng các thứ
khác chứ không phải vì nó nguy hiểm trực tiếp.

Và một lời khuyên thực tế trong lúc chờ: **đứng cạnh và tự tắt bằng tay khi thấy sôi**, đừng
bật rồi đi chỗ khác.

## Nhánh tắt trước khi nước sôi

Triệu chứng: ấm tắt sau một hai phút, nước mới âm ấm.

Đây thường **không phải rơ le nhiệt hỏng** mà là **rơ le chống cạn đang cắt**, và nó cắt vì
mâm quá nóng.

Nguyên nhân số một: **cặn vôi phủ mâm nhiệt**.

Cơ chế: cặn cách nhiệt, nên nhiệt không truyền hết vào nước và nằm lại ở mâm. Mâm vượt ngưỡng,
rơ le chống cạn cắt.

Cách xác nhận rất đơn giản: **nhìn xuống đáy ấm**. Nếu có lớp trắng dày thì gần như chốt
được.

Cách xử lý: tẩy cặn. Không cần sửa gì, và nhánh này dẫn sang KETTLE_SCALE.

Nguyên nhân thứ hai: **đun quá ít nước**. Mâm nóng nhanh hơn nước hấp thụ được.

Nguyên nhân thứ ba: **rơ le chống cạn đã yếu** và cắt ở ngưỡng thấp hơn thiết kế. Nhánh này
thì cần thay, và nó thuộc mã này.

Thứ tự kiểm rõ ràng: nhìn cặn trước, kiểm mực nước sau, rồi mới tới rơ le.

Rất nhiều ca dừng ở bước đầu tiên, và một buổi ngâm giấm giải quyết được thứ mà khách tưởng
là phải mua ấm mới.

## Nhánh công tắc không giữ được

Triệu chứng: gạt công tắc xuống thì nó bật lên ngay, không giữ.

Có hai nhánh và chúng khác hẳn nhau.

**Nhánh một, và nó không phải hỏng: ấm vừa đun xong.**

Lá kim loại kép còn nóng và chưa trở lại hình dạng cũ. Chừng nào nó còn cong thì nó còn giữ
lẫy ở trạng thái nhả.

Cách xử lý: chờ vài phút cho ấm nguội rồi thử lại.

Đây là nhánh rất phổ biến và khách hay tưởng ấm hỏng. Đáng hỏi ngay: **"ấm có vừa đun xong
không ạ?"**

Nếu đun lại ngay sau khi vừa sôi thì hiện tượng này gần như chắc chắn xảy ra, và nó là thiết
kế chứ không phải lỗi.

**Nhánh hai: lẫy giữ công tắc đã mòn.**

Cơ cấu cơ khí giữ công tắc ở vị trí bật đã mòn sau hàng nghìn lần dùng.

Dấu hiệu tách: xảy ra cả khi ấm nguội hoàn toàn, và nó tệ dần qua thời gian.

Nhánh này thuộc KETTLE_SWITCH.

Câu hỏi tách hai nhánh: **"lúc ấm nguội hẳn thì gạt có giữ được không ạ?"**

## Nhánh ấm không chịu bật lại sau khi đun

Biến thể của nhánh trên và đáng tách vì nó có một lời giải khác.

Khách kể: đun xong một ấm, muốn đun tiếp ấm thứ hai ngay, nhưng công tắc không gạt được.

Đây là hoạt động bình thường của rơ le, và có một lý do thiết kế đằng sau nó.

Rơ le nhiệt cần nguội để trở lại trạng thái sẵn sàng. Thời gian đó thường là vài phút.

Trong thời gian đó, cái ấm từ chối bật lại.

Điều này không phải lỗi, và nó có tác dụng phụ tốt: nó ngăn việc đun liên tục làm mâm nhiệt
quá tải.

Cách xử lý: chờ. Hoặc đổ nước lạnh vào ấm để nó nguội nhanh hơn, nếu vội.

Mẹo thứ hai đáng nói vì nó thực tế: đổ nước lạnh vào thì cả mâm lẫn khu vực rơ le nguội
nhanh, và ấm bật lại được sớm hơn.

Nếu ấm nguội hẳn rồi mà vẫn không gạt được, thì đó mới là bệnh.

## Việc khách tự làm được

**Kiểm nắp đóng kín chưa.** Việc đầu tiên và nó giải quyết nhiều ca nhất.

**Kiểm mực nước trong khoảng giữa hai vạch.**

**Nhìn đáy ấm xem có cặn không.**

**Tẩy cặn bằng giấm, và nghiêng ấm khi ngâm** để giấm vào đường dẫn hơi.

**Kiểm gioăng nắp** xem có mòn, có chai, có bị lắp lệch không.

**Chờ ấm nguội rồi thử lại**, với nhánh công tắc không giữ.

**Đổ nước lạnh vào cho nguội nhanh**, nếu cần đun lại ngay.

**Kiểm xem nắp có bị lắp ngược không**, sau khi rửa ấm. Một số nắp lắp được theo hai chiều
nhưng chỉ một chiều là đúng.

Việc khách không nên tự làm: mở ấm ra để thay rơ le. Lý do ở phần dưới, và nó là lý do kinh
tế cộng an toàn.

## Vì sao không nên sửa rơ le

Khi đã loại hết bốn thứ ở trên mà ấm vẫn không tự tắt hoặc vẫn tắt sớm, thì rơ le đúng là
đã hỏng.

Và lúc đó câu trả lời trung thực là: **nên thay ấm**.

**Lý do thứ nhất: phép tính.** Rơ le là chi tiết rẻ, nhưng nó nằm sâu trong cụm tay cầm hoặc
trong thân ấm. Việc tháo ra và lắp lại chiếm phần lớn công. Cộng lại thường tiệm cận giá một
cái ấm mới.

**Lý do thứ hai: nó liên quan tới phần kín.** Trên nhiều model, việc tháo tới rơ le đòi mở
phần đáy, tức là đụng tới lớp kín giữa nước và điện.

Lắp lại không kín thì tạo ra KETTLE_LEAK, và đó là mã ưu tiên cao.

**Lý do thứ ba: tuổi.** Nếu rơ le đã mỏi sau nhiều nghìn chu kỳ, thì gioăng, mâm nhiệt, và
các tiếp điểm trong cái ấm đó cũng cùng tuổi và cùng số chu kỳ.

Thay một chi tiết thì vài tháng sau tới lượt cái khác.

Vì vậy nói thẳng và nói sớm: với ấm phổ thông thì nên thay.

Ngoại lệ: ấm còn bảo hành, hoặc ấm loại đắt tiền như ấm có bình giữ nhiệt hoặc ấm chỉnh
được nhiệt độ. Với những loại đó thì phép tính đổi, và sửa có thể đáng.

Đáng hỏi sớm: **"ấm mua lâu chưa ạ?"**

## Khách nói thế nào

"ấm không tự tắt", "ấm sôi rồi không nhảy", "ấm siêu tốc không ngắt", "công tắc không bật
lên", "ấm tắt trước khi sôi", "nước chưa sôi ấm đã tắt", "ấm tự tắt giữa chừng", "gạt công
tắc không giữ", "ấm đun không được nữa".

Không dấu: am khong tu tat, am soi roi khong nhay, am sieu toc khong ngat, cong tac khong
bat len, am tat truoc khi soi, gat cong tac khong giu.

Cách nói khác: "ấm nhà em không biết dừng", "sôi ùng ục mà cứ đun", "ấm cứ tắt sớm", "gạt
xuống nó bật lên liền", "ấm không chịu chạy nữa".

Câu "sôi ùng ục mà cứ đun" là mô tả rõ nhất của nhánh không tự tắt.

Câu "gạt xuống nó bật lên liền" cần hỏi lại một câu về việc ấm có vừa đun xong không, vì
nhánh đó rất phổ biến và nó không phải bệnh.

Câu "ấm tự tắt giữa chừng" mơ hồ: có thể là tắt trước khi sôi, có thể là tắt rồi bật lại.
Hỏi nước đã nóng tới đâu khi nó tắt là tách được.

## Đọc ảnh

Ảnh nắp ấm ở vị trí đóng, chụp nghiêng. Thấy được nắp có khít không, có khe hở không.

Ảnh gioăng nắp. Thấy được có mòn, chai, hay lắp lệch không.

**Ảnh bên trong lòng ấm nhìn xuống đáy.** Ảnh quan trọng nhất, vì nó cho biết có cặn không,
và cặn là nguyên nhân số một của cả hai nhánh.

Ảnh mực nước so với hai vạch. Có ích để loại nhánh nước quá ít hoặc quá đầy.

Ảnh miệng đường dẫn hơi trong lòng ấm, nếu nhìn thấy được. Trên một số model nó là một lỗ
nhỏ gần miệng ấm.

Ảnh công tắc và vùng nhựa quanh nó. Thấy được có ố vàng, có biến dạng không, đó là dấu hiệu
phát nhiệt.

Ảnh tem thông số dưới đáy. Cho biết model, công suất, và đôi khi năm sản xuất.

Video ngắn quay lúc đun tới sôi. Có giá trị cao với mã này, vì nó cho thấy chính xác ấm phản
ứng thế nào và ở thời điểm nào.

## Lẫn với bệnh nào

**KETTLE_SCALE.** Đây là cặp quan trọng nhất, và quan hệ là nhân quả chứ không phải nhầm:
cặn vôi gây cả hai triệu chứng của mã này, theo hai hướng khác nhau.

Vì vậy trong mọi ca của mã này, câu hỏi về cặn nên đi trước mọi câu hỏi khác về rơ le.

Nhầm hướng này tốn kém rõ ràng: khách bỏ một cái ấm chỉ cần ngâm giấm một buổi.

**KETTLE_SWITCH.** Nhánh công tắc không giữ thuộc cả hai mã. Tách bằng việc ấm có vừa đun
xong không, và bằng việc lúc nguội hẳn thì có giữ được không.

**KETTLE_HEATING_BASE.** Nếu ấm hoàn toàn không nóng, không phải tắt sớm, thì đó là mã kia.
Tách bằng việc nước có ấm lên chút nào không trước khi tắt.

Có một nhánh không thuộc bệnh nào: **ấm mới mua và khách chưa quen**. Một số ấm tắt khi nước
đạt gần sôi chứ không sôi bùng, và một số ấm có chế độ giữ ấm. Đáng hỏi nếu ấm mới mua.

## Phòng cho lần sau

**Tẩy cặn định kỳ, và nghiêng ấm khi ngâm** để giấm vào được đường dẫn hơi.

Đây là việc phòng được cả hai nhánh của mã này cùng lúc.

**Đóng nắp cho tới khi nghe tiếng khớp**, mỗi lần đun.

**Đổ nước trong khoảng giữa hai vạch**, không ít hơn và không nhiều hơn.

**Kiểm nắp lắp đúng chiều sau khi rửa ấm.**

**Đừng đun lại ngay sau khi vừa sôi.** Cho rơ le nguội vài phút. Nếu vội thì tráng nước lạnh.

**Đổ hết nước thừa sau mỗi lần đun**, vì nó vừa giảm cặn vừa tránh việc đun lại nước cũ nhiều
lần.

**Đừng bật ấm rồi bỏ đi**, nhất là nếu ấm đã có dấu hiệu không tự tắt.

**Xử lý sớm khi ấm bắt đầu tắt muộn hơn bình thường.** Ở giai đoạn đó thường chỉ là cặn, và
tẩy thì miễn phí.

## Kịch bản mẫu

Khách nhắn "ấm sôi rồi mà không tự tắt". Hỏi nắp có đóng kín không, rồi hỏi về cặn ở đáy.
Hai câu đó loại được phần lớn ca.

Khách nhắn "nắp đóng kín rồi mà vẫn không tắt". Hướng dẫn tẩy cặn, kèm chi tiết nghiêng ấm
để giấm vào đường dẫn hơi.

Khách nhắn "ấm tắt trước khi nước sôi". Hỏi đáy ấm có lớp trắng dày không. Nếu có thì chốt
nhánh cặn và hướng dẫn tẩy.

Khách nhắn "gạt công tắc xuống nó bật lên ngay". Hỏi ấm có vừa đun xong không. Nếu có thì
giải thích và bảo chờ vài phút.

Khách nhắn "ấm nguội hẳn rồi mà vẫn không gạt được". Nhánh lẫy mòn. Chuyển sang mã công tắc.

Khách nhắn "không tự tắt có nguy hiểm không". Trả lời đủ hai phần: không cháy vì có rơ le
chống cạn, nhưng nên xử lý vì hơi nóng và vì nó làm hỏng mâm với gioăng.

Khách nhắn "tẩy cặn rồi vẫn không tự tắt". Hỏi có nghiêng ấm khi ngâm không. Nếu chưa thì
làm lại. Nếu rồi thì đây mới là nhánh rơ le, và nói thẳng về phép tính.

Khách nhắn "thay cái rơ le được không". Nói đủ ba lý do nên thay ấm, và hỏi ấm mua lâu chưa
để xét ngoại lệ bảo hành.

## Nền tri thức của tài liệu này

Toàn bộ nội dung được viết lại bằng lời của dự án, không sao chép nguyên văn từ nguồn
nào.

Nguyên lý rơ le nhiệt dùng lá kim loại kép cảm nhận hơi nước qua đường dẫn thay vì đo nhiệt
độ nước, và vai trò độc lập của rơ le chống cạn: nội dung mô đun thực hành thiết bị gia dụng
trong chương trình đào tạo nghề, đối chiếu tài liệu kỹ thuật của các hãng có mặt tại Việt
Nam.

Hiện tượng lá kim loại kép cần thời gian nguội để trở lại hình dạng, giải thích vì sao ấm
không bật lại được ngay sau khi đun: kiến thức vật liệu và nhiệt học phổ thông.

Cơ chế lớp cặn vôi cách nhiệt làm mâm chạy quá nhiệt và làm rơ le chống cạn cắt sớm: kiến
thức truyền nhiệt phổ thông.

Cơ chế cặn bít đường dẫn hơi làm rơ le nhiệt không nhận được tín hiệu: cùng cơ sở.

Hiện tượng mỏi của lá kim loại kép sau nhiều nghìn chu kỳ: kiến thức vật liệu phổ thông.

Yêu cầu an toàn với thiết bị đun chất lỏng dùng trong gia đình, gồm cơ cấu bảo vệ chống chạy
khô: tham chiếu TCVN 5699-1 về an toàn thiết bị điện gia dụng.

Tỷ trọng cao của các nhánh không phải hỏng trong tổng số ca báo ấm không tự tắt: kinh nghiệm
nghề của thợ sửa đồ điện gia dụng trong nước. Cần cập nhật khi hệ thống chạy thật.

## Chỗ cần thợ xác nhận

Rơ le có còn tốt không, sau khi đã tẩy cặn và đã kiểm nắp cùng mực nước.

Đường dẫn hơi có thông không.

Rơ le chống cạn có cắt ở đúng ngưỡng không.

Mâm nhiệt có bị ảnh hưởng chưa, nếu ấm đã bị đun tới cạn nhiều lần vì không tự tắt.

Gioăng quanh mâm nhiệt có còn kín không, cùng lý do.

Ấm còn hạn bảo hành không.

Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
