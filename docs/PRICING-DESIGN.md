# Cách dựng khoảng giá gợi ý

## Quy tắc

Khi AI nhận ra bệnh, nó gợi ý dịch vụ nên đặt, kèm một khoảng giá.

**Sàn là tiền công thợ.** Thợ vẫn phải di chuyển và làm việc dù cuối cùng có thay
linh kiện hay không, nên không có ca nào rẻ hơn mức đó.

**Trần là tiền công cộng ước tính linh kiện** cần thay hoặc sửa.

Khoảng được phép rộng, vì rộng mà đúng thì tốt hơn hẹp mà sai. Nhưng **không
được đội quá cao**, vì con số lớn làm khách ngộp rồi bỏ luôn ý định đặt lịch —
và một khách bỏ đi vì sợ giá là mất mát lớn hơn nhiều so với việc báo hụt vài
trăm nghìn rồi kỹ thuật viên điều chỉnh khi tới nơi.

## Hai bảng giá

**Tiền công** lấy từ mục 8.3.1 tài liệu nghiệp vụ. Mười tám dịch vụ, mỗi dịch vụ
một giá cố định do Admin quản lý và được snapshot lúc khách đặt lịch. Thấp nhất
100.000đ, cao nhất 650.000đ. Nằm ở `app/data/labour_catalog.json`.

**Linh kiện** lấy từ bảng 791 dòng do nhóm dev khác cung cấp. Mỗi dòng là một
khoảng vì giá thật phụ thuộc model. Từ 300đ tới 15 triệu. Nằm ở
`app/data/parts_catalog.json`.

## Vì sao không lấy thẳng trần của linh kiện

Block máy nén Inverter 24.000 BTU có giá 4.5 tới 7.5 triệu. Cộng tiền công thành
gần 8 triệu. Con số đó đúng về mặt kỹ thuật và sai về mặt sản phẩm: khách đọc
xong đóng ứng dụng.

Ba cách xử lý, dùng kết hợp.

**Chọn linh kiện đại diện chứ không chọn đắt nhất.** Một bệnh thường ứng với
nhiều mã linh kiện khác nhau theo công suất. Lấy mã phổ biến nhất chứ không lấy
mã cao cấp nhất.

**Trần lấy mức giữa của khoảng linh kiện, không lấy đỉnh.** Khoảng của mỗi linh
kiện đã tính tới hàng cao cấp; cộng dồn đỉnh của nhiều linh kiện ra một con số
gần như không bao giờ xảy ra.

**Với bệnh mà chi phí có thể rất lớn, nói rõ là cần kiểm tra.** Máy nén hỏng
không nên hiện "8 triệu" mà nên hiện khoảng thấp kèm ghi chú rằng hạng mục này
cần kỹ thuật viên xác định tại chỗ. Báo giá chính thức vốn dĩ chỉ lập sau khi
kiểm tra, nên nói vậy vừa đúng quy trình vừa đỡ dọa khách.

## Khi thiếu dữ liệu

Bảng linh kiện bản v4 (791 dòng) **phủ đủ mười bảy lớp**. Bản v3 trước đó bỏ
trống toàn bộ nhóm nước; bản mới bổ sung bồn rửa, vòi nước, bồn cầu, đường ống,
và tách riêng lò vi sóng, lò nướng, bếp gas, ấm đun thay vì gộp chung.

Còn thiếu là **bảng tiền công**, hiện chỉ phủ mười trong mười bảy lớp. Không có
giá công cho: tủ lạnh, lò vi sóng, lò nướng, bếp gas, ấm đun, bồn cầu, đường
ống nước.

Điều đó lệch về một phía đáng chú ý: bảy lớp này **có linh kiện nhưng không có
công**, nghĩa là biết được trần mà không biết sàn. Trong khi quy tắc lấy sàn làm
điểm tựa, vì đó là con số chắc chắn nhất và là con số khách nhìn trước tiên.

Khi thiếu công, sàn lùi về phí kiểm tra tại nhà 100.000đ. Trung thực, nhưng nó
nói rằng sửa tủ lạnh bắt đầu từ 100.000đ, điều đúng về mặt chữ nghĩa và dễ gây
hiểu nhầm. Bảy dòng bổ sung vào bảng 8.3.1 sẽ xử lý xong chuyện này.

## Con số được tính ra sao

Mỗi bệnh trong `fault_pricing_map.json` trỏ tới một mã tiền công và vài mã linh
kiện đại diện. `tools/price_faults.py` lấy đó dựng ra khoảng giá rồi ghi thẳng
vào bảng bệnh, thay hết các con số tôi ước lượng trước đây. Sàn là giá tiền công
của mã dịch vụ, trần là sàn cộng **mức giữa** khoảng giá của từng linh kiện, làm
tròn tới chục nghìn.

Mười hai bệnh chỉ hiện **một con số** chứ không hiện khoảng, vì chúng đúng là
một dịch vụ trọn gói: vệ sinh máy lạnh, vệ sinh máy giặt, súc bình nóng lạnh,
thay ổ cắm, thay bóng đèn. Không có linh kiện nào phải mua thêm nên không có
trần để mà nói.

## Khi hai bảng không đủ để báo giá

Mười tám bệnh **không hiện trần**. Một phần vì chi phí vốn dĩ mở: vỡ tấm nền TV,
thủng bình nóng lạnh, rò chân bồn cầu, nước đục do rỉ đường ống. Phần còn lại vì
hai bảng hiện tại không đỡ nổi: không có dòng tiền công nào cho việc đó và cũng
không có linh kiện nào đại diện được.

Nhóm thứ hai mới là chỗ dễ sai. Nếu cứ để nguyên, "nghẹt bồn cầu" sẽ hiện đúng
100.000đ — phí kiểm tra tại nhà — nhìn vừa rẻ vừa chắc chắn và sai hoàn toàn.
Nên `price_faults.py` tự đánh dấu mọi bệnh chỉ có `DIAGNOSE_ONSITE` mà không có
linh kiện nào là **cần khảo sát**, thay vì để nó báo một con số mà dữ liệu không
đỡ được.

Trong phản hồi API, `priceEstimate.max` khi đó là `null` kèm
`requiresAssessment: true`. Số 0 từng là lựa chọn hiển nhiên và là lựa chọn sai:
không phân biệt được với công việc không mất tiền, và nó phá luôn ràng buộc
sàn ≤ trần.

Nếu trong một ca có nhiều bệnh nghi ngờ mà chỉ một bệnh cần khảo sát thì cả ca
bỏ trần. Lấy trần cao nhất của các bệnh còn lại là đặt một con số chắc nịch lên
tình huống chưa ai định giá được, và khách sẽ đọc con số thấp đó như toàn bộ
chi phí.

Bảy dòng tiền công còn thiếu ở mục 8.3.1 sẽ kéo phần lớn nhóm này về lại có
trần.

## Quan hệ với báo giá chính thức

Khoảng giá này **chỉ là tham khảo** và không ràng buộc ai. Báo giá chính thức do
kỹ thuật viên lập sau khi kiểm tra trực tiếp, và chỉ có hiệu lực khi khách duyệt.
Điều đó đã nằm trong chính sách và AI luôn kèm câu miễn trừ.

Nói cách khác, khoảng giá tồn tại để khách quyết định **có nên đặt lịch hay
không**, không phải để khách biết mình sẽ trả bao nhiêu. Thiết kế nó theo đúng
mục đích đó thì mới chọn được các đánh đổi ở trên.
