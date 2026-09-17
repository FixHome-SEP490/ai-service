---
doc_id: KB_DEVICE_WASHING_MACHINE
doc_type: device
device_type: washing_machine
name_vi: Máy giặt
service_group: SVG_APPLIANCE
aliases_vi: [máy giặt, may giat, máy giặt cửa trên, máy giặt cửa ngang, máy giặt lồng đứng, máy giặt lồng ngang, mg]
fault_codes:
  - WM_DRAIN_PUMP
  - WM_NO_SPIN
  - WM_NO_WATER_INLET
  - WM_BEARING_NOISE
  - WM_PCB_FAULT
  - WM_DOOR_SEAL_LEAK
  - WM_DOOR_LOCK
  - WM_SMELL_MOLD
  - WM_MOTOR_FAULT
  - WM_OVERFLOW
price_policy: Không ghi giá trong tài liệu này. Giá lấy từ bảng giá của hệ thống.
last_reviewed: 2026-09-16
needs_technician_review:
  - Mã lỗi của các hãng
  - Tuổi thọ từng bộ phận tính bằng năm
  - Vị trí bộ lọc và ống xả khẩn cấp theo từng model
---

# Máy giặt

## Phạm vi tài liệu này

Tài liệu này nói về máy giặt gia đình: loại cửa trên lồng đứng và loại cửa ngang
lồng ngang, khối lượng giặt phổ biến từ bảy tới mười hai ký. Đây là nhóm chiếm
gần hết số ca của một dịch vụ sửa chữa gia dụng.

Máy giặt sấy kết hợp có thêm nhóm bệnh của phần sấy, và tài liệu này chỉ nhắc
qua. Máy giặt công nghiệp và máy giặt tiệm là nhóm thiết bị khác.

## Câu hỏi phải hỏi trước mọi thứ khác

Máy cửa trên hay máy cửa ngang.

Đây là câu hỏi quan trọng nhất của cả nhóm máy giặt, và nó khác với các thiết bị
khác ở chỗ hai loại này không chỉ khác hình dáng mà khác cả cấu tạo, khác nhóm
bệnh, khác cách xử lý, và khác rất xa về chi phí.

Máy cửa trên có lồng quay quanh trục thẳng đứng, không có khoá cửa chặt, không
có gioăng cửa kín nước, và cấu tạo đơn giản hơn nhiều. Tháo lắp dễ, linh kiện rẻ.

Máy cửa ngang có lồng quay quanh trục nằm ngang, cửa phải khoá chặt vì nước nằm
dưới mức cửa, có gioăng cao su lớn quanh miệng cửa, và vắt ở tốc độ cao hơn
nhiều. Cấu tạo phức tạp, tháo lắp phải rã gần hết vỏ, và một số hạng mục như
thay bạc đạn thì đắt hơn hẳn máy cửa trên.

Vì vậy nhiều bệnh trong danh sách chỉ áp dụng cho một loại. Gioăng cửa rách và
khoá cửa kẹt gần như chỉ có ở máy cửa ngang. Không kết luận những bệnh đó cho
máy cửa trên.

Cách nhận biết nếu khách không biết gọi tên: máy bỏ đồ vào từ phía trên nắp là
cửa trên; máy có cửa tròn kính mở ra phía trước là cửa ngang.

## Máy gồm những gì

Lồng giặt trong bằng thép không gỉ có đục lỗ, chứa quần áo.

Thùng ngoài chứa nước, bao quanh lồng trong. Nước nằm ở khoảng giữa hai lồng.

Mô tơ quay lồng. Trên máy đời cũ là mô tơ truyền động qua dây curoa và puly.
Trên máy đời mới nhiều model dùng mô tơ truyền động trực tiếp gắn thẳng vào trục
lồng, không có dây curoa.

Bạc đạn, còn gọi là vòng bi, đỡ trục lồng. Kèm theo là phớt chặn nước ngăn không
cho nước lọt vào bạc đạn.

Van cấp nước điện từ ở phía sau, mở ra cho nước vào theo lệnh của bo.

Bơm xả nước, thường ở góc dưới, có lưới lọc trước bơm.

Cảm biến mực nước. Đây là một chi tiết đáng hiểu vì nó gây ra nhiều bệnh: nó
không đo mực nước trực tiếp mà đo áp suất khí trong một buồng nhỏ nối với đáy
thùng qua một ống hơi mềm. Nước dâng thì khí trong buồng bị nén và cảm biến đọc
ra mức nước.

Khoá cửa, trên máy cửa ngang là khoá điện có chốt cơ khí, khoá chặt suốt chu
trình và chỉ nhả sau khi máy dừng và nước đã rút.

Gioăng cửa, trên máy cửa ngang là vòng cao su lớn giữa cửa và thùng.

Bo mạch điều khiển, cảm biến nhiệt độ nước, điện trở gia nhiệt trên model có
giặt nước nóng.

