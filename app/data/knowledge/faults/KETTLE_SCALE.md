---
doc_id: KB_FAULT_KETTLE_SCALE
doc_type: fault
device_type: kettle
fault_code: KETTLE_SCALE
name_vi: Đóng cặn vôi trong bình
urgency: LOW
confusable_with: [KETTLE_HEATING_BASE, KETTLE_THERMOSTAT, PIPE_RUSTY_WATER]
price_policy: Không ghi giá trong tài liệu này. Giá lấy từ bảng giá của hệ thống.
last_reviewed: 2026-09-17
needs_technician_review:
  - Mâm nhiệt có bị hỏng lớp bảo vệ do cạo cặn không
---

# Đóng cặn vôi trong bình

## Bệnh nhẹ nhất của cụm, và là nguyên nhân của ba mã còn lại

Cặn vôi không làm hỏng gì ngay. Ấm vẫn đun, nước vẫn sôi, không nguy hiểm.

Vì vậy mã này ở mức ưu tiên thấp và khách coi nó là chuyện thẩm mỹ.

Nhưng nó là **nguyên nhân nền của phần lớn cụm ấm siêu tốc**, và đó là điều đáng nói rõ.

Lớp cặn bám trên mâm nhiệt cách nhiệt. Mâm vẫn phát nhiệt đúng như thiết kế, nhưng nhiệt
không truyền hết được vào nước.

Phần nhiệt không thoát đi đâu thì nằm lại ở chính cái mâm. Nghĩa là **mâm nhiệt chạy ở nhiệt
độ cao hơn mức nó được thiết kế cho, mỗi lần đun, suốt nhiều năm**.

Từ đó ra bốn hệ quả, và chúng ứng với bốn mã khác nhau:

Đun lâu hơn và tốn điện hơn.

Mâm nhiệt già nhanh, và cuối cùng là cháy.

Rơ le chống cạn cắt sớm vì mâm quá nóng, nên ấm tắt trước khi nước sôi.

Gioăng quanh mâm chịu nhiệt cao hơn nên chai nhanh, và cuối cùng là rò.

Nghĩa là tẩy cặn không phải việc dọn dẹp. Nó là việc bảo dưỡng có ảnh hưởng thật tới tuổi
thọ của cái ấm.

## Cặn vôi từ đâu ra

Nước máy và nước giếng ở nhiều khu vực chứa khoáng hoà tan, chủ yếu là các muối canxi và
magiê. Nước chứa nhiều khoáng như vậy gọi là nước cứng.

Ở nhiệt độ thường, các khoáng đó tan trong nước và không nhìn thấy được.

Khi đun sôi, chúng kết tủa ra khỏi nước và bám vào bề mặt nóng nhất, tức là mâm nhiệt.

Ba điều đáng nói với khách từ đó:

**Cặn không phải bẩn.** Nó là khoáng có sẵn trong nước, và nó không độc. Khách hay lo chuyện
này.

**Nước càng cứng thì cặn càng nhanh.** Cùng một cái ấm, ở nhà này hai tháng đã trắng đáy,
ở nhà khác cả năm vẫn sạch.

**Lọc nước thông thường không loại được nó.** Lọc thô giữ cặn lơ lửng và rỉ, nhưng khoáng
hoà tan thì đi qua. Chỉ vài loại lọc chuyên dụng mới làm được, và chúng đắt hơn nhiều.

Vì vậy với nhà ở khu vực nước cứng, câu trả lời thực tế không phải là ngăn cặn hình thành,
mà là **tẩy nó định kỳ trước khi nó dày**.

## Tẩy cặn bằng giấm: cách chuẩn

Phần có giá trị nhất của tài liệu này, và khách tự làm hoàn toàn.

**Đổ giấm vào ấm, pha với nước theo tỷ lệ khoảng một phần giấm hai phần nước.** Đủ để ngập
hết lớp cặn.

