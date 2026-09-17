---
doc_id: KB_FAULT_KETTLE_HEATING_BASE
doc_type: fault
device_type: kettle
fault_code: KETTLE_HEATING_BASE
name_vi: Hỏng mâm nhiệt
urgency: LOW
confusable_with: [KETTLE_SWITCH, KETTLE_SCALE, KETTLE_THERMOSTAT]
price_policy: Không ghi giá trong tài liệu này. Giá lấy từ bảng giá của hệ thống.
last_reviewed: 2026-09-17
needs_technician_review:
  - Mâm nhiệt hỏng hay chỉ mất điện tới nó
---

# Hỏng mâm nhiệt

## Bệnh đặt dấu chấm hết cho cái ấm

Trong cụm ấm siêu tốc, đây là mã mà câu trả lời gần như luôn là thay ấm.

Không phải vì nguy hiểm, và không phải vì không sửa được. Mà vì mâm nhiệt là chi tiết chính
của cái ấm: nó chiếm phần lớn giá trị, và việc thay nó đòi tháo tới phần kín giữa nước và
điện.

Vì vậy mã này ở mức ưu tiên thấp về an toàn nhưng dứt khoát về kết luận.

Tuy nhiên có một điều quan trọng phải giữ: **đừng kết luận mâm nhiệt hỏng quá sớm**.

Có mấy nhánh rẻ hơn nhiều cho ra đúng triệu chứng "ấm không nóng", và một trong số đó không
tốn đồng nào.

Phần đầu của tài liệu này dành cho việc loại chúng.

## Bốn thứ miễn phí phải loại trước

**Một, ổ cắm.**

Cắm một thiết bị khác vào cùng ổ. Ấm siêu tốc ăn điện lớn và nó hay làm nhảy aptomat của
nhánh đang có nhiều thiết bị khác.

Cũng kiểm tra aptomat có bị nhảy không.

**Hai, ấm đặt đúng vào đế chưa.**

Giữa đáy ấm và đế có một cụm tiếp điểm tròn. Nếu ấm đặt lệch, hoặc nếu có vật gì kẹt ở giữa,
thì điện không lên.

Nhấc ấm ra, đặt lại cho ngay ngắn, xoay nhẹ cho khớp.

**Ba, tiếp điểm bẩn hoặc oxy hoá.**

Rút điện, lau cụm tiếp điểm ở cả đế lẫn đáy ấm bằng khăn khô. Nếu có vết đen hoặc lớp ố thì
chà nhẹ.

Nhánh này phổ biến hơn người ta nghĩ, nhất là ở nhà ẩm hoặc ở ấm hay bị ướt đáy.

**Bốn, ấm còn nóng nên rơ le chưa cho bật lại.**

Nếu vừa đun xong, lá kim loại trong rơ le còn cong và nó giữ công tắc ở trạng thái nhả.

Chờ vài phút cho nguội rồi thử lại.

Bốn thứ này chiếm một phần đáng kể số ca "ấm không nóng", và cả bốn mất chưa tới hai phút.

## Câu hỏi vàng: đèn báo có sáng không

**"Anh chị gạt công tắc xuống thì đèn báo có sáng không ạ?"**

Câu này chia bệnh làm hai nửa gần như không giao nhau.

**Đèn không sáng, công tắc không giữ:** điện chưa tới ấm, hoặc công tắc không đóng được.

Nghi ổ cắm, nghi tiếp điểm ở đế, nghi dây nguồn, hoặc nghi công tắc. Không phải mã này.

**Đèn không sáng nhưng công tắc giữ được:** đèn báo có thể chỉ là đèn hỏng riêng. Cần kiểm
thêm bằng nhiệt.

**Đèn sáng, công tắc giữ, nhưng nước không nóng lên:** điện đã tới nhưng mâm nhiệt không làm
việc. **Đây mới là mã này.**

**Đèn sáng, nước nóng nhưng rất chậm:** mâm còn làm việc nhưng hiệu suất giảm. Nghiêng về
cặn vôi chứ không phải mâm hỏng.

Tổ hợp đèn báo cộng với nhiệt tách được gần hết, và khách trả lời được ngay mà không cần
tháo gì.