Khay đựng bột giặt và nước xả, ống xả nước, ống cấp nước, và các lò xo cùng
giảm chấn treo thùng.

## Máy giặt làm việc theo chu trình

Hiểu chu trình giúp đọc đúng câu "máy đứng ở bước nào", và đó là một trong những
câu hỏi chẩn đoán tốt nhất của nhóm này.

Cấp nước. Van cấp mở, nước vào, cảm biến mực nước theo dõi cho tới khi đủ rồi
báo bo đóng van.

Giặt. Lồng quay đảo chiều liên tục ở tốc độ chậm.

Xả. Bơm xả đẩy nước ra qua ống xả.

Giũ. Cấp nước lại, quay đảo, rồi xả. Lặp vài lần.

Vắt. Lồng quay rất nhanh một chiều, nước bị văng ra qua lỗ lồng rồi bơm ra
ngoài. Trước khi vắt, máy kiểm tra hai điều kiện: nước đã rút hết chưa, và đồ
trong lồng có cân không.

Hai điều kiện đó giải thích phần lớn ca máy không vắt. Máy không từ chối vắt vì
hỏng; nó từ chối vì một trong hai điều kiện chưa đạt.

## Máy đứng ở bước nào, câu hỏi chẩn đoán tốt nhất

Khách thường biết máy dừng ở đâu, vì bảng điều khiển hiển thị hoặc vì họ nghe
được.

Đứng ở bước cấp nước, nước vào rất chậm hoặc không vào: nhánh van cấp, áp lực
nước, hoặc lưới lọc đầu van. Mã WM_NO_WATER_INLET.

Nước vào hoài không dừng: nhánh cấp nước không ngắt, mã WM_OVERFLOW. Đây là ca
ưu tiên cao nhất của nhóm máy giặt.

Đứng ở bước xả, nước không rút: nhánh bơm xả và đường xả, mã WM_DRAIN_PUMP.

Chạy tới bước vắt rồi dừng, đồ vẫn ướt sũng: nhánh không vắt, mã WM_NO_SPIN. Gốc
thường là lệch tải hoặc nước chưa rút hết, không phải hỏng.

Lồng hoàn toàn không quay từ đầu: nhánh mô tơ hoặc dây curoa, mã WM_MOTOR_FAULT
hoặc WM_NO_SPIN.

Dừng giữa chừng không theo quy luật, báo mã lỗi: nhánh bo, mã WM_PCB_FAULT.

Không chạy vì báo chưa đóng cửa: nhánh khoá cửa, mã WM_DOOR_LOCK.

Câu hỏi này nên được hỏi sớm, và nó tách được năm sáu nhánh chỉ bằng một câu.

## Khách gọi tên bộ phận thế nào

Lồng giặt: lồng, thùng, lô, cái lồng trong, thùng giặt.

Mô tơ: mô tơ, mo tơ, động cơ, cái mô tơ quay lồng.

Dây curoa: dây cua roa, dây curoa, dây cô roa, dây đai, dây kéo.

Bạc đạn: bạc đạn, vòng bi, bi, bạc, cái bi lồng.

Bơm xả: bơm xả, bơm, cái bơm nước ra, mô tơ xả.

Van cấp nước: van nước, van cấp, cái van sau máy, van điện từ.

Cảm biến mực nước: phao, cái phao, phao nước, cảm biến nước, sen sơ nước.

Khoá cửa: khoá cửa, chốt cửa, cái khoá, công tắc cửa.

Gioăng cửa: gioăng, ron, cao su cửa, viền cao su, cái vòng cao su.

Bo mạch: bo, bo mạch, board, bảng mạch, cái mạch.

Lưới lọc bơm: lưới lọc, bộ lọc, cái nắp tròn dưới góc, lọc cặn.

Khay bột giặt: khay, ngăn đựng xà bông, hộc bột giặt, khay nước xả.

Khi khách nói "cái phao hỏng" thì đó là cảm biến mực nước, và đây là từ nghề mà
nhiều khách đã nghe từ thợ trước.

## Khách gõ không dấu, gõ tắt

may giat khong vat, may giat khong xa nuoc, may giat khong vao nuoc, mg khong
vat, may giat keu to, may giat ro nuoc, may giat bao loi, may giat khong mo duoc
cua, may giat hoi, quan ao giat xong van uot, may giat rung lac.

Biến thể chính tả: giặt và giăt và dặt, vắt và vát và vắc, xả và sả, curoa và cua
roa và cu roa, bạc đạn và bạt đạn.

Cách nói chuyện: em ơi máy giặt nhà chị không vắt, ê máy giặt kêu to quá, cho
hỏi máy giặt không xả nước là bị gì.

## Bảy nhóm triệu chứng gốc

Nhóm một, máy không cấp nước hoặc cấp quá chậm.

Nhóm hai, máy cấp nước không ngừng, tràn nước. Ưu tiên cao nhất.

Nhóm ba, máy không xả được nước, nước đọng trong lồng.

Nhóm bốn, máy không vắt, đồ ra còn ướt sũng.