Nếu cặn dày thì dùng giấm đặc hơn.

**Đun sôi một lần**, rồi tắt.

**Để nguyên trong ấm ít nhất một giờ.** Cặn dày thì để qua đêm.

Thời gian ngâm quan trọng hơn nồng độ. Axit cần thời gian để phản ứng hết với lớp cặn.

**Đổ đi và rửa lại bằng nước sạch vài lần.** Rửa kỹ, vì mùi giấm bám lại.

**Đun sôi một lần nước sạch rồi đổ đi**, trước khi dùng lại bình thường.

**Lặp lại nếu cặn còn.** Lớp cặn dày nhiều năm có khi cần ba bốn lần.

Thay cho giấm, dùng được: **nước cốt chanh** pha loãng, hoặc **bột axit citric** bán sẵn.

Bột axit citric là loại chuyên dùng cho việc này và nó không để lại mùi, nên nếu nhà có sẵn
thì tiện hơn giấm.

## Ba việc không nên làm khi tẩy cặn

Ba việc này khách sẽ tự nghĩ ra, và cả ba đều làm hỏng cái ấm.

**Đừng cạo cặn bằng dao, thìa kim loại, hay vật cứng.**

Mâm nhiệt có một lớp bề mặt bảo vệ. Cạo làm xước lớp đó, và chỗ xước thì vừa bám cặn nhanh
hơn vừa là điểm bắt đầu ăn mòn.

Nặng hơn: cạo mạnh có thể làm hỏng lớp kín giữa mâm nhiệt và phần điện bên dưới, và đó là
con đường dẫn thẳng tới KETTLE_LEAK, một mã ưu tiên cao.

Nghĩa là **cạo cặn có thể biến một bệnh nhẹ nhất thành bệnh nguy hiểm nhất của cụm**.

Đây là điều đáng nói chủ động, vì cạo là việc rất trực giác khi nhìn thấy một lớp trắng bám
chặt.

**Đừng dùng bùi nhùi thép.** Cùng lý do, và thêm một lý do nữa: mảnh thép bám lại trên mâm
rồi rỉ.

**Đừng dùng hoá chất tẩy mạnh**, kể cả loại tẩy nhà vệ sinh. Cái ấm này đun nước để uống,
và không có cách nào chắc chắn rửa sạch hết dư lượng. Giấm và chanh thì ăn được nên không
có vấn đề đó.

## Nhận ra cặn ở mức nào

Có ích để định vị và để biết có ảnh hưởng gì chưa.

**Mức một: lớp màng mỏng, hơi mờ, thấy khi nhìn nghiêng.** Bình thường. Chưa ảnh hưởng gì.

**Mức hai: lớp trắng nhìn rõ nhưng còn thấy được mặt kim loại bên dưới.** Đây là lúc tẩy lý
tưởng, vì một lần ngâm giấm là sạch.

**Mức ba: lớp trắng dày, sần, phủ kín đáy.** Bắt đầu ảnh hưởng: đun lâu hơn.

**Mức bốn: cặn bong ra thành mảng trôi trong nước.** Khách hay lo ở mức này, vì họ thấy
"cái gì trắng trắng" trong cốc nước.

Trấn an được: đó là khoáng, không độc. Nhưng nó là dấu hiệu nên tẩy.

**Mức năm: ấm tắt trước khi sôi, hoặc không tự tắt.** Cặn đã ảnh hưởng tới rơ le, và bệnh
đã lan sang mã khác.

**Mức sáu: ấm không nóng nữa.** Mâm nhiệt đã cháy sau nhiều năm chạy quá nhiệt.

Câu hỏi định vị: **"anh chị nhìn xuống đáy ấm xem lớp trắng dày tới mức nào, còn thấy mặt
kim loại không ạ?"**

## Nhánh cặn lơ lửng trong nước

Nhánh khách hay hỏi và nó cần được trả lời cho đúng, vì nó liên quan tới thứ người ta uống.

