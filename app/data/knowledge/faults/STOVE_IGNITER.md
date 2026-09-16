---
doc_id: KB_FAULT_STOVE_IGNITER
doc_type: fault
device_type: gas_stove
fault_code: STOVE_IGNITER
name_vi: Không lên lửa, đánh lửa hỏng
urgency: MEDIUM
confusable_with: [STOVE_REGULATOR, STOVE_BURNER_CLOGGED, STOVE_FLAME_OUT, STOVE_GAS_LEAK]
price_policy: Không ghi giá trong tài liệu này. Giá lấy từ bảng giá của hệ thống.
last_reviewed: 2026-09-17
needs_technician_review:
  - Bộ đánh lửa chạy pin hay chạy điện lưới, trên đúng model khách đang dùng
---

# Không lên lửa, đánh lửa hỏng

## Cảnh báo phải nói trước khi chẩn đoán

Bệnh này được đánh mức ưu tiên trung bình, nhưng nó có một cạnh nguy hiểm mà phải nói
ngay ở câu đầu, trước khi hỏi bất cứ điều gì.

Khách gặp bệnh này thì phản xạ là bấm đánh lửa nhiều lần. Bấm, không lên, bấm tiếp,
vẫn không lên, bấm tiếp nữa.

**Mỗi lần bấm mà không cháy là một lần gas ra thẳng vào phòng.** Sau một chuỗi chục
lần, trong bếp đã có một lượng gas đáng kể nằm dưới sàn, và lần bấm tiếp theo là một
tia lửa gặp đúng lượng gas đó.

Vì vậy câu đầu tiên phải là: nếu đã bấm vài lần không lên thì dừng lại, khoá van bình,
mở cửa cho thoáng, chờ mùi tan hẳn rồi mới thử tiếp.

Nói kèm lý do chứ đừng chỉ ra lệnh. Khách hiểu vì sao thì mới làm.

Nếu khách đã nhắc tới mùi gas thì chuyển hẳn sang cảnh báo của STOVE_GAS_LEAK, đủ bốn
việc, rồi mới quay lại chẩn đoán.

## Ba việc phải hỏi và kiểm theo đúng thứ tự tiền

Bệnh này có đặc điểm tốt: phần lớn ca dừng ở những việc không mất tiền. Vì vậy thứ tự
kiểm tra quan trọng hơn kiến thức kỹ thuật.

**Một, bình còn gas không.** Việc miễn phí và là nguyên nhân số một.

**Hai, van bình đã mở chưa.** Cũng miễn phí. Nghe ngớ ngẩn nhưng nó là nhánh thật,
nhất là ở nhà có thói quen khoá van sau mỗi lần nấu, hoặc nhà vừa đi vắng về.

**Ba, pin bộ đánh lửa còn không.** Rẻ, khách tự thay được, và là nguyên nhân số hai.

Chỉ sau ba việc đó mới tới kim đánh lửa, mâm chia lửa, họng lửa, và cuối cùng là bo
mạch đánh lửa.

Đi đúng thứ tự này thì rất nhiều ca kết thúc trong hai tin nhắn và khách không mất
đồng nào. Đi ngược thứ tự thì khách được hẹn thợ cho một cục pin.

## Câu hỏi tách nhánh mạnh nhất

**"Anh chị bấm đánh lửa có nghe tiếng tạch tạch và thấy tia lửa không ạ?"**

Câu này chia bệnh làm hai nửa gần như không giao nhau, và khách trả lời được ngay mà
không cần tháo gì.

**Có tạch, có tia lửa, nhưng không cháy.** Điện đánh lửa còn tốt. Vấn đề ở phía gas:
hết gas, van chưa mở, van điều áp, họng lửa nghẹt, hoặc mâm lắp lệch.

**Không tạch, không tia lửa.** Vấn đề ở phía đánh lửa: hết pin, kim bẩn hoặc ướt, dây
đánh lửa đứt, nút bấm hỏng, bo mạch hỏng.

**Tạch yếu, thưa, phải bấm lâu mới ra tia.** Gần như chắc chắn là pin yếu. Đây là mô
tả rất đặc trưng và đáng nhận ra.