Nhóm năm, máy kêu to, rung lắc bất thường.

Nhóm sáu, máy rò nước ra sàn.

Nhóm bảy, máy không chạy, không nhận lệnh, báo mã lỗi, hoặc không mở được cửa.

Ngoài bảy nhóm đó còn nhóm mùi và cặn bẩn, không phải hỏng máy nhưng là ca rất
phổ biến.

## Nhóm một: không cấp nước

Mã WM_NO_WATER_INLET.

Thứ tự kiểm tra từ ngoài vào trong, và ba bước đầu hoàn toàn miễn phí. Van nước
tổng đã mở chưa. Vòi cấp có bị gập, bị đè, bị xoắn không. Khu vực có đang mất
nước hoặc yếu nước không.

Rồi mới tới lưới lọc ở đầu van cấp phía sau máy, thường bị cặn và rỉ sắt bịt.
Sau đó là van cấp điện từ, rồi tới cảm biến mực nước đọc sai làm máy tưởng đã
đủ nước, rồi tới bo.

Với nhà dùng bồn chứa trên mái và áp lực yếu, đây là nguyên nhân rất phổ biến và
không phải hỏng máy. Máy giặt cần một áp lực tối thiểu để van mở đúng.

## Nhóm hai: cấp nước không ngừng, tràn nước

Mã WM_OVERFLOW. Đây là ca duy nhất trong nhóm máy giặt được đánh mức ưu tiên cao
nhất, và cách xử lý khác mọi ca khác.

Lời khuyên phải đi trước mọi câu hỏi: khoá van cấp nước ngay. Nếu nước đã lan ra
sàn và có ổ điện gần đó thì ngắt aptomat khu vực.

Lý do đặt cao: nước tràn ra sàn nhà tắm hoặc ban công lan rất nhanh, gây trơn
trượt, làm hỏng sàn và tường, chảy xuống nhà dưới ở chung cư, và tiếp cận thiết
bị điện.

Có một biến thể đáng nhớ và khách hay kể: rút điện rồi mà nước vẫn vào. Đây là
dấu hiệu van cấp bị kẹt cơ khí ở trạng thái mở, vì van điện từ mất điện thì phải
tự đóng. Với ca này, rút điện không giải quyết được gì và bắt buộc phải khoá van
nước.

Nguyên nhân hay gặp: van cấp kẹt vì cặn, cảm biến mực nước hỏng, ống hơi của cảm
biến tuột hoặc thủng, buồng áp lực bị cặn bịt, hoặc bo hỏng.

## Nhóm ba: không xả được nước

Mã WM_DRAIN_PUMP.

Ba nguyên nhân phổ biến nhất theo thứ tự: lưới lọc trước bơm bị bịt bởi tóc, xơ
vải, tiền xu, ghim, hạt cúc; cánh bơm bị kẹt bởi cùng những thứ đó; và ống xả bị
gập, bị nâng quá cao, hoặc bị nghẹt.

Lưới lọc là chỗ khách tự làm được trên phần lớn máy cửa ngang, và nó giải quyết
một tỉ lệ đáng kể số ca. Nhưng phải nói rõ quy trình: rút điện, chuẩn bị khăn và
chậu vì nước sẽ chảy ra, xả hết nước qua ống xả khẩn cấp trước, rồi mới mở nắp
lọc.

Có một nhánh không phải hỏng bơm: cảm biến mực nước đọc sai làm máy tưởng vẫn
còn nước nên treo ở bước xả, hoặc ngược lại tưởng đã hết nên chuyển bước sớm.

## Nhóm bốn: không vắt

Mã WM_NO_SPIN. Đây là nhóm mà phần lớn ca không phải hỏng máy, và biết điều đó
tiết kiệm cho khách rất nhiều.

Máy chỉ vắt khi hai điều kiện đạt: nước đã rút hết, và đồ trong lồng phân bố cân.

Vì vậy nguyên nhân số một là lệch tải: một cái chăn, một tấm thảm, hoặc vài cái
áo dồn về một phía. Máy cố cân lại vài lần rồi bỏ cuộc. Xử lý là mở ra, dàn đều
đồ, và chạy lại chế độ vắt. Miễn phí.

Nguyên nhân số hai là nước chưa rút hết, nên thật ra đây là ca của nhóm ba đội
lốt.

Nguyên nhân số ba là giặt quá ít đồ. Một cái quần bò duy nhất trong lồng cũng
gây lệch tải.

Sau đó mới tới dây curoa trùng hoặc đứt trên máy có curoa, khoá cửa không báo
đóng, và cuối cùng là mô tơ.

Câu hỏi tách tốt nhất: lồng có quay chậm trong lúc giặt không, và mẻ giặt vừa
rồi có chăn, thảm, hay ít đồ không.

## Nhóm năm: kêu to, rung lắc

Mã WM_BEARING_NOISE cho tiếng do bạc đạn, WM_NO_SPIN nếu do lệch tải.

