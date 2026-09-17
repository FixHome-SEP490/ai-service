---
doc_id: KB_FAULT_HOB_ERROR_CODE
doc_type: fault
device_type: induction_hob
fault_code: HOB_ERROR_CODE
name_vi: Bếp từ báo mã lỗi E
urgency: MEDIUM
confusable_with: [HOB_NO_PAN_DETECT, HOB_FAN_NOISY, HOB_TOUCH_FAULT, HOB_NO_POWER]
price_policy: Không ghi giá trong tài liệu này. Giá lấy từ bảng giá của hệ thống.
last_reviewed: 2026-09-17
needs_technician_review:
  - Bảng mã lỗi của các hãng bán chạy nhất ở Việt Nam
  - Mã nào thợ xử lý tại chỗ được và mã nào phải mang bếp về
---

# Bếp từ báo mã lỗi E

## Đừng đoán ý nghĩa của mã, hãy hỏi cho đúng mã

Đây là chỗ dễ sai nhất của mã bệnh này, và sai theo hướng tệ: **mỗi hãng đánh số
lỗi một kiểu**. E0 của hãng này là không nhận nồi, của hãng kia là lỗi cảm biến
nhiệt. Trả lời "E1 là quá nhiệt" cho một khách không rõ bếp hãng gì là đoán,
và khách sẽ làm theo.

Nên việc đầu tiên là xin đúng hai thứ: **mã hiện trên bếp**, và **tên hãng**.
Có hai thứ đó thì thợ tra bảng mã của hãng; không có thì không ai nói chắc được
điều gì.

Cách xin cũng quan trọng. Đừng hỏi "bếp báo lỗi gì", vì khách sẽ trả lời "báo
lỗi E" và dừng ở đó. Hỏi: *bếp hiện đúng chữ và số nào ạ, anh chị đọc giúp em cả
chữ lẫn số*. Và xin một ảnh chụp màn hình bếp lúc đang báo.

## Ba nhóm mã, đúng với hầu hết các hãng

Dù số khác nhau, ý nghĩa gom về ba nhóm, và ba nhóm này dẫn tới ba lời khuyên
rất khác nhau.

**Nhóm nồi.** Không có nồi, nồi không nhiễm từ, nồi quá nhỏ, nồi đặt lệch. Đây
là nhóm hay gặp nhất và không phải hỏng. Thường là mã đầu bảng, và thường kèm
tiếng bíp rồi bếp tự tắt sau ít giây.

**Nhóm nhiệt.** Quá nhiệt bếp, quá nhiệt nồi, cảm biến nhiệt lỗi. Bếp tự ngắt để
tự bảo vệ. Dấu hiệu đi kèm: bếp đã chạy được một lúc rồi mới báo, quạt kêu to,
vỏ bếp nóng. Việc cần làm là để bếp nguội và xem khe thoát nhiệt có bị bịt
không.

**Nhóm điện.** Điện áp cao, điện áp thấp, lỗi mạch công suất, lỗi IGBT. Bếp báo
ngay khi bật hoặc ngay khi tăng công suất. Nhóm này là của thợ, và nếu đi kèm
mùi khét thì phải rút điện và không dùng tiếp.

## Việc khách tự làm được trước khi gọi thợ

**Tắt bếp, rút điện mười phút, bật lại.** Nghe như câu đùa nhưng nó có lý do
thật: phần lớn mã nhóm nhiệt là trạng thái tự bảo vệ, và nó chỉ xoá khi bếp
nguội và bo được cấp nguồn lại. Rất nhiều ca kết thúc ở đây.

**Đổi nồi khác có đáy nhiễm từ.** Loại trừ nguyên cả nhóm nồi trong ba mươi
giây. Thử nam châm vào đáy nồi: hút dính là dùng được.

**Xem khe thoát nhiệt dưới bếp.** Bếp âm tủ hay bị hộc tủ bịt kín khe gió, và
đó là nguyên nhân nền của cả nhóm nhiệt. Dấu hiệu: báo lỗi sau khi nấu được
mười lăm hai mươi phút, lần nào cũng vậy.

**Lau khô mặt kính.** Nước hoặc canh trào lên vùng cảm ứng làm bếp đọc sai và
một số hãng báo lỗi vì việc đó.

Nếu bốn việc trên không hết thì mới tới thợ.

## Khách nói thế nào

"bếp từ báo lỗi E1"

"bếp từ hiện chữ E rồi tắt"

"bếp báo E0 mà em vẫn đặt nồi lên"

"bếp từ nhấp nháy báo lỗi liên tục"

"bếp chạy được mười lăm phút là báo lỗi rồi tắt"

"bếp từ tự ngắt và hiện mã lỗi"

"bếp từ báo lỗi mà em không biết lỗi gì"

## Khách gõ không dấu, gõ tắt

"bep tu bao loi e1"

"bep tu hien chu e roi tat"

"bep tu bao loi lien tuc"

"bep chay mot luc la bao loi"

Chữ "E" hay bị gõ thành "e" thường hoặc bị bỏ qua hẳn — khách viết "bếp báo lỗi
1". Hỏi lại cho rõ là chữ E kèm số mấy, đừng suy ra.

