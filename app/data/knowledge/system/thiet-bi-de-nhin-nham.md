---
doc_id: KB_SYS_LOOKALIKE_DEVICES
doc_type: system
title_vi: Những thiết bị nhìn ảnh không phân biệt được, và cách hỏi lại
source: Ma trận nhầm lẫn của detector v1 đo trên tập test 22 lớp, docs/detector-v1-on-22class-test.json
last_reviewed: 2026-09-18
note: Danh sách cặp lấy từ số đo thật của mô hình, không phải phỏng đoán.
---

# Những thiết bị nhìn ảnh không phân biệt được

## Vì sao phải có tài liệu này

Mô hình nhận diện trả về đúng một cái tên, kèm một con số tin cậy. Nó không có
cách nào nói "tôi nghĩ là cái này, nhưng cũng có thể là cái kia". Nên khi ảnh
thật sự mơ hồ, nó vẫn trả về một cái tên nghe rất chắc chắn.

Đo trên tập test, detector nhầm lò nướng thành lò vi sóng **bảy lần**, nhầm
đường ống nước thành máy giặt **sáu lần** và thành vòi nước **sáu lần**, nhầm
bóng đèn thành bình nóng lạnh **bốn lần**. Đó không phải lỗi hiếm, đó là hình
dạng giống nhau.

Hậu quả không nằm ở cái tên. Nó nằm ở chỗ **hai thiết bị giống nhau trong ảnh
lại có lời khuyên an toàn khác hẳn nhau**. Một cái bếp từ được tư vấn như bếp
gas sẽ được dặn khoá van bình gas và mở cửa thông thoáng — lời khuyên vô nghĩa
cho một thiết bị cắm điện, và tệ hơn, nó làm khách tin rằng mình đã hiểu đúng
vấn đề.

Nên quy tắc là: **khi ảnh có thể là một trong hai, hỏi trước, đừng đoán**.

## Quy tắc chung, ba câu

Một, hỏi đúng **một** câu. Hỏi hai câu liên tiếp làm khách thấy như đang bị điều
tra, và phần lớn ca chỉ cần một câu là xong.

Hai, hỏi về **thứ khách nhìn thấy được**, đừng hỏi khách chọn nhãn. "Bên trong
lò có đĩa thuỷ tinh tròn xoay khi chạy không ạ?" là câu ai cũng trả lời được.
"Đây là lò vi sóng hay lò nướng ạ?" là trả lại cho khách đúng câu hỏi mà họ
không trả lời được — nếu họ phân biệt được thì đã không cần gửi ảnh.

Ba, **nếu khách đã nói rồi thì đừng hỏi**. Khách viết "máy giặt nhà em không
vắt" là đã trả lời xong câu hỏi máy giặt hay máy sấy. Hỏi lại là cách nhanh nhất
để khách thấy mình không được lắng nghe.

## Ngoại lệ của quy tắc thứ hai

Có một trường hợp được phép gọi thẳng tên thiết bị: **máy giặt, máy sấy quần áo
và máy rửa bát**.

Ba cái đó trong ảnh là cùng một vật — một hộp trắng có cửa. Nhưng không một
khách nào phân vân máy nhà mình dùng để giặt quần áo hay để rửa bát. Sự nhầm lẫn
ở đây hoàn toàn thuộc về tấm ảnh, không thuộc về khách. Nên hỏi thẳng là đúng và
nhanh nhất:

> Máy nhà mình là máy giặt, máy sấy quần áo, hay máy rửa bát ạ?

Trước đây câu hỏi ở đây là "máy có ngăn đổ bột giặt kéo ra được không". Câu đó
tách được máy giặt với máy sấy, nhưng **sai với máy rửa bát**: máy rửa bát đổ
viên rửa vào một hộc trong cánh cửa chứ không phải ngăn kéo, nên chủ máy trả lời
"không" và máy bị xếp thành máy sấy quần áo.

## Từng cặp, và dấu hiệu tách chúng ra

**Lò vi sóng và lò nướng.** Bên trong lò vi sóng có đĩa thuỷ tinh tròn xoay khi
chạy; lò nướng thì có khay và thanh nhiệt đỏ lên khi nóng. Đây là cặp detector
nhầm nhiều nhất.

**Máy giặt, máy sấy quần áo và máy rửa bát.** Hỏi máy dùng để làm gì, như trên.

**Quạt trần và quạt điện.** Hỏi quạt gắn cố định trên trần, hay quạt đứng dưới
sàn, treo tường. Lưu ý khách hay trả lời bằng cách phủ định: "không phải quạt
trần đâu ạ" là câu trả lời **quạt điện**, không phải quạt trần.

**Chậu rửa và vòi nước.** Hỏi chỗ đang hỏng là cái chậu và đường thoát bên dưới,
hay cái vòi. Cặp này khách thường mô tả lẫn lộn vì cả hai nằm cạnh nhau: "vòi
nước nhà em bị ứ" thường là tắc đường thoát của chậu chứ không phải vòi.

**Ổ cắm điện và bóng đèn.** Ảnh chụp gần một thiết bị điện gắn tường thì hai cái
này rất giống nhau. Hỏi chỗ đang hỏng là ổ cắm trên tường hay bóng đèn.

**Bếp gas và bếp từ.** Hỏi bếp nhà mình có dùng bình gas không. Cặp này quan
trọng hơn các cặp khác vì lời khuyên an toàn khác hẳn: bếp gas thì khoá van, mở
thoáng, không bật công tắc điện; bếp từ thì ngắt aptomat. Đưa nhầm lời khuyên
không chỉ vô ích mà còn làm khách yên tâm sai chỗ.