Rung lắc mạnh khi vắt: trước hết kiểm tra ba thứ miễn phí. Máy có kê cân không,
bốn chân có chạm đất đều không. Đồ có bị dồn lệch không. Và quan trọng với máy
mới mua: bốn con bu lông vận chuyển ở lưng máy đã tháo chưa. Không tháo bu lông
vận chuyển là nguyên nhân số một khiến máy mới rung như sắp nhảy, và nó làm hỏng
bạc đạn rất nhanh.

Tiếng ù to, rào rào, như máy bay, chỉ xuất hiện khi vắt và tăng dần theo tháng:
bạc đạn mòn. Đây là hạng mục đắt, nhất là với máy cửa ngang.

Tiếng kim loại va, tiếng lạch cạch: vật lạ lọt vào khe giữa hai lồng, thường là
đồng xu, ghim, gọng áo lót. Ca này rẻ nhưng để lâu thì vật lạ cào rách lồng.

Tiếng trượt, tiếng rít khi lồng bắt đầu quay: dây curoa trùng.

## Nhóm sáu: rò nước ra sàn

Nước ở phía trước máy cửa ngang, quanh cửa: gioăng cửa rách hoặc bẩn, mã
WM_DOOR_SEAL_LEAK.

Nước ở phía sau: ống cấp nước lỏng, ống xả tuột, hoặc khay bột giặt tràn.

Nước ở dưới đáy giữa máy: thùng nứt, phớt chặn nước hỏng, hoặc mối nối ống trong
máy.

Nước quanh nắp lọc dưới góc: nắp lọc chưa vặn chặt sau một lần vệ sinh.

Nước ở khay bột giặt tràn ra: khay bị cặn bịt, hoặc đổ quá nhiều bột.

Câu hỏi tách: nước xuất hiện ở phía nào của máy, và lúc nào trong chu trình.

Phần rò nước có một điểm an toàn riêng: nước trên sàn gần ổ cắm máy giặt là rủi
ro điện thật, và đáng cảnh báo.

## Nhóm bảy: không chạy, báo lỗi, không mở được cửa

Không lên nguồn: kiểm tra phích cắm, ổ cắm, aptomat trước.

Không nhận nút, tự dừng giữa chừng, đèn nháy, hiện mã lỗi: nhánh bo, mã
WM_PCB_FAULT. Nhưng trước khi kết luận bo, thử rút điện mười phút rồi bật lại
một lần, vì một số ca chỉ là vi điều khiển treo.

Báo chưa đóng cửa dù cửa đã đóng, hoặc không mở được cửa sau khi giặt xong: nhánh
khoá cửa, mã WM_DOOR_LOCK. Với máy cửa ngang, cửa không mở được khi trong lồng
còn nước là thiết kế đúng chứ không phải hỏng.

## Mười bệnh trong hệ thống

Hỏng bơm xả, nghẹt đường xả, WM_DRAIN_PUMP. Nước đọng trong lồng, máy đứng ở bước
xả. Một trong hai ca phổ biến nhất.

Không vắt, hỏng dây curoa hoặc lệch tải, WM_NO_SPIN. Đồ ra còn ướt sũng. Ca phổ
biến nhất, và phần lớn không phải hỏng máy.

Không cấp nước, nghẹt van cấp, WM_NO_WATER_INLET. Máy đứng ở bước cấp nước.

Mòn bạc đạn lồng giặt, WM_BEARING_NOISE. Kêu to khi vắt, tăng dần theo tháng.
Hạng mục đắt nhất sau mô tơ.

Lỗi bo mạch điều khiển, WM_PCB_FAULT. Thất thường, báo mã lỗi.

Rách gioăng cửa, rò nước, WM_DOOR_SEAL_LEAK. Chỉ có ở máy cửa ngang.

Hỏng khoá cửa, WM_DOOR_LOCK. Chủ yếu ở máy cửa ngang.

Hôi lồng giặt, đóng cặn, WM_SMELL_MOLD. Không phải hỏng máy nhưng rất phổ biến.

Hỏng mô tơ giặt, WM_MOTOR_FAULT. Lồng không quay, có thể kèm mùi khét. Ít gặp
nhưng đắt.

Cấp nước không ngắt, tràn nước, WM_OVERFLOW. Ưu tiên cao nhất.

## Bệnh nào hay gặp nhất

Xếp gần đúng theo tần suất: không vắt do lệch tải đứng đầu, rồi tới nghẹt lưới
lọc và bơm xả, rồi hôi lồng, rồi cấp nước yếu, rồi gioăng cửa và khoá cửa, rồi
bạc đạn, rồi bo, và cuối cùng là mô tơ.

Điều này có ý nghĩa với chẩn đoán: khi khách nói máy giặt không vắt, xác suất
tiên nghiệm nghiêng mạnh về lệch tải và về nước chưa rút, chứ không về mô tơ. Nói
điều đó với khách trước khi báo giá là đúng, và nó giải quyết được không ít ca
mà không cần thợ.

