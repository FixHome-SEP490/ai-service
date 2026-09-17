---
doc_id: KB_FAULT_OUTLET_NO_POWER
doc_type: fault
device_type: power_outlet
fault_code: OUTLET_NO_POWER
name_vi: Ổ cắm mất điện, đứt dây
urgency: MEDIUM
confusable_with: [OUTLET_LOOSE_CONTACT, OUTLET_TRIPS_BREAKER, OUTLET_SHORT_CIRCUIT]
price_policy: Không ghi giá trong tài liệu này. Giá lấy từ bảng giá của hệ thống.
last_reviewed: 2026-09-17
needs_technician_review:
  - Vị trí điểm đứt trên đường dây
---

# Ổ cắm mất điện, đứt dây

## Bệnh có nhiều nhánh miễn phí nhất của cụm điện

Trong cụm ổ cắm, đây là mã hiền nhất: không cháy, không giật, không có gì đang xấu đi.
Chỉ là một cái ổ không có điện.

Và nó là mã có tỷ lệ tự xử lý cao nhất của cụm, vì phần lớn ca không phải ổ cắm hỏng.

Aptomat nhánh đã nhảy mà không ai để ý. Một công tắc nào đó đang tắt. Cả nhánh mất điện.
Hoặc thiết bị đang cắm vào mới là cái hỏng.

Bốn nhánh đó chiếm phần lớn số ca, và cả bốn khách tự kiểm được trong vài phút.

Vì vậy thứ tự trả lời rất rõ: **mở rộng ra trước, thu hẹp vào sau**. Đừng bắt đầu bằng
việc chẩn đoán cái ổ.

Có một chỗ cần cẩn thận dù mã này hiền: nếu khách kể là ổ mất điện **sau khi có tiếng nổ,
có mùi khét, hoặc sau khi thấy tia lửa**, thì đây không còn là mã này. Đó là
OUTLET_SHORT_CIRCUIT và xử lý theo mức khẩn.

## Năm việc kiểm tra, theo thứ tự

**Một, thử một thiết bị khác vào ổ đó.** Ba mươi giây. Nó tách nhánh thiết bị hỏng ra
khỏi nhánh ổ hỏng, và nhánh thiết bị thì phổ biến hơn người ta tưởng.

**Hai, thử thiết bị đó vào một ổ khác.** Chiều ngược lại, cùng mục đích. Nếu nó cũng
không chạy ở ổ khác thì vấn đề ở thiết bị.

**Ba, các ổ khác trong phòng có điện không, đèn có sáng không.** Nó tách một ổ hỏng với
cả nhánh mất điện.

**Bốn, kiểm tra tủ aptomat.** Có aptomat nào đang ở vị trí nhảy không. Đây là nhánh rất
phổ biến, nhất là khi aptomat nhảy lúc không ai ở nhà.

**Năm, có công tắc nào điều khiển ổ đó không.** Ở một số nhà, ổ cắm được nối qua một công
tắc trên tường. Người trong nhà tắt rồi quên, hoặc dọn dẹp chạm phải.

Năm việc đó mất năm phút và chúng loại được phần lớn ca. Chỉ khi cả năm đều ổn thì vấn đề
mới nằm ở ổ cắm hoặc ở đường dây.

## Nhánh aptomat nhảy mà không ai biết

Đáng tách riêng vì nó rất phổ biến và vì nó có một đặc điểm gây nhầm.

Aptomat nhảy khi không ai ở nhà, hoặc nhảy ban đêm. Sáng ra khách thấy một vài ổ mất
điện, tủ lạnh ngừng chạy, và không hiểu vì sao.

Đặc điểm gây nhầm: **một số aptomat khi nhảy không xuống hẳn mà dừng ở giữa**, nên nhìn
qua thì tưởng vẫn đang bật.

Cách kiểm đúng: gạt hẳn xuống vị trí tắt trước, rồi mới gạt lên. Chỉ gạt lên thẳng từ vị
trí giữa thì có khi không đóng lại được.

Và có một câu phải kèm theo: **aptomat nhảy là nó phát hiện ra gì đó**. Nếu gạt lên mà nó
nhảy lại thì dừng, đừng gạt tiếp, và chuyển sang OUTLET_TRIPS_BREAKER.

Nếu gạt lên và nó giữ được bình thường thì có thể chỉ là một lần quá tải thoáng qua, và
đáng hỏi xem lúc đó nhà đang chạy những gì.

Nhánh này là lý do câu hỏi về tủ aptomat nên nằm trong ba tin nhắn đầu của mọi ca mất
điện.

## Nhánh cả nhánh mất điện

Khi nhiều ổ cùng mất, và đèn cùng khu vực cũng không sáng.