## Nhánh đun chậm: gần như luôn là cặn vôi

Đáng tách riêng vì khách hay báo nó là "mâm nhiệt yếu", và nó thì không phải.

Triệu chứng: ấm vẫn nóng, nước vẫn sôi, nhưng lâu hơn trước rõ rệt.

**Mâm nhiệt không "yếu dần".** Dây điện trở hoặc còn nguyên hoặc đã đứt. Nó không mất công
suất từ từ như pin.

Vì vậy khi ấm đun chậm dần qua nhiều tháng, nguyên nhân gần như luôn nằm ở chỗ khác: **lớp
cặn vôi trên mâm cách nhiệt**.

Nhiệt vẫn sinh ra đủ nhưng không truyền hết vào nước.

Cách xác nhận: nhìn xuống đáy ấm. Lớp trắng dày là đã có câu trả lời.

Cách xử lý: tẩy cặn bằng giấm. Nhánh này dẫn sang KETTLE_SCALE và nó không tốn gì.

Có hai nhánh phụ cũng gây đun chậm và cũng không phải mâm hỏng:

**Điện áp nhà yếu.** Ấm ăn điện lớn nên nó nhạy với sụt áp. Dấu hiệu: chỉ chậm vào giờ cao
điểm.

**Đun nhiều nước hơn trước.** Nghe hiển nhiên nhưng đáng hỏi.

## Khi đúng là mâm nhiệt

Sau khi đã loại hết: đèn sáng, công tắc giữ, ổ cắm tốt, không có cặn dày, mà nước hoàn toàn
không ấm lên.

**Dây điện trở đã đứt.** Nguyên nhân số một.

Dây điện trở nằm đúc kín trong mâm. Nó chịu chu kỳ nóng nguội hàng nghìn lần, và mỗi chu kỳ
là một lần giãn nở rồi co lại.

Sau đủ nhiều chu kỳ, nó đứt ở một điểm. Đứt là đứt hẳn, không có giai đoạn yếu dần.

**Rơ le chống cạn đã hỏng ở trạng thái cắt.**

Chi tiết này nằm sát mâm nhiệt và nó cắt điện khi mâm quá nóng. Nếu nó hỏng ở trạng thái
cắt vĩnh viễn, thì mâm không bao giờ nhận được điện dù mọi thứ khác đều tốt.

Nhánh này quan trọng vì **triệu chứng giống hệt mâm cháy nhưng nguyên nhân thì khác**, và
trên một số model nó thay được riêng.

Dấu hiệu nghi: ấm hỏng đột ngột ngay sau một lần bị đun cạn. Rơ le đã cắt lần đó và không
phục hồi.

**Mối nối bên trong bị đứt hoặc cháy.** Ít gặp hơn nhưng có, và nó rẻ hơn thay mâm nếu có
thể tới được.

## Nhánh sau khi bị đun cạn

Nguyên nhân dẫn tới mã này nhiều nhất, và nó phòng được hoàn toàn.

Khi ấm được bật mà không có nước, mâm nhiệt nóng lên rất nhanh vì không có gì hấp thụ nhiệt.

Rơ le chống cạn cắt điện, và đó là việc nó được thiết kế để làm.

Nhưng trong vài giây trước khi nó cắt, nhiệt độ ở mâm đã vượt xa mức bình thường.

Ba hậu quả, và chúng xuất hiện ở ba thời điểm khác nhau:

**Ngay lập tức:** rơ le chống cạn có thể hỏng vĩnh viễn ở trạng thái cắt, và ấm chết ngay.

**Vài tuần tới vài tháng sau:** dây điện trở đã bị sốc nhiệt và nó đứt sớm hơn tuổi thọ bình
thường.

**Vài tháng sau:** gioăng quanh mâm đã bị biến dạng cục bộ, và nó bắt đầu rò. Nhánh này dẫn
sang KETTLE_LEAK, một mã ưu tiên cao.

Vì vậy đáng hỏi trong mọi ca ấm không nóng: **"ấm có lần nào bị bật khi chưa có nước
không ạ?"**