Chú ý khi đọc câu trả lời về bếp: **"nhà em có cắm điện" không có nghĩa là bếp
từ**. Bếp gas cũng cắm điện để đánh lửa. Dấu hiệu đáng tin là có ngọn lửa hay
không, và có bình gas hay không.

## Máy sấy quần áo không phải máy sấy tóc

Chữ "máy sấy" trong tiếng Việt là ít nhất bốn thứ: máy sấy quần áo, máy sấy tóc,
máy sấy bát và máy sấy giày. Trong hệ thống này **máy sấy nghĩa là máy sấy quần
áo** — loại có lồng quay, có lưới lọc xơ vải và ống thoát hơi, đúng loại mà dịch
vụ vệ sinh của bên mình làm.

Điều này quan trọng vì máy sấy quần áo tắc xơ vải là **nguy cơ cháy**, và tài
liệu của mã bệnh đó có cảnh báo bốn bước. Trả lời cảnh báo cháy đó cho một người
đang cầm cái máy sấy tóc là vừa sai vừa làm khách hoảng.

Hai thứ nữa hay bị gộp nhầm vào đây, và **không phải** máy sấy quần áo: **tủ sấy
quần áo** là cái khung vải có quạt thổi hơi nóng, và **giàn phơi** thì không có
điện. Cả hai đều không có lồng quay, không có lưới lọc xơ, và không thuộc dịch
vụ đang nói tới.

Nên khi khách nhắc tới "máy sấy" mà trong câu có "tóc", "tủ sấy", "giàn phơi",
"bát", "giày" thì đó không phải thiết bị của mình.

## Khách trả lời bằng cách phủ định

Đây là chỗ hay sai nhất khi đọc câu trả lời, và nó sai theo hướng tệ nhất: ra
đúng thiết bị ngược lại.

Câu hỏi nhắc tới một dấu hiệu, và khách rất hay nhắc lại đúng dấu hiệu đó để
**bác bỏ** nó. "Không phải trần đâu ạ", "nhà em không gắn trần", "không có bình
gas" — cả ba đều chứa đúng từ khoá của vế khẳng định.

Đọc đúng: có từ phủ định ngay trước dấu hiệu thì câu trả lời là **vế còn lại**.

## "Em không rõ" không phải là "không"

"Em không rõ lắm", "không biết nữa ạ", "em chưa rõ" đều mang từ "không" nhưng
không phải câu phủ định. Đó là khách nói họ không phân biệt được.

Đọc nó thành "không" là tự trả lời hộ khách, và khách sẽ không bao giờ thấy chỗ
sai nằm ở đâu.

Khi khách không rõ, có hai đường đi. Hỏi một dấu hiệu khác dễ thấy hơn, hoặc
nhận ảnh thêm ở góc khác. Nếu vẫn không xong thì **đừng chọn bừa một bên**: mời
khách đặt gói kiểm tra và chẩn đoán thiết bị, nói rõ thợ sang xác định tận nơi.
Đó là câu trả lời trung thực và vẫn dẫn khách tới chỗ được giúp.

Chú ý một câu hay gặp và rất dễ đọc nhầm: "em không rõ, chắc là quạt trần". Câu
này có từ "không" nhưng thứ đáng giá nhất trong câu là phỏng đoán của khách. Đọc
nó thành phủ định là vứt đi đúng phần thông tin duy nhất khách đưa ra.

## Ba lựa chọn thì "có" không trả lời gì cả

Với câu hỏi hai lựa chọn, "dạ có" và "không" là câu trả lời đủ nghĩa.

Với câu hỏi ba lựa chọn — máy giặt, máy sấy quần áo, máy rửa bát — thì "có"
không chọn cái nào. Gặp câu trả lời như vậy thì hỏi lại ngắn gọn, đừng suy ra
cái đầu tiên trong danh sách.

## Những câu không được nói

Không đưa lời khuyên an toàn của cả hai thiết bị cùng lúc cho chắc. Khách sẽ làm
theo cả hai, và một trong hai là sai.

Không nói "theo ảnh thì đây là lò vi sóng" khi ảnh không đủ để nói vậy. Nói chắc
chắn một điều mình không chắc là cách nhanh nhất mất lòng tin, và khách sẽ phát
hiện ra ngay khi thợ tới.

Không hỏi lại lần thứ hai cùng một dấu hiệu bằng cách diễn đạt khác. Khách đã
trả lời là không phân biệt được thì hỏi lại kiểu khác cũng vẫn thế.

Không vì chưa chắc thiết bị mà ngừng mời đặt lịch. Chưa rõ thiết bị vẫn đặt được
gói kiểm tra và chẩn đoán.

## Chỗ cần thợ xác nhận

Máy rửa bát âm tủ có mặt nạ gỗ trùng với cánh tủ bếp thì trong ảnh gần như không
thấy được gì — có dấu hiệu nào khách nhìn thấy được để tách nó khỏi máy giặt
không, ngoài việc hỏi máy dùng làm gì.

Bếp hồng ngoại nên xếp cùng nhóm với bếp từ hay tách riêng, vì mặt bếp nhìn
giống nhau nhưng bếp hồng ngoại vẫn nóng mặt kính sau khi tắt và đó là một cảnh
báo an toàn khác.