Một câu hỏi tách được cả bệnh là thứ hiếm, nên câu này nên hỏi sớm, thường ngay tin
nhắn thứ hai.

## Nhánh có tia lửa mà không cháy

Đi từ rẻ tới đắt.

**Hết gas.** Nghiêng bình thấy nhẹ, hoặc mấy hôm trước lửa đã yếu dần. Nếu cả hai bếp
cùng không lên thì nhánh này càng mạnh.

**Van bình chưa mở**, hoặc mở chưa hết. Kiểm tra bằng mắt.

**Van điều áp lắp chưa khít**, nhất là ngay sau khi đổi bình. Dấu hiệu: vừa đổi bình
xong là bếp không lên.

**Mâm chia lửa lắp lệch.** Gas ra nhưng không tới được chỗ có tia lửa. Dấu hiệu: vừa
vệ sinh bếp xong.

**Họng lửa nghẹt.** Lỗ phun bị thức ăn khô bít lại. Dấu hiệu: trước đó lửa đã yếu dần
và cháy không đều. Nhánh này dẫn sang STOVE_BURNER_CLOGGED.

**Cảm ứng nhiệt.** Nếu lửa bùng lên rồi tắt ngay khi buông tay, đó không phải bệnh này
mà là STOVE_FLAME_OUT.

Ba nhánh đầu chiếm phần lớn ca và cả ba đều không cần thợ.

## Nhánh không có tia lửa

**Hết pin.** Nguyên nhân phổ biến nhất của nhánh này. Bếp dùng pin thường có một hộc
pin ở mặt dưới hoặc phía sau, mở bằng tay hoặc bằng một con vít. Thay pin mới cùng
loại, và thay cả cặp chứ không thay một viên.

Dấu hiệu rất đặc trưng: tiếng tạch yếu dần và thưa dần trong mấy tuần trước đó, phải
bấm lâu hơn mới lên. Khách hay kể là "dạo này phải bấm lâu mới cháy".

**Pin bị chảy nước.** Độ ẩm cao ở Việt Nam làm pin rỉ, và dịch rỉ ăn mòn tiếp điểm
trong hộc. Thay pin mới mà vẫn không tạch thì mở hộc ra xem có lớp trắng xanh bám ở
tiếp điểm không. Cạo sạch rồi thử lại.

**Kim đánh lửa ướt hoặc bẩn.** Sau khi trào nồi, sau khi rửa bếp, hoặc ngày nồm. Lau
khô đầu kim và phần sứ quanh nó, để khô hẳn rồi thử.

**Kim đánh lửa nứt phần sứ.** Điện rò ra thân bếp thay vì phóng qua khe. Nhìn kỹ thấy
vết nứt trên lớp sứ trắng. Cần thay kim.

**Bếp dùng điện lưới mà chưa cắm điện**, hoặc ổ cắm mất điện. Nghe đơn giản nhưng
đáng hỏi một câu.

**Nút bấm hoặc bo mạch đánh lửa hỏng.** Nhánh cuối cùng, và là nhánh duy nhất trong
nhóm này cần thợ.

## Thay pin: chi tiết nhỏ nhưng hay sai

Đáng viết riêng vì nó là việc khách tự làm nhiều nhất trong cả cụm bếp gas, và có
mấy chỗ sai lặp đi lặp lại.

Thay cả cặp cùng lúc, cùng loại, cùng hãng. Trộn một viên cũ một viên mới thì viên
mới bị kéo tụt theo và tuổi thọ ngắn lại.

Kiểm tra chiều cực. Lắp ngược là không tạch, và nhiều người lắp xong kết luận là bếp
hỏng.

Ấn cho pin vào hẳn lò xo. Hộc pin của bếp thường nằm ngửa dưới gầm nên dễ lắp hờ.

Nếu tiếp điểm có lớp trắng xanh thì cạo sạch trước khi lắp pin mới.

Nếu bếp không dùng lâu, nên tháo pin ra. Pin nằm lâu trong hộc là pin chảy nước, và
chảy nước thì hỏng cả hộc chứ không chỉ hỏng pin.