Vấn đề không nằm ở một cái ổ mà ở đường dây chung, ở aptomat của nhánh, hoặc ở mối nối
trong một hộp điện nào đó.

Có một điểm rất đáng biết và nó giải thích nhiều ca trông như kỳ lạ: **các ổ cắm trong
một phòng thường được nối chuỗi với nhau**. Dây đi từ tủ điện tới ổ thứ nhất, rồi từ ổ
thứ nhất sang ổ thứ hai, rồi sang ổ thứ ba.

Nghĩa là nếu mối nối ở ổ thứ nhất lỏng hoặc đứt, thì ổ thứ nhất vẫn có điện nhưng **mọi ổ
sau nó đều mất**.

Hệ quả thực tế: khi khách báo là mấy ổ liền nhau cùng mất, nên hỏi **ổ nào còn dùng
được**. Cái ổ cuối cùng còn điện thường là nơi có mối nối hỏng, hoặc ngay sau nó.

Đây là thông tin có ích thật cho thợ, và nó rút ngắn việc tìm kiếm đáng kể.

## Nhánh đứt dây trong tường

Ít gặp nhất nhưng là nhánh mà khách lo nhất, vì họ sợ phải đục tường.

Nguyên nhân:

**Đóng đinh hoặc khoan trúng dây.** Khi treo tranh, lắp kệ, lắp máy lạnh. Dấu hiệu rất
rõ: mất điện đúng sau khi ai đó khoan tường, và khách thường nhớ.

**Chuột cắn**, ở đoạn dây đi qua trần hoặc qua hộp kỹ thuật.

**Dây lão hoá**, ở nhà rất cũ. Lớp cách điện giòn và lõi đồng gãy tại chỗ uốn.

**Thấm nước** làm mối nối trong tường ăn mòn rồi đứt.

Điều nên nói với khách để họ đỡ lo: **thợ không đục tường ngẫu nhiên**. Có thiết bị dò
đường dây và dò điểm đứt, và việc khoanh vùng thường làm được khá chính xác trước khi
đụng tới tường.

Và trong nhiều trường hợp, cách xử lý không phải là sửa chỗ đứt trong tường mà là **kéo
một đường dây mới đi nổi trong ống gen**, rồi bỏ đoạn dây cũ. Rẻ hơn, nhanh hơn, và sau
này dễ kiểm tra hơn.

Nêu lựa chọn đó ra là có ích, vì nhiều khách không biết là có cách đó.

## Nhánh mối nối trong hộp điện

Phổ biến hơn đứt dây nhiều, và rẻ hơn nhiều.

Trong nhà có các hộp nối, thường nằm âm tường hoặc trên trần, nơi các đoạn dây gặp nhau.
Mối nối ở đó có thể lỏng, oxy hoá, hoặc đứt.

Dấu hiệu: mất điện cả một nhóm ổ, hoặc mất điện chập chờn theo thời tiết, hoặc mất rồi tự
có lại.

Nhánh chập chờn theo thời tiết đáng chú ý: mối nối oxy hoá thì dẫn kém đi khi ẩm, và đôi
khi tự khá lên khi trời khô. Khách kể là điện lúc có lúc không mà không theo quy luật gì.

Đây cũng là nhánh có một cạnh nguy hiểm: **mối nối lỏng thì phát nhiệt**, và nó nằm trong
một hộp kín trong tường. Vì vậy ca mất điện chập chờn không hoàn toàn hiền, và nên xử lý
chứ đừng sống chung.

Nếu khách kể là mất điện chập chờn kèm mùi khét nhẹ ở đâu đó, thì chuyển sang mức khẩn.

## Nhánh lá tiếp xúc mòn hẳn

Khi cái ổ đúng là thủ phạm.

Lá tiếp xúc trong ổ mòn tới mức không còn chạm vào chân phích nữa, hoặc đã gãy.

Dấu hiệu tách rất rõ: **động vào phích thì có điện trở lại, lay lay thì nó chạy**. Điện
vẫn tới ổ, chỉ là không sang được phích.

Nếu đúng như vậy thì đây là giai đoạn cuối của OUTLET_LOOSE_CONTACT, và cần thay ổ.

Nếu ổ hoàn toàn không có điện dù lay thế nào, thì vấn đề nằm trước cái ổ chứ không phải ở
nó.

Câu hỏi tách: **"anh chị lay nhẹ cái phích xem có lúc nào nó chạy được không ạ?"**

Có thì là cái ổ. Không thì tìm tiếp về phía sau.

## Khách nói thế nào

"ổ cắm không có điện", "ổ cắm mất điện", "cắm vào không chạy", "ổ điện chết", "ổ cắm
không lên", "cả phòng mất điện", "mấy ổ liền nhau không có điện", "ổ cắm lúc có lúc
không", "tự nhiên mất điện một khu".