Khách kể: rót nước ra thấy có mảnh trắng lơ lửng, hoặc có lớp cặn lắng dưới đáy cốc.

**Nếu là mảnh trắng, mỏng, dễ vỡ, lắng xuống đáy cốc:** đó là cặn vôi bong ra từ mâm nhiệt.
Không độc, và nó là dấu hiệu nên tẩy cặn.

**Nếu là lớp váng mỏng nổi trên mặt nước, óng ánh:** cũng là khoáng, và cũng vô hại. Nó hay
xuất hiện ở nước cứng khi để nguội.

**Nếu là cặn màu nâu đỏ:** không phải cặn vôi. Đó là rỉ sét, và nó đến từ đường ống chứ
không từ cái ấm. Nhánh này dẫn sang PIPE_RUSTY_WATER.

Tách bằng màu: trắng là khoáng từ nước cứng; nâu đỏ là rỉ từ ống.

**Nếu nước có mùi hoặc vị lạ:** cần tách. Mùi nhựa thường từ ấm mới, và nó hết sau vài lần
đun rồi đổ đi. Mùi khác thì có thể từ nguồn nước, và hệ thống này không kết luận được về
chất lượng nước uống.

Với nhánh cuối, nói rõ giới hạn: cần xét nghiệm nước mới biết, và đó không phải việc đoán
từ mô tả.

## Vì sao ấm tắt trước khi nước sôi

Nhánh nối mã này với KETTLE_THERMOSTAT, và nó là hệ quả trực tiếp của cặn.

Sát mâm nhiệt có một rơ le chống cạn. Việc của nó là cắt điện nếu mâm quá nóng, để bảo vệ
ấm khi ai đó bật nhầm lúc không có nước.

Khi mâm bị cặn phủ, nhiệt không truyền hết vào nước nên chính cái mâm nóng hơn bình thường.

Nếu nó vượt ngưỡng, rơ le chống cạn cắt, dù trong ấm vẫn đầy nước và nước chưa sôi.

Triệu chứng khách thấy: **ấm tự tắt sau một hai phút, nước mới âm ấm**.

Rất đặc trưng, và nó gần như chốt được nhánh cặn nếu đáy ấm có lớp trắng dày.

Cách xử lý: tẩy cặn. Không cần sửa gì.

Nếu tẩy cặn xong mà vẫn tắt sớm, thì rơ le đã yếu thật, và nhánh chuyển sang
KETTLE_THERMOSTAT.

Nhánh này đáng biết vì nếu không hiểu cơ chế thì khách sẽ nghĩ ấm hỏng và đi mua ấm mới,
trong khi việc cần làm là một buổi ngâm giấm.

## Vì sao cặn làm ấm không tự tắt

Hệ quả thứ hai, và nó đi theo hướng ngược lại.

Rơ le nhiệt không đo nhiệt độ nước. Nó cảm nhận hơi nước bốc lên qua một đường dẫn nhỏ trong
thân hoặc trong tay cầm.

Đường dẫn đó cũng bị cặn vôi bám, vì hơi nước mang theo khoáng.

Khi nó bít, hơi không tới được rơ le, và ấm không biết là nước đã sôi. Nó tiếp tục đun cho
tới khi nước cạn và rơ le chống cạn cắt.

Triệu chứng: **ấm sôi ùng ục mà công tắc không bật lên**.

Cách xử lý: tẩy cặn, và trong lúc ngâm giấm thì nghiêng ấm qua lại để giấm vào được đường
dẫn hơi.

Chi tiết cuối đáng nói vì nó không hiển nhiên: ngâm bình thường thì giấm chỉ ở đáy, còn
đường dẫn hơi thì ở phía trên.

Nếu tẩy xong vẫn không tự tắt, thì kiểm tra nắp đóng kín chưa trước khi nghĩ tới rơ le hỏng.

## Bao lâu tẩy một lần