## Khách tự chẩn đoán rồi nói kết luận

"chắc cháy sò công suất rồi"

"em tra mạng thấy E1 là quá nhiệt"

Câu thứ hai rất hay gặp và phải xử lý khéo. Bảng mã trên mạng thường là của một
hãng khác, và nói thẳng "cái đó là của hãng khác" nghe như bác bỏ. Nói theo
hướng: mỗi hãng đánh số khác nhau nên mình xác nhận lại tên hãng cho chắc, rồi
mới kết luận.

## Khi nào là gấp

Báo lỗi **kèm mùi khét, tiếng nổ nhỏ, hoặc khói**: rút điện ngay, không dùng
tiếp, thợ sang trong ngày. Lúc này mã lỗi không còn quan trọng nữa.

Báo lỗi **kèm nhảy aptomat**: không gạt aptomat lên lại, và xử lý như mã bệnh
mất nguồn.

Báo lỗi **kèm mặt kính nứt**: ngừng dùng, vì nước lọt qua vết nứt xuống bo.

Ba trường hợp này đi trước mọi câu hỏi về mã.

## Ảnh khách gửi

Ảnh **màn hình bếp đang hiện mã** là ảnh đáng xin nhất, vì nó loại bỏ sai sót
khi khách đọc lại.

Ảnh mặt trước bếp thấy logo hãng.

Ảnh khe thoát nhiệt dưới bếp hoặc hộc tủ bên dưới, khi nghi nhóm nhiệt.

Ảnh đáy nồi đang dùng, khi nghi nhóm nồi.

## Những câu không được nói

Không nói nghĩa của một mã cụ thể khi chưa biết hãng. Đây là lỗi hay nhất ở mã
bệnh này.

Không bảo khách cứ bật lại dùng tiếp khi bếp đã báo lỗi kèm mùi khét.

Không bảo khách tự mở đáy bếp kiểm tra. Trong đó có tụ lọc nguồn giữ điện áp cao
hàng phút sau khi rút điện.

Không nói "bếp hỏng rồi phải thay" khi mới chỉ có một mã lỗi. Nhóm nồi và nhóm
nhiệt chiếm phần lớn và không phải hỏng.

## Chuyển sang thợ

Sau khi khách đã thử rút điện mười phút, đổi nồi, xem khe thoát nhiệt và lau khô
mặt kính mà vẫn báo lỗi, mời đặt dịch vụ sửa bếp từ. Nói rõ thợ tra bảng mã của
hãng và đo mạch công suất — hai việc không làm qua tin nhắn được.

Nhắc khách chuẩn bị sẵn tên hãng và đời bếp, hoặc chụp cái tem dán dưới đáy bếp,
để thợ mang đúng linh kiện. Điều này tiết kiệm cho khách nguyên một lượt hẹn.

## Kịch bản mẫu

Khách: "bếp từ nhà em nấu được một lúc là hiện chữ E rồi tắt ạ"

Trả lời: Dạ anh chị đọc giúp em đúng mã đang hiện — chữ E kèm số mấy — và cho em
xin tên hãng bếp nữa ạ. Mỗi hãng đánh số lỗi một kiểu nên em không dám đoán
nghĩa khi chưa biết hãng.

Nhưng riêng kiểu anh chị tả — nấu được một lúc mới báo rồi tắt — thì thường là
nhóm lỗi quá nhiệt, bếp tự ngắt để bảo vệ. Anh chị thử hai việc giúp em: tắt
bếp rút điện khoảng mười phút rồi bật lại, và xem khe thoát nhiệt phía dưới bếp
có bị hộc tủ bịt kín không. Bếp âm tủ bị bịt khe gió là nguyên nhân hay gặp nhất
của kiểu này ạ.

Cho em hỏi thêm: có ngửi thấy mùi khét gì không ạ? Nếu có thì anh chị rút điện
và đừng dùng tiếp, để thợ sang xem trong ngày.

Làm hai việc trên mà vẫn báo lỗi thì bên em có dịch vụ sửa bếp từ, thợ tra bảng
mã của hãng và đo mạch công suất tận nơi. Anh chị chụp giúp em cái tem dưới đáy
bếp để thợ mang đúng đồ, rồi đặt lịch giúp em nhé.

## Nền tri thức của tài liệu này

Ba nhóm trạng thái tự bảo vệ của bếp từ — nhận nồi, quá nhiệt, bảo vệ điện áp —
theo tài liệu kỹ thuật bếp từ gia dụng. Việc bảng mã khác nhau giữa các hãng, và
việc rút điện xoá được trạng thái tự bảo vệ, theo hướng dẫn sử dụng của các dòng
bán tại Việt Nam. Phần bếp âm tủ bị bịt khe thoát nhiệt dựa trên ghi nhận của
thợ sửa bếp và thợ lắp tủ bếp.

## Chỗ cần thợ xác nhận

Bảng mã lỗi của các hãng bán chạy nhất ở Việt Nam. Có bảng đó thì trợ lý trả lời
được ngay thay vì phải hỏi hãng rồi chờ thợ.

Mã nào thợ xử lý tại chỗ được và mã nào phải mang bếp về xưởng, để nói trước cho
khách biết mình sẽ mất bếp mấy ngày.