Không dấu: o cam khong co dien, o cam mat dien, cam vao khong chay, o dien chet, ca
phong mat dien, o cam luc co luc khong.

Cách nói khác: "cái ổ này chết rồi", "cắm gì vào cũng không ăn", "ổ cắm không ra điện",
"chỗ này không có điện".

Chú ý một chỗ: **"mất điện" ở miền Nam đôi khi nghĩa là aptomat nhảy chứ không phải điện
lưới mất**. Và ngược lại, có khách nói "cúp điện" khi thực ra chỉ một ổ hỏng.

Câu hỏi tách luôn nên có sớm: **"là mất cả nhà, mất một phòng, hay chỉ một cái ổ ạ? Hàng
xóm có mất không?"**

Câu đó định vị phạm vi trong một lần hỏi, và nó quyết định toàn bộ hướng đi sau đó.

## Đọc ảnh

Ảnh tủ aptomat chụp thẳng. Ảnh có giá trị cao nhất của mã này. Thấy được aptomat nào đang
nhảy, kể cả loại nhảy dừng ở giữa mà nhìn qua tưởng vẫn bật.

Ảnh chụp gần cái aptomat nghi ngờ. Vị trí cần gạt thì rõ hơn.

Ảnh mặt ổ cắm. Thấy được có vết đen không, có ố vàng không. Nếu có thì đây không phải mã
này mà là nhánh chập.

Ảnh các ổ cắm trong phòng, để biết cái nào còn điện và cái nào không. Thứ tự đó có ích
cho việc tìm mối nối hỏng.

Ảnh tường có vệt ẩm gần khu vực mất điện. Nhánh thấm nước.

Ảnh chỗ vừa khoan hoặc vừa đóng đinh gần đó. Nhánh đứt dây do khoan, và khách thường nhớ
việc này khi được nhắc.

Ảnh ổ cắm lỏng khỏi tường hoặc mặt ổ kênh ra.

Không bảo khách mở mặt ổ hay mở nắp hộp điện để chụp bên trong.

## Lẫn với bệnh nào

**OUTLET_LOOSE_CONTACT.** Là giai đoạn trước của một trong các nhánh. Tách bằng việc lay
phích có ăn lại không.

**OUTLET_TRIPS_BREAKER.** Nếu nguyên nhân là aptomat nhảy, thì câu hỏi tiếp theo là vì sao
nó nhảy, và đó là mã kia. Gạt lên mà nó nhảy lại thì chuyển hẳn sang đó.

**OUTLET_SHORT_CIRCUIT.** Nếu ổ mất điện sau một tiếng nổ, một tia lửa, hoặc kèm mùi khét
và vết đen, thì đây là hậu quả của chập chứ không phải mã này. Xử lý theo mức khẩn.

Có một nhánh không thuộc bệnh nào và đáng loại trừ trong câu hỏi đầu tiên: **mất điện
lưới**. Hỏi hàng xóm có mất không.

Và một nhánh nữa rất hay gặp ở nhà trọ và chung cư: **công tơ hoặc aptomat tổng của căn
hộ bị cắt**, vì lý do hành chính hoặc vì quá hạn. Đáng hỏi nhẹ nhàng nếu mất điện cả nhà
mà hàng xóm thì không.

## Sửa hay thay

Chi phí của mã này phụ thuộc hoàn toàn vào việc điểm hỏng nằm ở đâu, và nó trải rất rộng.

**Aptomat nhảy:** không tốn gì. Gạt lại và tìm hiểu vì sao.

**Công tắc đang tắt:** không tốn gì.

**Lá tiếp xúc mòn:** thay ổ. Rẻ nhất trong nhóm cần thợ.

**Mối nối trong ổ hoặc trong hộp điện lỏng:** nối lại và siết. Rẻ, và phổ biến.

**Đứt dây trong tường:** đắt nhất trong nhóm, vì phải dò tìm và phải xử lý đường dây. Nhưng
thường vẫn không đắt như khách sợ, nhất là khi chọn phương án kéo dây mới đi nổi.

Vì khoảng trải rộng như vậy, **đừng báo giá trước khi biết điểm hỏng ở đâu**. Nói cấu trúc
của phép tính là đủ: có mấy nhánh, phần lớn thì rẻ, một nhánh thì tốn hơn, và thợ cần dò
mới biết.

Một điểm nên nói khi nghi đứt dây ở nhà cũ: nếu dây đã lão hoá thì sửa một chỗ hôm nay
không ngăn được chỗ khác đứt sang năm. Với nhà rất cũ, đáng cân nhắc kéo lại cả nhánh.