Và đáng nói sau mọi ca đun cạn, kể cả khi ấm vẫn chạy bình thường: nếu có mùi khét hoặc nếu
nhựa quanh đáy biến dạng thì nên thay, đừng đợi.

## Nhánh ấm chạy một lúc rồi tắt và không bật lại

Biến thể đáng tách vì nó dễ nhầm với mã rơ le nhiệt.

Triệu chứng: ấm đun được một lúc, tắt, và sau đó không bật lại được nữa dù đã nguội.

Hai khả năng:

**Rơ le chống cạn cắt và không phục hồi.** Thường vì mâm quá nóng do cặn dày, hoặc do đun
quá ít nước.

**Mâm nhiệt vừa đứt.** Dây điện trở đứt thường xảy ra đúng lúc đang đun, khi kim loại đang
giãn nở nhiều nhất.

Tách bằng việc đã loại cặn chưa: nếu đáy ấm đầy cặn thì nhánh thứ nhất mạnh hơn, và tẩy cặn
có thể cứu được nếu rơ le phục hồi.

Nếu đã tẩy cặn và để nguội hoàn toàn vài giờ mà vẫn không lên, thì nghiêng về mâm đứt.

Có một chi tiết đáng biết: **một số rơ le chống cạn loại tự phục hồi sẽ đóng lại sau khi
nguội hẳn**, nhưng phải nguội thật, có khi vài giờ chứ không phải vài phút.

Vì vậy với nhánh này, đáng khuyên khách để ấm nguội qua đêm rồi thử lại trước khi kết luận.

Đó là lời khuyên rẻ nhất có thể có, và đôi khi nó cứu được cái ấm.

## Vì sao không nên sửa

Khách sẽ hỏi, và câu trả lời trung thực có ba phần.

**Một, phép tính.** Mâm nhiệt là chi tiết chính của cái ấm. Cộng với công tháo lắp, tổng
thường vượt giá một cái ấm mới cùng loại.

**Hai, việc sửa đụng tới phần kín.** Thay mâm nhiệt nghĩa là mở đáy ấm, tháo mâm cũ ra, và
lắp mâm mới với gioăng mới.

Lớp kín đó là thứ duy nhất ngăn nước vào phần điện. Lắp lại không kín thì tạo ra
KETTLE_LEAK, và đó là mã ưu tiên cao trên một thiết bị mà người ta cầm bằng tay ướt.

Và không có cách nào tại chỗ để biết nó còn kín sau một trăm chu kỳ nóng nguội nữa hay
không.

**Ba, tuổi.** Nếu mâm đã đứt sau hàng nghìn chu kỳ, thì gioăng, rơ le, công tắc, và tiếp
điểm trong cái ấm đó đều cùng tuổi và cùng số chu kỳ.

Thay mâm thì vài tháng sau tới lượt cái khác.

Vì vậy với ấm phổ thông, câu trả lời là **nên thay ấm**, và nói thẳng sớm.

**Ngoại lệ:**

**Ấm còn bảo hành.** Hỏi sớm: "ấm mua lâu chưa ạ?"

**Ấm loại đắt tiền**, như ấm có bình giữ nhiệt, ấm chỉnh nhiệt độ, hoặc ấm dùng cho quán.
Với những loại đó phép tính đổi hẳn.

**Nhánh rơ le chống cạn**, nếu trên model đó nó thay được riêng mà không phải mở tới phần
kín. Rẻ hơn nhiều, và đáng hỏi thợ xem có phải trường hợp đó không.

## Khách nói thế nào

"ấm không nóng", "ấm siêu tốc không đun được", "cắm điện mà nước không nóng", "ấm không lên
nhiệt", "đèn sáng mà nước lạnh ngắt", "ấm chết rồi", "ấm không hoạt động", "ấm đun mãi không
sôi", "mâm nhiệt hỏng".

Không dấu: am khong nong, am sieu toc khong dun duoc, cam dien ma nuoc khong nong, den sang
ma nuoc lanh ngat, am dun mai khong soi.

Cách nói khác: "ấm nhà em đơ luôn", "cắm vào không thấy gì", "ấm chạy mà không nóng", "ấm
hết đời rồi hả em".