## Tuổi thọ

Một máy giặt gia đình dùng bình thường thường phục vụ tốt khoảng tám tới mười
hai năm, có máy lâu hơn.

Các bộ phận không có tuổi thọ bằng nhau. Gioăng cửa, dây curoa, lưới lọc và khoá
cửa là nhóm xuống trước. Bơm xả và van cấp thuộc nhóm thay giữa đời máy. Bạc đạn
thường xuống ở nửa sau đời máy. Mô tơ và lồng là phần bền nhất, và khi mô tơ hoặc
lồng hỏng thì thường là lúc cân nhắc thay máy.

Các mốc năm cụ thể nên để thợ xác nhận.

## Lắp đặt và kê máy

Phần này giải thích được nhiều ca mà khách tưởng là máy hỏng.

Tháo bu lông vận chuyển. Máy cửa ngang mới xuất xưởng có ba tới bốn con bu lông
ở lưng máy giữ chặt thùng để nó không lắc khi vận chuyển. Phải tháo hết trước khi
dùng. Không tháo thì máy rung dữ dội và bạc đạn hỏng rất nhanh. Đây là lỗi lắp
đặt phổ biến nhất và là câu đáng hỏi mọi khách có máy mới mua kêu to.

Kê cân bằng. Chỉnh bốn chân cho máy đứng vững, không bập bênh. Máy giặt vắt ở tốc
độ rất cao nên chỉ lệch một chút là rung mạnh.

Kê trên nền cứng và phẳng. Sàn gỗ mỏng, sàn gác, hoặc bệ kê yếu đều cộng hưởng.

Ống xả đặt đúng độ cao theo hướng dẫn. Đặt quá cao thì bơm không đẩy nổi; đặt
thấp quá hoặc thả vào nước thì nước có thể chảy ngược vào lồng.

Van cấp nước riêng cho máy, có khoá được. Việc này quan trọng hơn vẻ ngoài của
nó, vì ca tràn nước chỉ xử lý được bằng cách khoá van.

Ổ cắm riêng, có tiếp đất, và tốt nhất là có thiết bị chống dòng rò.

Đặt máy nơi khô ráo, thoáng. Máy đặt ngoài ban công hứng mưa nắng xuống cấp
nhanh hơn nhiều, và đây là bối cảnh rất phổ biến ở Việt Nam.

## An toàn điện

Máy giặt là thiết bị vừa dùng điện vừa dùng nước, nên nó là một trong những thiết
bị gia dụng có rủi ro điện giật cao nhất trong nhà.

Hệ thống điện nhà ở tại Việt Nam có quy chuẩn kỹ thuật quốc gia riêng quy định về
bảo vệ chống điện giật, bảo vệ quá tải và ngắn mạch, và nối đất bảo vệ. Bản thân
máy giặt cũng có tiêu chuẩn an toàn riêng cho thiết bị điện gia dụng.

Ba điều đáng nói với khách bằng ngôn ngữ thường. Vỏ máy giặt nên được nối đất,
hoặc ít nhất phải cắm vào ổ ba chấu có dây tiếp đất. Nên có thiết bị chống dòng
rò trên nhánh điện đó. Và ổ cắm phải đặt cao, khô ráo, xa chỗ nước có thể lan tới.

Bốn tình huống phải cảnh báo ngay, không hỏi vòng vo trước. Sờ vào vỏ máy thấy tê
tay. Bật máy lên là nhảy aptomat. Có mùi khét hoặc thấy khói. Nước đã lan tới ổ
cắm hoặc bảng điện.

Với cả bốn, hướng xử lý là ngắt aptomat cấp cho máy, không bật lại, không chạm
vào máy khi chân đang ướt, và gọi thợ.

Cảnh báo tê tay đáng được nhấn mạnh riêng với máy giặt, vì người dùng thường đứng
chân trần trên sàn ướt khi chạm vào máy, và đó là điều kiện xấu nhất cho một cú
giật.

## Dùng đúng cách

Không giặt quá tải. Nhồi đầy lồng làm máy giặt không sạch, gây lệch tải, và hại
bạc đạn.

Không giặt quá ít. Một hai món trong lồng lớn cũng gây lệch tải khi vắt.

Kiểm tra túi quần áo trước khi giặt. Đồng xu, chìa khoá, ghim, bút là nguyên nhân
thật của nghẹt bơm và của vật lạ lọt vào khe lồng.

Dùng túi giặt cho áo lót có gọng. Gọng bung ra là vật lạ nguy hiểm nhất cho lồng
và bơm.

Dùng đúng loại và đúng lượng bột giặt. Máy cửa ngang cần loại ít bọt; dùng sai
loại hoặc đổ quá nhiều sinh bọt tràn và để lại cặn.

Mở cửa và mở khay bột giặt sau khi giặt xong cho khô thoáng. Đây là cách đơn giản
nhất để tránh hôi lồng.