Không có con số chung, và nói thật điều đó tốt hơn là đưa một con số sai.

Nó phụ thuộc vào ba thứ:

**Độ cứng của nước ở khu vực đó.** Chênh nhau rất nhiều giữa các nơi.

**Số lần đun mỗi ngày.** Ấm văn phòng đun hai chục lần một ngày thì đóng cặn nhanh gấp
nhiều lần ấm gia đình.

**Nguồn nước.** Nước giếng thường cứng hơn nước máy.

Vì vậy cách thực tế nhất là **nhìn**: cứ thấy lớp trắng bắt đầu dày lên rõ rệt thì tẩy.

Với nhà ở khu vực nước cứng và dùng nhiều, có khi hằng tháng. Với nhà nước mềm và dùng ít,
có khi vài tháng một lần.

Nguyên tắc đáng nói: **tẩy khi còn mỏng thì một lần ngâm là sạch; để dày thì phải làm nhiều
lần và có khi không sạch hết**.

Và nó rẻ hơn theo nghĩa khác: ấm không phải chạy quá nhiệt trong suốt thời gian đó.

## Nhánh không phải cặn vôi

Đáng tách vì có mấy thứ trông giống.

**Vết ố vàng hoặc nâu ở đáy ấm inox.** Có thể là rỉ do nước có sắt, hoặc do một vật kim loại
để trong ấm.

Thử bằng giấm: cặn vôi tan; rỉ thì không.

**Lớp màng nhờn ở lòng ấm.** Thường do đổ nước chưa sạch, hoặc do ấm dùng đun thứ khác ngoài
nước.

**Vết đen hoặc vết cháy trên mâm nhiệt.** Không phải cặn. Đó là dấu hiệu mâm đã bị quá
nhiệt, thường sau khi bị đun cạn. Cần chú ý vì nó liên quan tới an toàn.

**Nhựa thân ấm ố vàng.** Lão hoá vì nhiệt, không phải cặn, và không tẩy được.

Câu hỏi tách: lớp đó có màu gì, và ngâm giấm có tan không.

## Khách nói thế nào

"ấm bị đóng cặn", "đáy ấm có lớp trắng", "ấm siêu tốc bị cáu cặn", "nước có cặn trắng", "đun
nước thấy có sạn", "đáy ấm bị vôi", "ấm đun lâu hơn trước", "ấm tắt trước khi sôi", "nước có
mảng trắng nổi lên".

Không dấu: am bi dong can, day am co lop trang, am sieu toc bi cau can, nuoc co can trang,
day am bi voi, am dun lau hon truoc.

Cách nói khác: "đáy ấm trắng xoá", "ấm bị đóng vôi", "có cái gì trăng trắng trong nước",
"ấm nhà em bị ố đáy".

Câu "có cái gì trăng trắng trong nước" là câu khách lo nhất, và nó cần được trấn an sớm:
đó là khoáng, không độc.

Câu "ấm đun lâu hơn trước" đáng nhận ra vì khách kể nó như chuyện riêng, không nối với lớp
cặn. Hỏi một câu về đáy ấm là nối được hai chuyện.

## Đọc ảnh

Ảnh bên trong lòng ấm, chụp thẳng xuống đáy. Ảnh quyết định của mã này.

Thấy được lớp cặn dày tới đâu, có còn nhìn thấy mặt kim loại không, và cặn có màu gì.

Ảnh chụp nghiêng để thấy độ dày. Từ trên xuống thì khó ước.

Ảnh sau khi đã tẩy một lần. Cho biết cần làm thêm không.

Ảnh cốc nước có cặn lắng. Cho biết màu, và màu tách được cặn vôi với rỉ sét.

Ảnh mâm nhiệt có vết đen hoặc vết cháy. Không phải cặn, và nó là dấu hiệu khác cần chú ý.

Ảnh mâm nhiệt có vết xước hoặc vết cạo. Nếu thấy thì có một việc cần nói: đừng cạo nữa, và
lớp bảo vệ có thể đã hỏng.