## Lau kim đánh lửa

Việc miễn phí thứ hai và cũng nên gợi ý sớm.

Để bếp nguội hẳn và khoá van bình.

Kim đánh lửa là que mảnh có phần thân bọc sứ trắng, đầu kim bằng kim loại nhô ra, đặt
sát mép mâm chia lửa.

Lau đầu kim và phần sứ bằng khăn khô. Nếu có muội đen bám thì chà rất nhẹ.

Không uốn, không bẻ. Khoảng cách từ đầu kim tới mâm lửa là có tính toán; xa quá thì
không phóng được tia, gần quá thì tia phóng vào mâm chứ không vào chỗ có gas.

Để khô hoàn toàn rồi mới thử lại. Chỗ này khách hay vội, và thử khi còn ẩm thì vẫn
không tạch, rồi kết luận nhầm.

## Vì sao ngày nồm bếp hay không lên lửa

Đáng giải thích vì nó là nhánh theo mùa rất rõ ở miền Bắc, và biết trước thì không
phải gọi thợ.

Tia lửa đánh lửa là điện áp cao phóng qua một khe hở nhỏ. Khi bề mặt sứ quanh kim
đọng ẩm, điện tìm được đường đi dễ hơn: nó rò dọc theo mặt sứ ẩm xuống thân bếp thay
vì phóng qua khe.

Kết quả là có điện, có bấm, nhưng không có tia ở đúng chỗ cần. Hoặc tia rất yếu.

Cách xử lý: lau khô kim và mặt sứ, để bếp thoáng cho khô, và nếu nhà đang nồm nặng
thì lau lại trước mỗi lần nấu trong vài ngày.

Cùng cơ chế đó giải thích vì sao vừa rửa bếp xong thì đánh lửa không lên, và vì sao
chờ khô là tự hết.

## Khách nói thế nào

"bếp không lên lửa", "bếp không đánh lửa được", "bấm không cháy", "không có lửa",
"bếp gas không nổ lửa", "đánh lửa không ăn", "bấm hoài không lên", "không tạch",
"tạch mà không cháy", "phải bấm lâu mới cháy", "mồi lửa không được".

Không dấu: bep khong len lua, bep gas khong danh lua, bam hoai khong len, khong nghe
tach, tach ma khong chay, phai bam lau moi chay.

Cách nói vùng miền: "bếp không nổ lửa" và "không mồi được lửa" hay gặp ở miền Nam.
"Không đánh lửa" và "không tạch" hay gặp ở miền Bắc.

Có một câu mơ hồ cần hỏi lại: "bếp gas không dùng được". Nó có thể là bệnh này, có thể
là lửa yếu, có thể là núm kẹt. Hỏi một câu về đánh lửa là tách được.

## Đọc ảnh

Ảnh hộc pin mở ra. Thấy được pin có bị chảy nước không, tiếp điểm có lớp trắng xanh
không, pin có lắp đúng chiều không. Ảnh có ích nhất của nhánh không tạch.

Ảnh cụm đầu đốt chụp gần. Thấy được kim đánh lửa, phần sứ có nứt không, đầu kim có
bám muội không, khoảng cách tới mâm có bất thường không.

Ảnh mâm chia lửa nhìn từ trên. Thấy được mâm có vào đúng rãnh không.

Ảnh họng lửa và các lỗ. Thấy được lỗ có bị bít không.

Ảnh van điều áp gắn trên bình. Thấy được van đã vào khớp chưa, tay khoá ở vị trí mở
hay đóng.

Ảnh mặt bếp còn ướt hoặc đọng nước. Bối cảnh mạnh cho nhánh ẩm.

Cần cẩn thận một chỗ: trên ảnh, kim đánh lửa và đầu cảm ứng nhiệt trông giống nhau.
Nếu không phân biệt chắc thì đừng kết luận cái nào hỏng, mà mô tả cả hai rồi hướng
dẫn lau cả hai. Lau cả hai không hại gì.

## Lẫn với bệnh nào