Lau khô gioăng cửa sau mỗi lần giặt, với máy cửa ngang. Nước đọng trong nếp gioăng
là nơi sinh mốc đen.

Vệ sinh lưới lọc bơm định kỳ.

Chạy chu trình vệ sinh lồng định kỳ, hoặc chạy một mẻ không tải với nước nóng.

Khoá van cấp nước khi đi vắng dài ngày.

## Khí hậu và bối cảnh Việt Nam

Máy giặt ở Việt Nam thường đặt ngoài ban công, ngoài hiên, hoặc trong nhà tắm
chật. Ba bối cảnh đó đều ẩm, và ẩm là kẻ thù của phần điện.

Máy đặt ngoài ban công hứng mưa tạt và nắng chiếu: vỏ và bo xuống cấp nhanh hơn,
và rủi ro rò điện cao hơn. Nếu buộc phải đặt ngoài thì nên có mái che và có bệ kê
cao.

Độ ẩm cao quanh năm làm lồng giặt sinh mốc nhanh hơn, nên ca hôi lồng ở Việt Nam
phổ biến hơn xứ khô.

Nước cứng và nước có nhiều cặn, nhất là nước giếng khoan và nước bồn chứa lâu
ngày, làm bịt lưới lọc đầu van cấp và để lại cặn trong lồng.

Áp lực nước yếu ở nhiều khu vực và nhà dùng bồn trên mái: máy cấp nước chậm, và
đây không phải hỏng máy.

Điện áp chập chờn làm hỏng bo.

Chuột và gián chui vào khoang máy, cắn dây, và làm tổ trong buồng áp lực của cảm
biến mực nước.

## Bối cảnh nơi đặt

Chung cư. Nước tràn chảy xuống nhà dưới là chuyện nghiêm trọng hơn nhiều so với
nhà đất, nên ca tràn nước và ca rò nước nên được ưu tiên cao hơn. Máy đặt trong
nhà tắm chật cũng khó tháo lắp và ảnh hưởng tới công.

Nhà phố, máy đặt ngoài ban công hoặc sau bếp. Hứng mưa nắng.

Nhà trọ. Máy thường cũ, nhiều đời người dùng, kê tạm bợ, và có chuyện ai trả tiền
sửa giữa chủ trọ và người thuê.

Tiệm giặt và hộ kinh doanh. Máy chạy liên tục nhiều mẻ mỗi ngày, tích lũy giờ
chạy rất nhanh, và bạc đạn cùng bơm xuống sớm hơn hẳn. Khách nhóm này cần sửa
nhanh vì mất doanh thu theo ngày.

Nhà có trẻ nhỏ. Máy cửa ngang có cửa kính trẻ hay nghịch, và chuyện trẻ chui vào
lồng là rủi ro thật ở nước ngoài đã có ghi nhận. Khoá trẻ em trên máy là có lý do.

## Các hãng phổ biến ở Việt Nam

Nhóm Nhật và Hàn: Panasonic, Toshiba, Sharp, Hitachi, LG, Samsung.

Nhóm châu Âu: Electrolux, Bosch, Beko.

Nhóm phổ thông: Aqua, Casper, Midea, Whirlpool, Candy, Funiki.

Ý nghĩa với việc sửa chữa: hãng phổ biến thì linh kiện dễ kiếm và rẻ hơn, thợ
quen tay hơn. Hãng ít gặp hoặc máy nội địa xách tay thì phải đặt linh kiện và
chờ.

Máy nội địa Nhật xách tay đáng lưu ý riêng: chạy điện một trăm vôn nên phải dùng
qua biến áp, bảng điều khiển tiếng Nhật, mã lỗi tra khó, và bo gần như phải tìm
hàng tháo máy. Khi khách kể máy chạy qua cục biến áp hoặc bảng điều khiển toàn
chữ Nhật, phải nhận ra ngay và báo trước rằng ca này phức tạp hơn.

## Mã lỗi: nguyên tắc đọc

Máy giặt đời mới hiện mã lỗi trên màn hình hoặc báo bằng đèn nháy và tiếng bíp.

Tài liệu này hiện chưa có mã lỗi máy giặt nào được đối chiếu đủ tin cậy để ghi.
Đây là chỗ nên mở rộng dần bằng tài liệu chính hãng.

Ba nguyên tắc bắt buộc. Mã khác nhau giữa các hãng và giữa các dòng của cùng một
hãng, nên không được đoán. Khi khách đưa mã, hỏi hãng và model, nói rõ rằng mã
cần tra theo đúng model, rồi chuyển sang hỏi triệu chứng thực tế. Và mã lỗi cho
biết máy tự thấy cái gì bất thường, không cho biết nguyên nhân gốc: một mã báo
lỗi xả có thể do bơm hỏng, do lưới lọc bịt, do ống xả gập, hoặc do cảm biến đọc
sai.

Một bảng mã bịa ra trông rất đáng tin và sẽ được lặp lại với mọi khách.

## Đọc ảnh khách gửi