Ảnh đáy ấm nhìn từ dưới, nếu nghi đã có rò. Vì cạo cặn mạnh có thể dẫn tới đó.

## Lẫn với bệnh nào

**KETTLE_THERMOSTAT.** Không phải nhầm mà là quan hệ nhân quả theo cả hai hướng: cặn làm
ấm tắt sớm, và cặn bít đường dẫn hơi làm ấm không tự tắt.

Nếu khách báo một trong hai triệu chứng đó, việc đầu tiên nên hỏi là về lớp cặn, chứ không
phải kết luận rơ le hỏng.

**KETTLE_HEATING_BASE.** Cũng nhân quả: cặn dày làm mâm chạy quá nhiệt nhiều năm và cuối
cùng là cháy.

Nếu ấm không nóng nữa và đáy đầy cặn, thì cặn là nguyên nhân gốc chứ không phải chuyện phụ.

**KETTLE_LEAK.** Liên hệ qua việc cạo cặn: cạo bằng vật cứng làm hỏng lớp bảo vệ và có thể
dẫn tới rò.

Nếu khách kể là đã cạo cặn bằng dao, thì đáng hỏi thêm về nước ở đáy ấm.

**PIPE_RUSTY_WATER.** Tách bằng màu: cặn trắng là khoáng từ nước cứng, cặn nâu đỏ là rỉ từ
đường ống.

Nhánh rỉ thì không phải chuyện của cái ấm, và nó có thể ảnh hưởng tới cả nhà.

## Sửa hay thay

Mã này gần như không có chi phí, và nên nói rõ vì nó là tin tốt.

**Tẩy cặn:** khách tự làm, tốn một chai giấm.

Không có chi tiết nào để thay, không cần thợ, không cần mua gì đặc biệt.

**Thay ấm** chỉ khi cặn đã dẫn tới hậu quả: mâm nhiệt đã cháy, hoặc ấm đã rò, hoặc rơ le đã
hỏng thật.

Và khi đó thì bệnh không còn là mã này nữa.

Có một điểm đáng nói khi khách hỏi có nên mua ấm khác cho đỡ đóng cặn: **mọi ấm đều đóng cặn
như nhau ở cùng một nguồn nước**. Không có loại ấm nào chống được, vì cặn đến từ nước chứ
không từ cái ấm.

Điều duy nhất khác nhau là **mâm nhiệt phẳng dễ tẩy hơn mâm nhiệt dạng ống lộ**, vì ống lộ
có nhiều khe và cặn bám quanh khó ra.

Đó là thông tin có ích khi khách sắp mua ấm mới, và nó không phải cách bán hàng.

## Phòng cho lần sau

**Tẩy định kỳ, đừng đợi dày.** Lời khuyên có tác dụng nhất, và nó vừa dễ hơn vừa bảo vệ mâm
nhiệt.

**Đổ hết nước thừa sau mỗi lần đun.** Nước để lại trong ấm bay hơi dần và để lại toàn bộ
khoáng của nó. Đun bao nhiêu thì dùng bấy nhiêu.

Đây là thói quen ít ai nghĩ tới và nó giảm đáng kể tốc độ đóng cặn.

**Tráng ấm bằng nước sạch sau mỗi lần dùng**, nếu tiện.

**Dùng nước đã lọc** nếu nhà có hệ lọc phù hợp. Lọc thô không giúp, nhưng một số loại lọc
khác thì có.

**Đừng cạo cặn bằng vật cứng.** Nhắc lại vì nó quan trọng.

**Đừng đun lại nhiều lần cùng một mẻ nước.** Mỗi lần đun là một lần khoáng kết tủa thêm.

**Với ấm ở văn phòng hoặc ở quán:** tẩy dày hơn nhiều so với ấm gia đình, vì số lần đun gấp
nhiều lần.

## Kịch bản mẫu