## Phòng cho lần sau

Ghi nhãn cho tủ aptomat. Việc mất nửa tiếng một lần và nó tiết kiệm rất nhiều lần về sau,
kể cả trong các tình huống khẩn khi cần cắt đúng nhánh thật nhanh.

Trước khi khoan hoặc đóng đinh vào tường, dùng máy dò đường dây, hoặc tránh các vùng
thẳng hàng phía trên và phía dưới ổ cắm và công tắc. Dây thường đi thẳng đứng từ ổ lên
hoặc xuống.

Xử lý sớm khi một ổ bắt đầu chập chờn, vì mối nối lỏng thì vừa gây mất điện vừa phát
nhiệt.

Chống thấm cho tường có đường dây đi qua.

Kiểm tra và siết lại mối nối trong các hộp điện, vài năm một lần.

Ở nhà có chuột, kiểm tra các đoạn dây đi qua trần và qua hộp kỹ thuật.

## Kịch bản mẫu

Khách nhắn "ổ cắm không có điện". Hỏi phạm vi trước: một ổ, một phòng, hay cả nhà, và
hàng xóm có mất không. Rồi hướng dẫn năm việc kiểm tra.

Khách nhắn "cả phòng không có điện". Hỏi ngay về tủ aptomat, vì đó là nhánh phổ biến nhất.
Nhắc cách gạt đúng: xuống hẳn rồi mới lên.

Khách nhắn "gạt aptomat lên nó lại nhảy". Dừng, đừng gạt tiếp. Chuyển sang mã rò điện.

Khách nhắn "mấy ổ liền nhau mất điện, ổ đầu thì còn". Nhánh mối nối chuỗi. Nói rõ điểm
hỏng thường ở ngay sau cái ổ cuối cùng còn điện, và thông tin đó rút ngắn việc tìm.

Khách nhắn "lay cái phích thì nó chạy". Nhánh lá tiếp xúc mòn. Thay ổ, và nói rõ đây là
nhánh rẻ.

Khách nhắn "hôm qua khoan tường xong mất điện một khu". Nhánh khoan trúng dây. Nói rõ thợ
có thiết bị dò và không đục tường ngẫu nhiên, và nêu phương án kéo dây mới đi nổi.

Khách nhắn "điện lúc có lúc không, trời mưa thì hay mất". Nhánh mối nối ẩm. Nói rõ nên
xử lý chứ đừng sống chung, vì mối nối lỏng thì phát nhiệt.

Khách nhắn "ổ cắm mất điện sau khi nghe tiếng nổ". Không phải mã này. Chuyển sang cảnh
báo của mã chập.

## Nền tri thức của tài liệu này

Toàn bộ nội dung được viết lại bằng lời của dự án, không sao chép nguyên văn từ nguồn
nào.

Cách đi dây nối chuỗi các ổ cắm trong một phòng, và hệ quả là mối nối hỏng ở một ổ làm
mất điện mọi ổ phía sau: nội dung mô đun điện dân dụng trong chương trình đào tạo nghề,
cộng kinh nghiệm nghề của thợ điện trong nước.

Đặc điểm một số aptomat khi tác động dừng ở vị trí giữa, và cách gạt đúng: tài liệu kỹ
thuật của thiết bị đóng cắt.

Cơ chế mối nối oxy hoá dẫn điện kém đi khi độ ẩm tăng, và hiện tượng mất điện chập chờn
theo thời tiết: kiến thức vật liệu và điện phổ thông.

Yêu cầu về đi dây, hộp nối và bảo vệ trong hệ thống điện nhà ở: tham chiếu quy chuẩn kỹ
thuật quốc gia về hệ thống điện của nhà ở và công trình công cộng QCVN 12:2014/BXD.

Việc dây thường đi thẳng đứng từ ổ cắm và công tắc, cơ sở của lời khuyên tránh khoan
trúng: quy tắc đi dây thông dụng.

Phương án kéo dây mới đi nổi trong ống gen thay vì sửa đoạn đứt trong tường: kinh nghiệm
nghề của thợ điện dân dụng trong nước. Cần cập nhật khi hệ thống chạy thật.

## Chỗ cần thợ xác nhận

Vị trí điểm đứt hoặc điểm mất tiếp xúc trên đường dây. Cần dò bằng thiết bị.

Nguyên nhân aptomat nhảy, nếu đó là nhánh được xác định.

Mối nối trong các hộp điện còn chắc không.

Dây của nhánh đã lão hoá tới mức nào, ở nhà cũ, và có nên kéo lại cả nhánh không.

Có nên xử lý bằng cách kéo dây mới đi nổi thay vì đục tường không.

Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