Ảnh cả cái máy nhìn từ ngoài. Xác định được loại cửa trên hay cửa ngang, và đó
đã là thông tin quan trọng nhất của nhóm này.

Ảnh bảng điều khiển hiện mã lỗi. Có giá trị nếu biết hãng, nhưng tài liệu này
chưa có mã nào được đối chiếu nên phải hỏi model và không đoán.

Ảnh lưới lọc bơm đầy tóc, xơ vải, đồng xu. Bằng chứng trực tiếp cho ca không xả.

Ảnh gioăng cửa rách, nứt, hoặc có mốc đen trong nếp. Bằng chứng trực tiếp.

Ảnh nước trên sàn quanh máy. Cần hỏi thêm nước ở phía nào của máy.

Ảnh lồng giặt có cặn đen, rong rêu, hoặc mảng bẩn. Chỉ về ca hôi lồng.

Ảnh quần áo lấy ra có vệt đen bám. Cùng hướng.

Ảnh lưng máy còn nguyên bu lông vận chuyển. Rất giá trị với máy mới rung mạnh.

Ảnh ống xả bị gập, bị nâng cao, hoặc thả ngập trong nước. Bằng chứng tốt cho ca
không xả.

Ảnh chân máy không chạm đất đều, hoặc máy kê trên vật kê tạm. Chỉ về ca rung.

Ảnh tem máy phía sau. Rất giá trị: model, hãng, khối lượng giặt, công suất.

Giới hạn: ảnh không cho biết máy đang đứng ở bước nào, và một tấm ảnh máy trông
bình thường không chứng minh được gì.

## Khi nào nên sửa, khi nào nên thay

Nghiêng về sửa khi máy còn dưới khoảng bảy tám năm, bệnh nằm ở nhóm linh kiện
thay được như bơm xả, van cấp, dây curoa, gioăng cửa, khoá cửa, và chi phí sửa
nhỏ so với giá máy mới cùng khối lượng.

Nghiêng về thay khi máy đã cũ và hỏng đúng vào nhóm đắt nhất là mô tơ, bạc đạn
trên máy cửa ngang, hoặc lồng; hoặc khi máy đã sửa nhiều lần trong thời gian
ngắn; hoặc khi linh kiện của model đó không còn kiếm được; hoặc khi là máy nội
địa xách tay khó kiếm linh kiện.

Bạc đạn trên máy cửa ngang là ranh giới đáng nói riêng: nó đòi tháo gần hết máy
nên công cao, và với máy đã nhiều năm thì chi phí có thể chạm ngưỡng đáng cân
nhắc thay máy. Nhưng để lâu không thay thì trục lồng mòn theo và chi phí đội lên
nhiều lần, nên đây là hạng mục không nên hoãn một khi đã xác định.

Khi tư vấn, nói cả hai phương án kèm lý do rồi để khách quyết.

## Kịch bản hội thoại mẫu

Khách nói máy giặt không vắt. Xác nhận, rồi hỏi một câu gộp: máy cửa trên hay cửa
ngang, và mẻ vừa rồi có chăn, thảm, hay rất ít đồ không. Nói trước rằng phần lớn
ca không vắt là do lệch tải hoặc nước chưa rút chứ không phải hỏng máy, và gợi ý
khách dàn đều đồ rồi chạy lại chế độ vắt.

Khách nói máy giặt không xả nước. Hỏi loại máy, và với máy cửa ngang thì hướng
dẫn kiểm tra lưới lọc ở góc dưới, kèm nhắc rút điện và chuẩn bị khăn hứng nước.

Khách nói nước vào hoài không dừng. Đây là ca ưu tiên cao nhất. Câu đầu tiên là
khoá van cấp nước ngay, và nếu nước đã lan ra sàn gần ổ điện thì ngắt aptomat.
Sau đó mới hỏi thêm.

Khách nói máy giặt kêu to khi vắt. Hỏi máy mua bao lâu rồi. Nếu mới mua thì hỏi
đã tháo bu lông vận chuyển ở lưng máy chưa. Nếu máy đã vài năm và tiếng tăng dần
theo tháng thì nghiêng về bạc đạn, và nói trước rằng đây là hạng mục đáng kể,
nhất là với máy cửa ngang.

Khách nói máy giặt không mở được cửa. Hỏi trong lồng còn nước không. Nếu còn thì
nói rõ đó là thiết kế đúng chứ không phải hỏng, và hướng dẫn xả nước qua ống xả
khẩn cấp trước.

Khách nói sờ vào máy thấy tê tay. Cảnh báo an toàn trước tiên: ngắt aptomat,
không chạm vào máy khi chân ướt, không dùng tiếp. Không hỏi vòng vo trước.

Khách nói quần áo giặt xong vẫn hôi. Đây là ca hôi lồng, không phải hỏng máy. Nói
rõ điều đó và hướng dẫn vệ sinh lồng, gioăng cửa và khay bột giặt.