**STOVE_FLAME_OUT.** Khách gộp hai chuyện làm một khi nói "bếp không cháy". Tách bằng
câu hỏi: lửa có bùng lên rồi tắt, hay không bùng lên lần nào. Bùng rồi tắt là bệnh
kia.

**STOVE_BURNER_CLOGGED.** Nghẹt nặng thì cũng không lên lửa nổi. Tách bằng bệnh sử:
nghẹt thì lửa yếu dần trong nhiều ngày trước đó chứ không đột ngột.

**STOVE_REGULATOR.** Van điều áp hỏng cũng làm gas không tới bếp. Tách bằng phạm vi
và bằng mốc đổi bình: cả hai bếp cùng không lên, và mới đổi bình.

**STOVE_GAS_LEAK.** Giao nhau qua chuyện bấm nhiều lần sinh mùi gas. Nếu khách nhắc
mùi gas thì cảnh báo trước, chẩn đoán sau, không có ngoại lệ.

## Kịch bản mẫu

Khách nhắn "bếp không lên lửa". Nhắc trước chuyện đừng bấm liên tục và lý do. Rồi hỏi
câu vàng về tiếng tạch.

Khách nhắn "có tạch mà không cháy". Đi thẳng vào phía gas: bình còn gas không, van mở
chưa, có mới đổi bình không.

Khách nhắn "bấm không nghe gì cả". Đi thẳng vào pin. Hướng dẫn tìm hộc pin, thay cả
cặp, kiểm tra chiều cực, và xem tiếp điểm có rỉ không.

Khách nhắn "dạo này phải bấm lâu mới cháy". Gần như chắc là pin yếu. Trả lời dứt
khoát và hướng dẫn thay pin.

Khách nhắn "vừa rửa bếp xong không lên lửa". Nghiêng về ẩm hoặc mâm lắp lệch. Hướng
dẫn để khô hẳn và kiểm tra mâm đã vào rãnh chưa.

Khách nhắn "mới đổi bình xong là không lên". Nghiêng về van điều áp lắp chưa khít.
Gợi ý gọi lại đại lý vừa đổi bình, và nhắc thử xà phòng.

Khách nhắn "bấm cả chục lần rồi mà không lên, giờ có mùi gas". Chuyển hẳn sang cảnh
báo an toàn đủ bốn việc. Chẩn đoán để sau.

## Nền tri thức của tài liệu này

Toàn bộ nội dung được viết lại bằng lời của dự án, không sao chép nguyên văn từ nguồn
nào.

Cấu tạo bộ đánh lửa áp điện và đánh lửa dùng pin, vai trò của kim đánh lửa và lớp sứ
cách điện: nội dung mô đun thực hành thiết bị gia dụng trong chương trình đào tạo
nghề, đối chiếu tài liệu kỹ thuật của các hãng bếp gas có mặt tại Việt Nam.

Cơ chế điện áp cao rò dọc bề mặt sứ ẩm thay vì phóng qua khe hở: nguyên lý phóng điện
qua khe, kiến thức điện phổ thông.

Cảnh báo về việc bấm đánh lửa liên tục làm tích tụ gas: hướng dẫn an toàn sử dụng khí
hoá lỏng của các đơn vị kinh doanh gas tại Việt Nam.

Thứ tự kiểm tra từ rẻ tới đắt, và tỷ trọng thực tế của nhánh hết pin và nhánh hết gas:
kinh nghiệm nghề của thợ sửa bếp trong nước. Cần cập nhật khi hệ thống chạy thật.

Nhánh theo mùa nồm ở miền Bắc: quan sát thực tế, không phải trích dẫn.

## Chỗ cần thợ xác nhận

Bộ đánh lửa của model khách đang dùng chạy pin hay chạy điện lưới. Khác nhau thì cách
kiểm tra khác hẳn.

Loại và số lượng pin đúng cho model đó.

Khoảng cách chuẩn từ đầu kim đánh lửa tới mâm chia lửa, nếu nghi kim đã bị uốn.

Bo mạch đánh lửa còn làm việc không, khi đã loại hết các nhánh rẻ.

Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