Câu "đèn sáng mà nước lạnh ngắt" là mô tả chính xác nhất của mã này, và nó đã tự tách với
nhánh công tắc.

Câu "ấm đun mãi không sôi" thì khác: nó nghiêng về cặn vôi chứ không về mâm hỏng. Hỏi nước
có nóng lên chút nào không là tách được.

Cần tách rõ hai câu này, vì chúng dẫn tới hai kết luận rất khác nhau: một cái phải thay ấm,
một cái chỉ cần ngâm giấm.

## Đọc ảnh

Ảnh đèn báo khi đã gạt công tắc. Ảnh có ích nhất cho việc tách nhánh.

Ảnh bên trong lòng ấm nhìn xuống mâm nhiệt. Thấy được có cặn dày không, và thấy được mâm có
vết cháy, vết ố nâu, hay vết phồng không.

Vết cháy hoặc vết đổi màu trên mâm là dấu hiệu đã bị quá nhiệt, và nó xác nhận nhánh đun
cạn.

Ảnh đáy ấm nhìn từ dưới lên, thấy cụm tiếp điểm. Thấy được tiếp điểm có đen, rỉ, hay cháy
không.

Ảnh đế cắm điện. Cùng lý do, và có ích để loại nhánh tiếp điểm bẩn.

Ảnh dây nguồn và phích cắm. Chân phích đen là dấu hiệu tiếp xúc kém.

Ảnh nhựa quanh đáy ấm. Biến dạng hoặc ố vàng là dấu hiệu đã quá nhiệt.

Ảnh tem thông số dưới đáy. Cho biết model, công suất, và đôi khi năm sản xuất, và cái cuối
có ích cho câu hỏi bảo hành.

**Không xin ảnh bên trong đáy ấm**, vì để chụp được thì khách phải mở ra, và đó là việc không
nên làm.

## Lẫn với bệnh nào

**KETTLE_SWITCH.** Cặp phải tách đầu tiên và tách bằng đèn báo.

Đèn không sáng và công tắc không giữ: nhánh công tắc, và nó rẻ hơn nhiều.

Đèn sáng mà không nóng: mã này.

**KETTLE_SCALE.** Cặp quan trọng nhất về mặt kinh tế.

Cặn vôi làm đun chậm, và khách báo là "mâm yếu". Nhưng mâm không yếu dần, nên đun chậm gần
như luôn là cặn.

Nhầm hướng này tốn kém rõ ràng: khách bỏ một cái ấm chỉ cần ngâm giấm một buổi.

Vì vậy với triệu chứng đun chậm, **luôn hỏi về cặn trước khi nói bất cứ điều gì về mâm
nhiệt**.

**KETTLE_THERMOSTAT.** Nếu ấm tắt sớm rồi không bật lại, thì có thể là rơ le chống cạn chứ
không phải mâm đứt. Tách bằng việc để nguội hoàn toàn rồi thử lại.

Có một nhánh không thuộc bệnh nào: **đèn báo hỏng riêng**. Ấm vẫn nóng bình thường nhưng đèn
không sáng. Đáng loại bằng cách hỏi nước có nóng không, chứ đừng kết luận từ mỗi cái đèn.

## Phòng cho cái ấm tiếp theo

Phần này đáng nói kỹ vì khách sắp mua ấm mới, và phần lớn ca của mã này phòng được.

**Đừng bật ấm khi chưa có nước.** Nguyên nhân dẫn tới mã này nhiều nhất.

Thành thói quen: nhìn vào ấm hoặc nhấc thử xem có nặng không, trước khi gạt công tắc.

**Đừng đun ít hơn vạch tối thiểu.** Nước ít thì mâm nóng nhanh hơn mức thiết kế, và rơ le
chống cạn phải làm việc thường xuyên.

**Tẩy cặn định kỳ.** Cặn dày làm mâm chạy quá nhiệt mỗi lần đun, suốt nhiều năm. Đây là con
đường chậm dẫn tới mã này.

**Đừng cạo cặn bằng vật cứng.**