Khách hỏi giá sửa máy giặt. Trả lời giá từ bảng giá, nói rõ biên độ rộng tùy
bệnh và tùy loại cửa trên hay cửa ngang, và mời khách mô tả thêm.

## Khi thiếu thông tin thì ước lượng thế nào

Nói rõ đây là chẩn đoán sơ bộ, và thợ cần kiểm tra tại chỗ.

Với máy giặt, hai thông tin đáng đổi một câu hỏi hơn cả là loại cửa và máy đứng ở
bước nào.

Đưa bệnh khả dĩ nhất theo cả dấu hiệu lẫn tần suất. Với máy giặt, tần suất
nghiêng mạnh về nhóm không phải hỏng máy: lệch tải, lưới lọc bịt, ống xả gập, bu
lông vận chuyển chưa tháo, áp lực nước yếu.

Gợi ý một việc khách tự kiểm tra được ngay và an toàn. Với máy giặt thì có rất
nhiều việc như vậy, và đó là điểm khác biệt của nhóm này so với máy lạnh và tủ
lạnh.

Không bao giờ kết luận một bệnh đắt như mô tơ hoặc bạc đạn từ một mô tả mơ hồ.

## Khách hay hỏi thêm

Máy giặt cửa trên hay cửa ngang tốt hơn. Cửa ngang giặt sạch hơn, tiết kiệm nước
hơn, vắt khô hơn, nhưng đắt hơn và sửa chữa tốn hơn. Cửa trên rẻ hơn, nhanh hơn,
sửa rẻ hơn. Nói theo tiêu chí rồi để khách chọn.

Bao lâu vệ sinh lồng giặt một lần. Chạy chu trình vệ sinh lồng định kỳ, và lau
gioăng cửa cùng khay bột giặt thường xuyên hơn.

Có cần dùng nước xả vải không. Không bắt buộc, và dùng nhiều thì để lại cặn trong
lồng và trong khay.

Giặt nước nóng có tốt hơn không. Sạch hơn với đồ bẩn nhiều và giúp diệt mốc trong
lồng, nhưng tốn điện và không hợp với mọi loại vải.

Máy giặt có cần tiếp đất không. Nên có. Máy giặt vừa dùng điện vừa dùng nước nên
đây là thiết bị đáng nối đất nhất trong nhà.

Đặt máy giặt ngoài ban công có sao không. Dùng được nhưng xuống cấp nhanh hơn vì
mưa nắng và ẩm. Nên có mái che và bệ kê cao.

Máy giặt dùng được bao lâu. Khoảng tám tới mười hai năm với sử dụng bình thường.
Con số cụ thể để thợ xác nhận.

Giặt bao nhiêu ký là vừa. Không nên nhồi đầy lồng. Nhồi đầy làm giặt không sạch,
gây lệch tải, và hại bạc đạn.

## Nền tri thức của tài liệu này

Toàn bộ nội dung được viết lại bằng lời của dự án, không sao chép nguyên văn từ
nguồn nào.

Phần cấu tạo, chu trình giặt, nguyên lý cảm biến mực nước đo áp suất khí qua ống
hơi, và điều kiện để máy cho phép vắt: nội dung mô đun thực hành sửa chữa điện
lạnh và điện gia dụng trong chương trình đào tạo nghề, cộng tài liệu kỹ thuật và
hướng dẫn sử dụng của các hãng có mặt tại Việt Nam.

Phần khác biệt giữa máy cửa trên và máy cửa ngang về cấu tạo, tốc độ vắt, khoá
cửa và chi phí sửa chữa: tài liệu kỹ thuật ngành điện gia dụng trong nước, đối
chiếu chéo nhiều nguồn.

Phần lắp đặt gồm tháo bu lông vận chuyển, kê cân bằng và độ cao ống xả: hướng dẫn
lắp đặt của các hãng.

Phần an toàn điện, nối đất bảo vệ, thiết bị chống dòng rò: tham chiếu QCVN
12:2014/BXD về hệ thống điện của nhà ở và nhà công cộng, và tiêu chuẩn an toàn
thiết bị điện gia dụng.

Phần bối cảnh máy đặt ngoài ban công, nước cứng, áp lực nước yếu, và thói quen
sử dụng: quan sát thực tế trong nước, không phải trích dẫn. Cần cập nhật khi hệ
thống chạy thật.

## Chỗ cần thợ xác nhận

Mã lỗi của các hãng. Tài liệu này chưa có mã máy giặt nào được đối chiếu đủ tin
cậy, nên tuyệt đối không đoán. Đây là mục quan trọng nhất trong danh sách này.

Vị trí lưới lọc bơm và ống xả khẩn cấp theo từng model, vì nó khác nhau và có
model không có.

Vị trí và số lượng bu lông vận chuyển theo từng model.

Độ cao ống xả cho phép theo khuyến cáo của hãng.

Áp lực nước tối thiểu để van cấp làm việc đúng.

Tuổi thọ tính bằng năm của từng bộ phận.

Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