Khách nhắn "đáy ấm có lớp trắng dày". Hướng dẫn tẩy bằng giấm đủ các bước, và nhắc đừng cạo.

Khách nhắn "nước có cặn trắng lơ lửng". Trấn an rằng đó là khoáng và không độc, rồi hướng
dẫn tẩy cặn.

Khách nhắn "ấm đun lâu hơn trước". Hỏi đáy ấm có lớp trắng không. Nếu có thì nối hai chuyện
và giải thích cơ chế cách nhiệt.

Khách nhắn "ấm tắt trước khi nước sôi". Hỏi về lớp cặn trước khi nghĩ tới rơ le. Nhánh cặn
chiếm phần lớn.

Khách nhắn "ấm sôi rồi mà không tự tắt". Hỏi nắp đóng kín chưa, rồi hỏi về cặn. Và nhắc
nghiêng ấm khi ngâm giấm để giấm vào được đường dẫn hơi.

Khách nhắn "em lấy dao cạo cho nhanh được không". Nói rõ là không, và nói lý do: nó làm hỏng
lớp bảo vệ và có thể dẫn tới rò nước vào phần điện.

Khách nhắn "cặn màu nâu đỏ". Không phải cặn vôi. Đó là rỉ từ đường ống, và nó là chuyện của
cả nhà chứ không của cái ấm.

Khách nhắn "mua ấm loại nào đỡ đóng cặn". Nói thật là mọi ấm đều như nhau ở cùng nguồn nước,
và điều khác biệt duy nhất là mâm phẳng dễ tẩy hơn mâm dạng ống.

## Nền tri thức của tài liệu này

Toàn bộ nội dung được viết lại bằng lời của dự án, không sao chép nguyên văn từ nguồn
nào.

Cơ chế các muối canxi và magiê hoà tan trong nước kết tủa khi đun sôi và bám vào bề mặt
nóng nhất: kiến thức hoá học về nước cứng.

Hiện tượng lớp cặn cách nhiệt làm bề mặt gia nhiệt chạy ở nhiệt độ cao hơn thiết kế: kiến
thức truyền nhiệt phổ thông, và là cơ sở giải thích cả bốn hệ quả.

Tác dụng của axit yếu trong giấm, nước chanh và axit citric với cặn vôi: hoá học phổ thông.

Nguyên lý rơ le chống cạn cắt khi mâm nhiệt vượt ngưỡng, và rơ le nhiệt cảm nhận hơi nước
qua đường dẫn: nội dung mô đun thực hành thiết bị gia dụng trong chương trình đào tạo nghề,
đối chiếu tài liệu kỹ thuật của các hãng có mặt tại Việt Nam.

Việc lọc thô không loại được khoáng hoà tan: kiến thức xử lý nước phổ thông.

Yêu cầu an toàn với thiết bị đun chất lỏng dùng trong gia đình: tham chiếu TCVN 5699-1 về an
toàn thiết bị điện gia dụng.

Rủi ro làm hỏng lớp bảo vệ của mâm nhiệt khi cạo cặn bằng vật cứng, và hệ quả dẫn tới rò:
kinh nghiệm nghề của thợ sửa đồ điện gia dụng trong nước. Cần cập nhật khi hệ thống chạy
thật.

## Chỗ cần thợ xác nhận

Mâm nhiệt có bị hỏng lớp bảo vệ do cạo cặn không, nếu khách đã từng cạo.

Mâm nhiệt còn nguyên không, nếu ấm đã đun lâu với lớp cặn dày trong nhiều năm.

Rơ le có còn tốt không, nếu tẩy cặn xong mà ấm vẫn tắt sớm hoặc vẫn không tự tắt.

Cặn màu bất thường đến từ nguồn nước hay từ chính cái ấm.

Chất lượng nước có vấn đề gì không, nếu nước có mùi hoặc vị lạ. Cần xét nghiệm, và hệ thống
này không kết luận được.

Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