**Đừng đun liên tục nhiều mẻ sát nhau.** Cho ấm nghỉ giữa các lần.

**Đừng đặt ấm lên bếp nóng hoặc gần bếp.**

**Cắm ấm vào ổ riêng**, vì sụt áp làm ấm đun lâu hơn và làm mâm làm việc lâu hơn mỗi lần.

**Đổ hết nước thừa sau mỗi lần đun**, vì nó giảm cặn.

## Kịch bản mẫu

Khách nhắn "ấm không nóng". Hỏi bốn thứ miễn phí trước, rồi hỏi câu về đèn báo.

Khách nhắn "đèn sáng mà nước lạnh ngắt". Đã tách xong. Hỏi ấm có từng bị đun cạn không, rồi
nói thẳng về phép tính.

Khách nhắn "ấm đun mãi không sôi". Không phải mã này. Hỏi đáy ấm có lớp trắng dày không, và
hướng dẫn tẩy cặn.

Khách nhắn "cắm vào không thấy gì, đèn cũng không sáng". Nhánh khác. Gợi ý thử ổ cắm, đặt
lại ấm cho khớp, và lau tiếp điểm.

Khách nhắn "hôm qua bật quên đổ nước, giờ không lên". Nhánh đun cạn. Gợi ý để nguội hoàn
toàn vài giờ rồi thử lại, vì có loại rơ le tự phục hồi.

Khách nhắn "để qua đêm rồi vẫn không lên". Nghiêng về mâm đứt hoặc rơ le hỏng vĩnh viễn. Nói
thẳng về phép tính và hỏi ấm mua lâu chưa.

Khách nhắn "thay mâm nhiệt được không". Nói đủ ba lý do nên thay ấm, và nêu ngoại lệ bảo
hành cùng ngoại lệ ấm loại đắt.

Khách nhắn "mới mua tháng trước thôi". Hỏi có còn hoá đơn không, và hướng dẫn liên hệ nơi
mua trước khi tính gì khác.

## Nền tri thức của tài liệu này

Toàn bộ nội dung được viết lại bằng lời của dự án, không sao chép nguyên văn từ nguồn
nào.

Cấu tạo mâm nhiệt với dây điện trở đúc kín, và đặc điểm dây điện trở hoặc còn nguyên hoặc
đứt hẳn chứ không suy giảm dần: nội dung mô đun thực hành thiết bị gia dụng trong chương
trình đào tạo nghề, đối chiếu tài liệu kỹ thuật của các hãng có mặt tại Việt Nam.

Vai trò rơ le chống cạn đặt sát mâm nhiệt, và việc một số loại tự phục hồi sau khi nguội
hẳn còn một số loại cắt vĩnh viễn: tài liệu kỹ thuật của nhà sản xuất.

Cơ chế mỏi và đứt của dây điện trở sau nhiều chu kỳ giãn nở nhiệt: kiến thức vật liệu phổ
thông.

Hiện tượng lớp cặn vôi cách nhiệt làm mâm chạy ở nhiệt độ cao hơn thiết kế, và hệ quả là
đun chậm: kiến thức truyền nhiệt phổ thông.

Ảnh hưởng của việc đun cạn tới dây điện trở, rơ le và gioăng, ở ba mốc thời gian khác nhau:
kinh nghiệm nghề của thợ sửa đồ điện gia dụng trong nước.

Yêu cầu an toàn với thiết bị đun chất lỏng dùng trong gia đình, gồm cơ cấu bảo vệ chống chạy
khô và cách ly giữa phần mang điện với phần chứa nước: tham chiếu TCVN 5699-1 về an toàn
thiết bị điện gia dụng. Cần cập nhật khi hệ thống chạy thật.

## Chỗ cần thợ xác nhận

Mâm nhiệt hỏng hay chỉ mất điện tới nó. Cần đo để tách.

Rơ le chống cạn có hỏng ở trạng thái cắt không, và trên model đó nó có thay riêng được
không.

Cụm tiếp điểm ở đáy ấm và ở đế có còn tốt không.

Gioăng quanh mâm còn kín không, nếu ấm đã từng bị đun cạn.

Ấm còn hạn bảo hành không.

Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
